"""The command line. `videogen --help` shows the commands; `videogen <command> --help` the options."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from pathlib import Path

import numpy as np

from videogen import __version__, langs, paths, speech
from videogen import config as video_config
from videogen import subtitles
from videogen.narration import load_script
from videogen.tts import ENGINES, SAMPLE_RATE, get_engine, load_env

# quality -> (Manim flag, name for the output file)
QUALITIES = {"l": ("-ql", "480"), "m": ("-qm", "720"), "h": ("-qh", "1080")}   # flag, name for files
NOISE = re.compile(r"SyntaxWarning|re\.match|^\s*$|Manim Community|^\s+│|^\s+╭|^\s+╰|^\s+\S+\.py:\d+$")
SCENE_FILE = re.compile(r"^(ch\d{2})_.*\.py$")

LATEX_TEST = (
    "import tempfile, manim\n"
    "manim.config.media_dir = tempfile.mkdtemp()\n"
    "manim.config.verbosity = 'WARNING'\n"
    "from manim import MathTex\n"
    "print('LATEX_OK' if MathTex(r'\\frac{1}{2}').width > 0 else 'LATEX_FAIL')\n"
)


def tool_env(root: Path, quality: str) -> dict:
    """The environment of the child processes: the tools on the PATH, and the video folder."""
    env = dict(os.environ)
    extra = [str(folder) for folder in (paths.tex_bin(), paths.venv_bin()) if folder and folder.is_dir()]
    env["PATH"] = os.pathsep.join(extra + [env.get("PATH", "")])
    env["VIDEO_ROOT"] = str(root)
    env["VIDEOGEN_QUALITY"] = quality
    env["PYTHONPATH"] = os.pathsep.join([str(paths.template_root()), env.get("PYTHONPATH", "")])
    env["PYTHONWARNINGS"] = "ignore"   # the dependencies of Manim show SyntaxWarning at import
    return env


def scene_files(root: Path, script) -> dict[str, Path]:
    """One scene file for each scene of the script: scenes/<scene>_*.py."""
    found = {}
    for path in sorted((root / "scenes").glob("ch*.py")):
        match = SCENE_FILE.match(path.name)
        if match:
            if match.group(1) in found:
                raise RuntimeError(f"Two scene files for {match.group(1)}: {found[match.group(1)].name} and {path.name}. Keep one.")
            found[match.group(1)] = path
    missing = [scene for scene in script.order if scene not in found]
    if missing:
        raise RuntimeError(f"No scene file for: {', '.join(missing)}. The file name is scenes/<scene>_<name>.py, for example scenes/ch02_idea.py.")
    return found


def scene_class(path: Path) -> str:
    match = re.search(r"^class (\w+)\(NarratedScene\)", path.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        raise RuntimeError(f"{path.name} has no class that inherits from NarratedScene: `class Name(NarratedScene):`.")
    return match.group(1)


def run_scenes(root: Path, script, scenes, quality: str, jobs: int, dry_run: bool = False, log=print) -> dict:
    """Render scenes with Manim, in parallel. With `dry_run` there is no video: the scenes
    only run, and report layout, cue and pace problems."""
    files = scene_files(root, script)
    env = tool_env(root, "dry" if dry_run else quality)
    tag = "dry" if dry_run else quality
    results = {}

    def one(scene: str):
        media = root / "build" / "media" / tag / scene
        command = [
            sys.executable, "-m", "manim", "--dry_run" if dry_run else QUALITIES[quality][0], "--disable_caching",
            "-v", "WARNING", "--progress_bar", "none", "--media_dir", str(media), str(files[scene]), scene_class(files[scene]),
        ]
        started = time.time()
        done = subprocess.run(command, env=env, capture_output=True, text=True)
        return scene, done, time.time() - started

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        for scene, done, seconds in pool.map(one, scenes):
            output = [line for line in (done.stdout + "\n" + done.stderr).splitlines() if line.strip() and not NOISE.search(line)]
            if done.returncode != 0:
                output = output[-25:]
            results[scene] = {"code": done.returncode, "seconds": seconds, "output": output}
    stats = {"layout": 0, "cue": 0, "pace": 0, "failed": []}
    for scene in scenes:
        result = results[scene]
        counts = {"layout": 0, "cue": 0, "pace": 0}
        for line in result["output"]:
            for kind in counts:
                if line.startswith(f"[{kind}]"):
                    counts[kind] += 1
            if line.startswith("["):
                log("  " + line)
        if result["code"] != 0:
            stats["failed"].append(scene)
            log(f"  FAILED {scene} (exit {result['code']}):")
            for line in result["output"]:
                log("    " + line[:200])
        else:
            log(f"{scene}: {'dry run' if dry_run else 'rendered'} in {result['seconds']:.0f} s, "
                f"{counts['layout']} layout, {counts['cue']} cue, {counts['pace']} pace")
        for kind in counts:
            stats[kind] += counts[kind]
    return stats


# ------------------------------------------------------------------------- commands


def cmd_tts(args):
    config = video_config.load(args.root)
    script = load_script(config.root)
    engine = get_engine(config.engine)
    speech.synthesize(script, config, engine, scenes=args.scenes or None, force=args.force, workers=args.workers)
    print(f"Voice clips ready: {script.beat_count} beats, {config.resolved_voice}, {config.rate}")


def cmd_check(args):
    config = video_config.load(args.root)
    script = load_script(config.root)
    print(f"Layout verification of {', '.join(args.scenes or script.order)} (no video):")
    stats = run_scenes(config.root, script, args.scenes or script.order, "l", args.jobs, dry_run=True)
    total = stats["layout"] + stats["cue"] + stats["pace"]
    print(f"{stats['layout']} layout problems, {stats['cue']} phrases not found, {stats['pace']} beats longer than the voice."
          + ("" if total or stats["failed"] else " The scenes are clean."))
    return 1 if total or stats["failed"] else 0


def cmd_render(args):
    config = video_config.load(args.root)
    script = load_script(config.root)
    stats = run_scenes(config.root, script, args.scenes or script.order, args.quality, args.jobs)
    if stats["failed"]:
        print(f"Not rendered: {', '.join(stats['failed'])}")
        return 1
    print(f"Rendered {len(args.scenes or script.order)} scenes at {QUALITIES[args.quality][1]}p in {config.root / 'build' / 'media' / args.quality}")
    return 0


def scene_videos(root: Path, quality: str, scene: str) -> list[Path]:
    folder = root / "build" / "media" / quality / scene / "videos"
    return sorted((path for path in folder.rglob("*.mp4") if path.is_file()), key=lambda path: path.stat().st_mtime) if folder.is_dir() else []


def video_length(path: Path) -> tuple[float, float]:
    """The exact length of a video: frames divided by the frame rate."""
    probe = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
         "stream=nb_read_frames,r_frame_rate", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout)["streams"][0]
    rate = Fraction(probe["r_frame_rate"])
    return int(probe["nb_read_frames"]) / rate, 1 / rate


def cmd_assemble(args):
    config = video_config.load(args.root)
    script = load_script(config.root)
    language = config.lang
    quality = args.quality
    out = config.root / "out"
    out.mkdir(exist_ok=True)
    film, parts, chapters, words = [], [], [], []
    cursor = 0.0
    print("Scene videos on the timeline:")
    for scene in script.order:
        timing = speech.load_timing(config.root, scene)
        timeline_path = config.root / "build" / "timing" / quality / f"{scene}.json"
        if not timeline_path.is_file():
            raise RuntimeError(f"{scene}: no timeline at quality '{quality}'. Do: videogen render --quality {quality} {scene}")
        actual = json.loads(timeline_path.read_text(encoding="utf-8"))
        if actual["track_hash"] != speech.track_hash(script, scene, timing):
            raise RuntimeError(f"{scene}: the video is older than the narration. Do: videogen render --quality {quality} {scene}")
        videos = scene_videos(config.root, quality, scene)
        if not videos:
            raise RuntimeError(f"{scene}: no video at quality '{quality}'. Do: videogen render --quality {quality} {scene}")
        video = videos[-1]
        if video.stat().st_mtime < timeline_path.stat().st_mtime - 5:
            raise RuntimeError(f"{scene}: the video is older than its timeline. Do: videogen render --quality {quality} {scene}")
        length, frame = video_length(video)
        if abs(length - actual["total"]) > 1.5 * frame:
            raise RuntimeError(f"{scene}: the video is {length:.3f} s long, its timeline {actual['total']:.3f} s. Do: videogen render --quality {quality} {scene}")
        track = np.zeros(int(round(length * SAMPLE_RATE)), dtype=np.float32)
        for key, start, _end in actual["beats"]:
            clip = speech.read_wav(speech.clip_path(config.root, scene, key))
            offset = int(round(start * SAMPLE_RATE))
            if offset + len(clip) > len(track):
                raise RuntimeError(f"{scene}/{key}: the voice clip does not fit in its beat.")
            track[offset:offset + len(clip)] += clip
            # The service gives the time of each word, but usually without the punctuation.
            # The subtitles show the words of the script when their number agrees.
            timed = timing["beats"][key]["words"]
            shown = (timing["beats"][key].get("spoken") or beat_text(script, scene, key)).split()
            for index, (word_start, word_duration, word) in enumerate(timed):
                text = shown[index] if len(shown) == len(timed) else word
                words.append((cursor + start + float(word_start), float(word_duration), text))
        film.append(track)
        parts.append(video)
        number, title = script.chapters[scene]
        chapters.append((cursor, f"{number}. {title}" if number else title or language.text["opening"]))
        print(f"  {scene}: {length:7.2f} s, starts at {cursor:7.2f} s")
        cursor += length

    with tempfile.TemporaryDirectory() as tmp:
        listing = Path(tmp) / "concat.txt"
        listing.write_text("".join(f"file '{path}'\n" for path in parts), encoding="utf-8")
        silent = Path(tmp) / "video_only.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(silent)], check=True)
        voice = out / "voice.wav"
        speech.write_wav(voice, np.concatenate(film))
        final = out / f"{config.out}_{QUALITIES[quality][1]}p.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(silent), "-i", str(voice), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
             "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", str(SAMPLE_RATE), "-ac", "2", "-c:a", "aac", "-b:a", "192k",
             "-movflags", "+faststart", "-shortest", str(final)],
            check=True,
        )
    cues = subtitles.group_cues(words, language.function_words)
    (out / f"{config.out}_{QUALITIES[quality][1]}p.srt").write_text(subtitles.srt_text(cues, cursor), encoding="utf-8")
    def clock(seconds: float) -> str:
        return f"{int(seconds // 60):02d}:{seconds % 60:05.2f}".replace(".", language.decimal_separator)

    (out / "chapters.txt").write_text("".join(f"{clock(start)} {title}\n" for start, title in chapters), encoding="utf-8")
    (out / "film.json").write_text(json.dumps(
        {"file": final.name, "duration": round(cursor, 3), "chapters": [{"start": round(start, 3), "title": title} for start, title in chapters]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{final}\n{cursor / 60:.1f} minutes, {len(cues)} subtitle lines. Files in {out}")


def beat_text(script, scene: str, key: str) -> str:
    for beat in script.beats[scene]:
        if beat.key == key:
            return beat.text
    return ""


def cmd_script(args):
    """script.md: the narration with time codes, for the user and for a new voice."""
    config = video_config.load(args.root)
    script = load_script(config.root)
    language = config.lang
    text = language.text
    cursor, rows = 0.0, []

    def clock(seconds: float) -> str:
        return f"{int(seconds // 60):02d}:{seconds % 60:05.2f}".replace(".", language.decimal_separator)

    for scene in script.order:
        timeline_path = config.root / "build" / "timing" / (args.quality or "") / f"{scene}.json"
        if not timeline_path.is_file():
            print(f"No timeline for {scene} at quality '{args.quality}'. The time codes start from zero for each chapter.")
        timeline = json.loads(timeline_path.read_text(encoding="utf-8")) if timeline_path.is_file() else {"beats": [[beat.key, 0.0, 0.0] for beat in script.beats[scene]], "total": 0.0}
        starts = {key: start for key, start, _end in timeline["beats"]}
        timing = speech.load_timing(config.root, scene)["beats"]
        number, title = script.chapters[scene]
        heading = f"{number}. {title}" if number else (title or text["opening"])
        rows.append(f"\n## {heading}  ({clock(cursor)})\n")
        rows.append(f"| {text['id']} | {text['start']} | {text['narration']} | {text['duration']} | {text['on_screen']} |")
        rows.append("|---|---|---|---|---|")
        for beat in script.beats[scene]:
            start = cursor + starts.get(beat.key, 0.0)
            seconds = f"{timing[beat.key]['dur']:.1f}".replace(".", language.decimal_separator)
            rows.append(f"| {beat.key} | {clock(start)} | {beat.text} | {seconds} | {beat.visual} |")
        cursor += timeline["total"]
    voice = f"{config.resolved_voice} ({config.engine}, {config.rate})"
    header = (
        f"# {config.title}: {text['script_title']}\n\n"
        f"- {text['duration']}: {int(cursor // 60)} min {cursor % 60:.0f} s\n"
        f"- {text['voice']}: {voice}\n"
        f"- {len(script.order)} {text['chapters']}, {script.beat_count} {text['beats']}\n\n"
        f"{text['note']}\n"
    )
    target = config.root / "script.md"
    target.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")
    print(f"{target} ({int(cursor // 60)} min {cursor % 60:.0f} s, {script.beat_count} beats)")


def cmd_sheet(args):
    """One frame at the end of each beat, in contact sheets: to verify the visuals fast."""
    config = video_config.load(args.root)
    script = load_script(config.root)
    out = config.root / "build" / "sheets" / args.quality
    out.mkdir(parents=True, exist_ok=True)
    width, columns, per_sheet = (768, 3, 9) if args.quality == "l" else (960, 2, 8)
    for scene in args.scenes or script.order:
        videos = scene_videos(config.root, args.quality, scene)
        timeline_path = config.root / "build" / "timing" / args.quality / f"{scene}.json"
        if not videos or not timeline_path.is_file():
            print(f"{scene}: no video at quality '{args.quality}'")
            continue
        actual = json.loads(timeline_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for key, _start, end in actual["beats"]:
                stamp = max(0.0, end - 0.3)
                target = Path(tmp) / f"{key}_at_{stamp:05.1f}s.png"
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{stamp:.3f}", "-i", str(videos[-1]), "-frames:v", "1", "-vf", f"scale={width}:-1", str(target)], check=True)
                frames.append(target)
            sheets = []
            for index in range(0, len(frames), per_sheet):
                sheet = out / f"{scene}_{index // per_sheet + 1:02d}.png"
                subprocess.run(
                    ["magick", "montage", "-label", "%t", *map(str, frames[index:index + per_sheet]), "-tile", f"{columns}x",
                     "-geometry", "+6+6", "-background", "#0b0f12", "-fill", "white", "-pointsize", "18", str(sheet)],
                    check=True,
                )
                sheets.append(sheet)
        for sheet in sheets:
            print(sheet)


def cmd_voice_adopt(args):
    config = video_config.load(args.root)
    script = load_script(config.root)
    adopted, skipped = speech.adopt_recordings(script, config, Path(args.folder), force=args.force)
    print(f"{adopted} beats adopted, {skipped} skipped. The scenes follow the new length of the clips when they render again.")


def cmd_options(args):
    """The data for the menus of the skill: languages, engines, voices."""
    data = {"template": str(paths.template_root()), "version": __version__, "languages": [], "engines": []}
    for code, language in langs.LANGS.items():
        data["languages"].append({"code": code, "name": language.name, "voices": {engine.id: engine.voices(language) for engine in ENGINES.values()}})
    for engine in ENGINES.values():
        status = engine.status()
        data["engines"].append({"id": engine.id, "name": engine.name, "available": status.available, "detail": status.detail})
    if args.online:
        online = {}
        for code in langs.LANGS:
            try:
                online[code] = [voice["ShortName"] for voice in ENGINES["edge-tts"].online_voices(code)]
            except Exception as error:   # no connection: the menus use the default voices
                online[code] = []
                print(f"No online voices for {code}: {error}", file=sys.stderr)
        data["online_voices"] = online
    print(json.dumps(data, indent=1, ensure_ascii=False))


def cmd_new(args):
    folder = Path(args.folder).resolve()
    if folder.exists() and any(folder.iterdir()):
        raise RuntimeError(f"{folder} is not empty. `videogen new` needs a new or empty folder.")
    if args.language not in langs.LANGS:
        raise ValueError(f"Unknown language '{args.language}'. Available: {', '.join(langs.LANGS)}")
    if args.engine not in ENGINES:
        raise ValueError(f"Unknown engine '{args.engine}'. Available: {', '.join(ENGINES)}")
    config = video_config.VideoConfig(root=folder, title=args.title or folder.name, language=args.language, engine=args.engine, voice=args.voice)
    text = config.lang.text
    templates = paths.template_root() / "videogen" / "templates"
    for source in sorted(templates.rglob("*.tmpl")):
        relative = source.relative_to(templates).as_posix()[:-5]
        content = source.read_text(encoding="utf-8")
        for name, value in {"__TITLE__": config.title, "__LANGUAGE__": config.language, "__SLUG__": config.out,
                            "__BEAT_1__": text["beat_1"], "__VISUAL_1__": text["visual_1"],
                            "__BEAT_2__": text["beat_2"], "__VISUAL_2__": text["visual_2"]}.items():
            content = content.replace(name, value)
        target = folder / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    (folder / paths.CONFIG_NAME).write_text(video_config.render(config), encoding="utf-8")
    (folder / ".gitignore").write_text("build/\nout/\nscript.md\n", encoding="utf-8")
    print(f"Video project in {folder}: narration.py, scenes/ch00_intro.py, {paths.CONFIG_NAME}")
    print("Next: videogen extract <url>  (optional), then write narration.py and the scenes, then videogen tts, check, render, assemble.")


def fetch(url: str, timeout: int = 60) -> bytes:
    import urllib.request

    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AIVideoGenerator"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def cmd_extract(args):
    """A web article (or a local file) to text and figures, in build/source."""
    root = _video_root_or_here(args.root)
    out = root / "build" / "source"
    figures = out / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    source = args.source
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import trafilatura
    except ImportError as error:
        raise RuntimeError("The package trafilatura is not installed. Do: uv pip install -e '.[extract]' in the template folder") from error
    source_language = ""
    if re.match(r"https?://", source):
        html = fetch(source).decode("utf-8", errors="replace")
        found = re.search(r"<html[^>]+lang=[\"']([A-Za-z-]+)", html)
        source_language = found.group(1).split("-")[0].lower() if found else ""
        document = trafilatura.extract(html, output_format="markdown", include_images=True, include_links=True, with_metadata=True)
        if not document:
            raise RuntimeError("The page has no readable article text. The site can need a login, or it can block the download. Read it with your tools and save the text in build/source/article.md.")
        header = f"source: {source}\n"
        raw = html
    else:
        path = Path(source)
        if not path.is_file():
            raise LookupError(f"No file: {path}")
        header = f"source: {path.resolve()}\n"
        if path.suffix.lower() in (".html", ".htm"):
            raw = path.read_text(encoding="utf-8", errors="replace")
            document = trafilatura.extract(raw, output_format="markdown", include_images=True, include_links=True, with_metadata=True) or ""
        elif path.suffix.lower() == ".pdf":
            if not shutil.which("pdftotext"):
                raise RuntimeError("For a PDF, install poppler-utils (pdftotext), or change the PDF to text with your tools.")
            document = subprocess.run(["pdftotext", "-layout", str(path), "-"], check=True, capture_output=True, text=True).stdout
            raw = ""
        else:
            document = path.read_text(encoding="utf-8", errors="replace")
            raw = ""
    if source_language:
        header += f"language of the source: {source_language}\n"
    (out / "article.md").write_text(header + document + "\n", encoding="utf-8")
    urls = []
    for url in re.findall(r"!\[[^\]]*\]\(([^)\s]+)", document):
        if url not in urls:
            urls.append(url)
    match = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', raw)
    if match and match.group(1) not in urls:
        urls.insert(0, match.group(1))
    index = []
    for number, url in enumerate(urls[: args.limit], start=1):
        try:
            data = fetch(url)
            suffix = Path(url.split("?")[0]).suffix.lower()
            if suffix not in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"):
                suffix = ".img"
            name = f"fig_{number:02d}{suffix}"
            (figures / name).write_bytes(data)
            index.append(f"- {name}: {url}")
        except Exception as error:
            index.append(f"- (not downloaded: {error}) {url}")
    (figures / "index.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    print(f"{out / 'article.md'}: {len(document)} characters, {document.count(chr(10) + chr(10))} paragraphs"
          + (f", source language {source_language}" if source_language else ""))
    print(f"{figures}: {len(urls)} figures in the article, {min(len(urls), args.limit)} downloaded (index.md has the list)")


def _video_root_or_here(root):
    try:
        return paths.in_video(root)
    except LookupError:
        return Path(root or Path.cwd()).resolve()


def cmd_doctor(args):
    """Verify the tools. Exit status 1 when something necessary is missing."""
    cache = paths.cache_root()
    problems, notes = [], []

    def line(ok: bool, name: str, detail: str, necessary: bool = True) -> None:
        print(f"{'OK      ' if ok else 'MISSING '}{name}: {detail}")
        if not ok:
            (problems if necessary else notes).append(f"{name}: {detail}")

    template = paths.template_root()
    try:
        revision = subprocess.run(["git", "-C", str(template), "describe", "--always", "--dirty"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        revision = "no git"
    print(f"AIVideoGenerator {__version__} in {template} ({revision})")
    print(f"Tools in {cache}" + ("  (set by AIVIDEOGEN_CACHE)" if os.environ.get("AIVIDEOGEN_CACHE") else ""))
    in_venv = Path(sys.prefix).resolve() == (cache / "venv").resolve()
    line(in_venv, "python environment", f"{'venv of the cache' if in_venv else sys.prefix} (Python {sys.version.split()[0]})")
    for module, necessary in (("manim", True), ("edge_tts", True), ("faster_whisper", False), ("trafilatura", False)):
        try:
            imported = __import__(module)
            line(True, f"package {module}", f"version {getattr(imported, '__version__', '?')}", necessary)
        except ImportError:
            line(False, f"package {module}", "not installed" + ("" if necessary else " (optional: see the extras in pyproject.toml)"), necessary)
    for tool, necessary in (("ffmpeg", True), ("ffprobe", True), ("magick", False), ("pdftotext", False)):
        found = shutil.which(tool) or shutil.which(str(paths.venv_bin() / tool)) or None
        line(found is not None, tool, found or "not found", necessary)
    tex = paths.tex_bin()
    line(tex is not None, "TeX Live", str(tex) if tex else "not installed")
    if tex:
        done = subprocess.run([sys.executable, "-c", LATEX_TEST], env=tool_env(template, "dry"), capture_output=True, text=True)
        line("LATEX_OK" in done.stdout, "LaTeX compilation", "MathTex compiles" if "LATEX_OK" in done.stdout else "MathTex does not compile: " + done.stderr.strip()[-300:])
    for engine in ENGINES.values():
        status = engine.status()
        line(status.available, f"speech engine {engine.id}", status.detail)
    if args.online:
        edge = ENGINES["edge-tts"]
        for language in langs.LANGS.values():
            voice = language.voices[edge.id][0]
            try:
                clip = edge.synthesize(language.text["test_sentence"], voice, "+0%")
                line(len(clip.samples) > 1000, f"voice {voice}", f"{len(clip.samples) / SAMPLE_RATE:.2f} s of audio from the service", False)
            except Exception as error:
                line(False, f"voice {voice}", str(error)[:160], False)
    print(f"GPU: {'nvidia-smi found' if shutil.which('nvidia-smi') else 'no nvidia-smi'} (only for local speech engines)")
    for note in notes:
        print(f"NOTE: {note}")
    if problems:
        print(f"\n{len(problems)} problem(s). Correct them with: tools/setup.sh")
        if args.fix:
            subprocess.run([str(template / "tools" / "setup.sh")], check=True)
            return cmd_doctor(argparse.Namespace(online=False, fix=False))
        return 1
    print("\nAll the necessary tools are ready.")
    return 0


def cmd_selftest(args):
    """The full pipeline on examples/demo: the proof that the tools work on this computer."""
    demo = paths.template_root() / "examples" / "demo"
    config = video_config.load(demo)
    script = load_script(demo)
    started, failures = time.time(), []
    print(f"Selftest of videogen {__version__} on {demo.name} ({script.beat_count} beats)")
    try:
        if not args.skip_tts:
            speech.synthesize(script, config, get_engine(config.engine), log=lambda message: None)
        print("OK      tts")
        stats = run_scenes(demo, script, script.order, "l", args.jobs, dry_run=True, log=lambda message: print("        " + message))
        if stats["failed"] or stats["layout"]:
            raise RuntimeError(f"{stats['layout']} layout problems, failed: {stats['failed']}")
        print("OK      check (no layout problem)")
        if not args.skip_render:
            stats = run_scenes(demo, script, script.order, "l", args.jobs, log=lambda message: None)
            if stats["failed"]:
                raise RuntimeError(f"render failed: {stats['failed']}")
            print("OK      render")
            cmd_assemble(argparse.Namespace(root=demo, quality="l"))
            final = demo / "out" / f"{config.out}_480p.mp4"
            length, _frame = video_length(final)
            if length < 30:
                raise RuntimeError(f"the film is only {length:.1f} s long")
            print(f"OK      assemble ({final.stat().st_size / 1048576:.1f} MB, {length:.1f} s)")
        print(f"SELFTEST PASSED in {time.time() - started:.0f} s")
        return 0
    except Exception as error:
        print(f"SELFTEST FAILED: {error}")
        return 1


def _normalize(text: str) -> str:
    return " ".join("".join(character if character.isalnum() else " " for character in text.lower()).split())


def cmd_transcript(args):
    """Transcribe the voice clips with an offline speech recognizer, and compare the result
    with the script. This is how you verify the pronunciation of names: you cannot hear the clips."""
    try:
        import faster_whisper
    except ImportError as error:
        raise RuntimeError("The package faster-whisper is not installed. Install the extra 'qa' of the template.") from error
    config = video_config.load(args.root)
    script = load_script(config.root)
    clips, expected, cursor, gap = [], [], 0.0, 0.6
    for scene in script.order:
        timing = speech.load_timing(config.root, scene)
        for beat in script.beats[scene]:
            raw = subprocess.run(
                ["ffmpeg", "-v", "error", "-i", str(speech.clip_path(config.root, scene, beat.key)), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                check=True, capture_output=True,
            ).stdout
            audio = np.frombuffer(raw, dtype=np.float32)
            expected.append((cursor, cursor + len(audio) / 16000, f"{scene}/{beat.key}", timing["beats"][beat.key].get("spoken") or beat.text))
            clips.extend([audio, np.zeros(int(gap * 16000), dtype=np.float32)])
            cursor += len(audio) / 16000 + gap
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = faster_whisper.WhisperModel(args.model, device="cpu", compute_type="int8", cpu_threads=args.threads)
        # The recognizer gets the samples directly: its file reader does not agree with the
        # audio library that Manim uses.
        segments, _ = model.transcribe(np.concatenate(clips), language=config.language, beam_size=5, word_timestamps=True)
        words = [(word.start, word.end, word.word.strip()) for segment in segments for word in (segment.words or [])]
    from difflib import SequenceMatcher
    rows = []
    for start, end, label, spoken_text in expected:
        heard = " ".join(word for begin, finish, word in words if start <= (begin + finish) / 2 < end)
        rows.append((SequenceMatcher(None, _normalize(spoken_text), _normalize(heard)).ratio(), label, spoken_text, heard))
    for ratio, label, spoken_text, heard in sorted(rows):
        if ratio < args.threshold or args.show:
            print(f"[{ratio:.2f}] {label}: {heard}" + ("" if ratio >= args.threshold else f"\n       script: {spoken_text}"))
    flagged = [label for ratio, label, _s, _h in rows if ratio < args.threshold]
    print(f"{len(rows)} clips transcribed. Mean similarity {np.mean([row[0] for row in rows]):.3f}. "
          + ("The voice says the script." if not flagged else f"{len(flagged)} clips are different from the script: {' '.join(flagged)}"))
    return 1 if flagged else 0


def cmd_sync(args):
    """Verify the film: each voice clip must start when its scene put it on the time line."""
    config = video_config.load(args.root)
    script = load_script(config.root)
    out = config.root / "out"
    film = out / f"{config.out}_{QUALITIES[args.quality][1]}p.mp4"
    if not film.is_file() or not (out / "film.json").is_file():
        raise LookupError(f"No film at quality '{args.quality}' in {out}. Do: videogen assemble --quality {args.quality}")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(film), "-vn", "-f", "f32le", "-ac", "1", "-ar", str(SAMPLE_RATE), "-"], check=True, capture_output=True).stdout
    audio = np.frombuffer(raw, dtype=np.float32)
    starts = [chapter["start"] for chapter in json.loads((out / "film.json").read_text(encoding="utf-8"))["chapters"]]
    gaps = []
    for scene, chapter_start in zip(script.order, starts):
        actual = json.loads((config.root / "build" / "timing" / args.quality / f"{scene}.json").read_text(encoding="utf-8"))
        for key, start, _end in actual["beats"]:
            begin = chapter_start + start
            window = audio[int((begin - 0.25) * SAMPLE_RATE):int((begin + 1.5) * SAMPLE_RATE)]
            loud = np.flatnonzero(np.abs(window) > 0.015)
            gaps.append((begin - 0.25 + loud[0] / SAMPLE_RATE - begin if loud.size else float("nan"), f"{scene}/{key}"))
    values = np.array([gap for gap, _label in gaps])
    stray = [label for gap, label in gaps if not 0.02 < gap < 0.6]   # some voices start slowly
    print(f"{len(gaps)} clips. The voice starts {np.nanmean(values) * 1000:.0f} ms after the start of its beat on average "
          f"(the first word needs some time). Minimum {np.nanmin(values) * 1000:.0f} ms, maximum {np.nanmax(values) * 1000:.0f} ms.")
    print("OK: voice and video agree." if not stray else f"PROBLEM: {len(stray)} clips do not start where the time line says: {' '.join(stray[:8])}")
    return 0 if not stray else 1


def _add_root(parser):
    parser.add_argument("--root", type=Path, default=None, help="the folder of the video project (default: the nearest video.toml)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="videogen", description=__doc__)
    parser.add_argument("--version", action="version", version=f"videogen {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, function, help_text in (
        ("doctor", cmd_doctor, "verify the tools of this computer"),
        ("options", cmd_options, "languages, engines and voices, in JSON: the data for the menus"),
        ("new", cmd_new, "start a video project in a new folder"),
        ("extract", cmd_extract, "a web article or a local file to text and figures"),
        ("tts", cmd_tts, "make the voice clips of the narration"),
        ("check", cmd_check, "run the scenes without a video: find layout, cue and pace problems"),
        ("render", cmd_render, "render the scenes"),
        ("sheet", cmd_sheet, "contact sheets with one frame at the end of each beat"),
        ("assemble", cmd_assemble, "join the scenes, add the voice, write subtitles and chapters"),
        ("script", cmd_script, "write script.md: the narration with time codes"),
        ("voice-adopt", cmd_voice_adopt, "use your recordings as the voice-over"),
        ("selftest", cmd_selftest, "run the full pipeline on the demo video"),
        ("transcript", cmd_transcript, "transcribe the voice clips offline: verify the pronunciation"),
        ("sync", cmd_sync, "verify that voice and video agree in the film"),
    ):
        sub = commands.add_parser(name, help=help_text, description=function.__doc__)
        sub.set_defaults(function=function)
        if name in ("tts", "check", "render", "sheet", "assemble", "script", "extract", "voice-adopt", "transcript", "sync"):
            _add_root(sub)
        if name in ("check", "render", "selftest"):
            sub.add_argument("--jobs", type=int, default=max(1, min(6, (os.cpu_count() or 4) // 4)), help="scenes that render at the same time")
        if name in ("tts", "check", "render", "sheet"):
            sub.add_argument("scenes", nargs="*", help="only these scenes, for example ch02 ch03")
        if name in ("render", "assemble", "sheet"):
            sub.add_argument("--quality", choices=QUALITIES, default={"render": "h", "assemble": "h", "sheet": "l"}[name], help="l = 480p15 preview, h = 1080p60 final")
    commands.choices["doctor"].add_argument("--online", action="store_true", help="also test the speech service with one short sentence for each language")
    commands.choices["doctor"].add_argument("--fix", action="store_true", help="correct the problems with tools/setup.sh")
    commands.choices["options"].add_argument("--online", action="store_true", help="also get the full list of voices from the speech service")
    new = commands.choices["new"]
    new.add_argument("folder", help="the folder of the new video project")
    new.add_argument("--title", help="the title of the video (default: the name of the folder)")
    new.add_argument("--language", default="en", help="the narration language (default: en)")
    new.add_argument("--engine", default="edge-tts", help="the speech engine")
    new.add_argument("--voice", help="a voice of the engine (default: the first voice of the language)")
    extract = commands.choices["extract"]
    extract.add_argument("source", help="a URL, or a local file: .html, .md, .txt, .pdf")
    extract.add_argument("--limit", type=int, default=30, help="maximum number of figures to download (default: 30)")
    commands.choices["tts"].add_argument("--force", action="store_true", help="make all the clips again")
    commands.choices["tts"].add_argument("--workers", type=int, default=4, help="clips that are made at the same time")
    commands.choices["script"].add_argument("--quality", choices=QUALITIES, help="use the time codes of a render at this quality")
    adopt = commands.choices["voice-adopt"]
    adopt.add_argument("folder", help="the folder of your recordings: <scene>_<beat>.wav")
    adopt.add_argument("--force", action="store_true", help="replace the beats that are already a recording")
    test = commands.choices["selftest"]
    test.add_argument("--skip-tts", action="store_true", help="use the voice clips that are in the demo folder")
    test.add_argument("--skip-render", action="store_true", help="only the voice clips and the layout verification")
    listen = commands.choices["transcript"]
    listen.add_argument("--model", default="small", help="size of the offline recognizer: tiny, base, small, medium (default: small)")
    listen.add_argument("--threads", type=int, default=12, help="processor threads of the recognizer")
    listen.add_argument("--threshold", type=float, default=0.9, help="a clip with a lower similarity is different from the script")
    listen.add_argument("--show", action="store_true", help="print the transcription of each clip")
    commands.choices["sync"].add_argument("--quality", choices=QUALITIES, default="h", help="the quality of the film to verify")
    return parser


def main() -> int:
    load_env(paths.template_root() / ".env")
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "root", None) is not None or hasattr(args, "scenes"):
        try:
            load_env(paths.in_video(args.root) / ".env")
        except LookupError:
            pass
    try:
        result = args.function(args)
        return int(result or 0)
    except (LookupError, ValueError, RuntimeError, KeyError, FileNotFoundError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
