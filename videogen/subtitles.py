"""Subtitles: the timed words of the voice-over, grouped in short lines, as an .srt file, or
drawn into the film as an ASS file."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace

from PIL import Image, ImageFont


def letters(word: str) -> str:
    return "".join(character for character in word.lower() if character.isalnum())


def ends_clause(word: str) -> bool:
    return len(word) > 1 and word[-1] in ".,:;?!»”)"


def group_cues(words, function_words=frozenset(), pause: float = 0.5, soft: int = 36, hard: int = 54) -> list[tuple[float, float, str]]:
    """Group timed words in subtitle lines. A line ends at a pause, after the punctuation of
    a sentence, or when it is long. A line does not end with (or start with) a short
    function word. `words` are (start in seconds, duration in seconds, word)."""
    cues, line, line_start, last_end = [], [], None, None
    for start, duration, word in words:
        paused = last_end is not None and start - last_end > pause
        joined = " ".join(line)
        too_long = bool(line) and (
            len(joined) > hard or (len(joined) > soft and letters(line[-1]) not in function_words and letters(word) not in function_words)
        )
        if line and (paused or too_long):
            cues.append((line_start, last_end + 0.25, joined))
            line, line_start = [], None
        if line_start is None:
            line_start = start
        line.append(word)
        last_end = start + duration
        if ends_clause(word) and len(" ".join(line)) >= 12:
            cues.append((line_start, last_end + 0.3, " ".join(line)))
            line, line_start, last_end = [], None, None
    if line:
        cues.append((line_start, last_end + 0.25, " ".join(line)))
    return cues


def srt_time(seconds: float) -> str:
    hours, rest = divmod(max(0.0, seconds), 3600)
    minutes, rest = divmod(rest, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{rest:06.3f}".replace(".", ",")


def srt_text(cues, limit: float) -> str:
    """The text of an .srt file. Each cue is at least 0.9 seconds and stops before the next."""
    out = []
    for index, (start, end, text) in enumerate(cues, start=1):
        next_start = cues[index][0] - 0.05 if index < len(cues) else limit
        out.append(f"{index}\n{srt_time(start)} --> {srt_time(min(max(end, start + 0.9), next_start))}\n{text}\n")
    return "\n".join(out)   # each item ends with a line break: the join makes the empty line between cues


def ass_time(seconds: float) -> str:
    """A time for subtitles that are drawn into the film: H:MM:SS.cc (hundredths of a second)."""
    hundredths = round(max(0.0, seconds) * 100)
    hours, rest = divmod(hundredths, 360_000)
    minutes, rest = divmod(rest, 6_000)
    return f"{hours}:{minutes:02d}:{rest / 100:05.2f}"


def ass_color(color: str) -> str:
    """"#RRGGBB" to the color of ASS, where blue comes before red: &H00BBGGRR."""
    red, green, blue = (int(color[index:index + 2], 16) for index in (1, 3, 5))
    return f"&H00{blue:02X}{green:02X}{red:02X}"


ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},{color},{color},&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,2,60,60,36,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def font_file(family: str, fonts: Path | None) -> Path | None:
    """The file of a family of fonts in a folder, or None. The name of the family is not
    case-sensitive."""
    if fonts is None or not fonts.is_dir():
        return None
    for path in sorted(fonts.iterdir()):
        if path.suffix.lower() not in (".ttf", ".otf"):
            continue
        try:
            if ImageFont.truetype(str(path), 20).getname()[0].lower() == family.lower():
                return path
        except OSError:
            continue
    return None


def letters_factor(family: str, fonts: Path | None) -> float:
    """How many pixels of em the subtitles draw for one unit of size with this font. The filter
    that draws the subtitles scales a font with the metrics of that font: with Inter, a size of
    88 gives letters of 65. With the file of the font, the size of the project becomes the size
    of the font. Without it, the factor is 1.0."""
    path = font_file(family, fonts)
    if path is None:
        return 1.0
    probe = 400
    with tempfile.TemporaryDirectory() as tmp:
        ass = Path(tmp) / "probe.ass"
        probe_style = SimpleNamespace(font=family, size=probe, color="#FFFFFF")
        ass.write_text(ass_text([(0.0, 1.0, "H")], probe_style, 1.0), encoding="utf-8")
        frame = Path(tmp) / "probe.png"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=1920x1080:r=5:d=0.2",
             "-frames:v", "1", "-vf", f"ass={ass.name}:fontsdir={fonts.resolve()}", str(frame)], check=True, cwd=tmp,
        )
        with Image.open(frame) as picture:
            box = picture.convert("RGB").getbbox()
    if box is None:
        return 1.0
    reference = ImageFont.truetype(str(path), 1000)
    cap = reference.getbbox("H")[3] - reference.getbbox("H")[1]
    return (box[3] - box[1]) / cap * 1000 / probe


def ass_text(cues, style, limit: float, factor: float = 1.0) -> str:
    """The cues as an ASS file, to draw the subtitles into the film: the style is the section
    `[subtitles]` of video.toml. The lines are at the bottom of a frame of 1920 by 1080, and
    each one stops before the next one, as in the .srt file. `factor` comes from `letters_factor`."""
    color = ass_color(style.color)
    text = ASS_HEADER.format(font=style.font, size=max(1, round(style.size / factor)), color=color)
    for index, (start, end, line) in enumerate(cues):
        next_start = cues[index + 1][0] - 0.05 if index + 1 < len(cues) else limit
        stop = min(max(end, start + 0.9), next_start)
        text += f"Dialogue: 0,{ass_time(start)},{ass_time(stop)},Default,,0,0,0,,{line}\n"
    return text


def burn(film: Path, ass: Path, fonts: Path | None = None) -> None:
    """Draw the subtitles into the film, in place. The voice is copied as it is."""
    options = {}
    if fonts:
        options["fontsdir"] = str(fonts.resolve())
    drawn = "ass=" + ass.name + "".join(f":{name}={value}" for name, value in options.items())
    temporary = film.with_name(film.stem + ".drawn.mp4")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(film.resolve()), "-vf", drawn, "-c:v", "libx264", "-crf", "18",
         "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(temporary.resolve())],
        check=True, cwd=ass.parent,
    )
    temporary.replace(film)
