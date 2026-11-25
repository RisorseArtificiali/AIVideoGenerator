"""Tests of the look of a video project: a background image with a logo, the band at the bottom
that the scenes keep free for the subtitles, and the subtitles drawn into the film."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import manim
import pytest
from PIL import Image, ImageFont
from manim import VGroup

from videogen import blocks, config as video_config
from videogen import paths, style, subtitles, theme

RED, GREEN, BLUE, YELLOW = (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)
ORANGE = theme.SERIES["orange"]
NIGHT = (22, 28, 32)   # the background of the template: #161C20

STYLE = """
[style]
background = "bg.png"
logo = "logo.png"
logo_height = 108
subtitle_band = 250

[subtitles]
font = "Inter"
size = 88
color = "#FF0000"
fonts = "fonts"
"""


def project(tmp_path: Path, text: str = "") -> video_config.VideoConfig:
    """A video project with only its configuration."""
    (tmp_path / "video.toml").write_text('title = "Prova"\nlanguage = "it"\n' + text, encoding="utf-8")
    return video_config.load(tmp_path)


def new_project(folder: Path):
    """`videogen new` in a new folder, with the voice of the template."""
    command = [sys.executable, "-m", "videogen.cli", "new", str(folder), "--language", "it", "--title", "Prova"]
    return subprocess.run(command, capture_output=True, text=True)


def half(path: Path, size, left, right, mode="RGB"):
    """An image with two colors: the left half and the right half."""
    picture = Image.new(mode, size, left)
    box = (size[0] // 2, 0, size[0], size[1])
    picture.paste(Image.new(mode, (size[0] - size[0] // 2, size[1]), right), box)
    picture.save(path)


def a_font_file():
    """A TrueType file of this computer, or None."""
    if not shutil.which("fc-match"):
        return None
    found = subprocess.run(["fc-match", "-f", "%{file}", "sans"], capture_output=True, text=True).stdout.strip()
    return Path(found) if found and Path(found).is_file() else None


def ffmpeg_draws_subtitles():
    listing = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    return " ass " in listing


def need_ffmpeg_with_subtitles():
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg is not installed")
    if not ffmpeg_draws_subtitles():
        pytest.skip("this ffmpeg cannot draw subtitles")


def test_configuration_reads_the_style(tmp_path):
    config = project(tmp_path, STYLE)
    assert config.background == "bg.png" and config.logo == "logo.png"
    assert config.logo_height == 108 and config.subtitle_band == 250
    shown = config.subtitles
    assert (shown.font, shown.size, shown.color, shown.fonts) == ("Inter", 88, "#FF0000", "fonts")
    plain = project(tmp_path)
    assert plain.background is None and plain.logo is None and plain.subtitle_band == 0 and plain.subtitles is None
    small = project(tmp_path, '[style]\nlogo = "logo.png"\n')
    assert small.logo_height == 140   # a small logo at 1080p


def test_configuration_refuses_impossible_values(tmp_path):
    with pytest.raises(ValueError, match="subtitle_band"):
        project(tmp_path, '[style]\nsubtitle_band = -5\n')
    with pytest.raises(ValueError, match="size"):
        project(tmp_path, '[subtitles]\nfont = "Inter"\nsize = 0\n')


def test_a_new_project_gets_the_look_of_the_template(tmp_path):
    """Every new video has the background, the logo, the band and the subtitles: `videogen new`
    writes them in video.toml, with paths that lead to the files of the template from any folder."""
    import tomllib

    folder = tmp_path / "my-video"
    done = new_project(folder)
    assert done.returncode == 0, done.stderr
    look = tomllib.loads((paths.template_root() / "videogen" / "templates" / "look.toml").read_text(encoding="utf-8"))
    config = video_config.load(folder)
    assert config.subtitle_band == look["style"]["subtitle_band"]
    assert config.logo_height == look["style"]["logo_height"]
    wanted = tuple(look["subtitles"][key] for key in ("font", "size", "color"))
    assert (config.subtitles.font, config.subtitles.size, config.subtitles.color) == wanted
    assert (folder / config.background).is_file() and (folder / config.logo).is_file()
    assert subtitles.font_file(config.subtitles.font, folder / config.subtitles.fonts) is not None
    assert Path(config.background).is_absolute()   # out of the repository: a clear path, not a climb of "../"


def test_the_blocks_keep_the_band_and_the_logo_corner_free():
    """With their default positions, the blocks build screens that fit above the band of the look
    of the template (140 pixels) and away from its logo (180 pixels high, 44 from the edges)."""
    band = 140 * 8 / 1080
    corner = (5.9, 2.3)
    rows = [("Model A", "large", 71, BLUE), ("Model B", "medium", 58, ORANGE), ("Model C", None, 55, BLUE),
            ("Model D", None, 50, BLUE), ("Model E", None, 45, BLUE), ("Model F", "small", 42, BLUE)]
    series = [("A", BLUE, [(1, 10), (2, 20), (3, 30), (4, 40)]), ("B", ORANGE, [(1, 12), (2, 25), (3, 45), (4, 70)])]
    columns = [("First", "one pass"), ("Second", "two passes"), ("Third", None)]
    table = blocks.compare_table(columns, ("one", "two", "three", "four", "five"))
    table_rows = VGroup(*[table.row(index, ["12", "24", "same"]) for index in range(5)])
    chart = blocks.column_chart(["A", "B", "C", "D"], [42, 58, 35, 71], (0, 80), y_ticks=[0, 40, 80], y_fmt=str,
                                x_label="condition", title="Four", note="Data.")
    bars = blocks.ranked_bars(rows, (0, 80), x_ticks=[0, 40, 80], x_label="score", title="Six models", note="Data.")
    points = [(f"M{index}", 60 + index, BLUE) for index in range(6)]
    dots = blocks.dot_plot(points, (55, 70), x_ticks=[55, 60, 65, 70], x_label="score", title="Points", note="Data.")
    options = dict(x_label="steps", y_label="score", title="Score", legend_entries=True, reference=(50, "level"))
    ticks = dict(x_ticks=[1, 2, 3, 4], y_ticks=[0, 40, 80])
    trend = blocks.line_chart(series, (0, 5), (0, 80), note="Data.", **ticks, **options)
    panels = [("one", series), ("two", series), ("three", series)]
    multiples = blocks.small_multiples(panels, (0, 5), (0, 80), x_ticks=[1, 4], y_ticks=[0, 80], x_label="steps",
                                       note="Data.")
    screens = {
        "column_chart": chart.everything(),
        "ranked_bars": bars.everything(),
        "dot_plot": dots.everything(),
        "line_chart": trend.everything(),
        "small_multiples": multiples.everything(),
        "compare_table": VGroup(table.rules, table.headers, table.subheaders, table.labels, table_rows),
    }
    for name, screen in screens.items():
        assert theme.layout_issues([screen], band=band, corner=corner) == [], name


def test_text_in_the_subtitle_band_is_reported():
    low = theme.T("low").move_to([0, -3.7, 0])
    high = theme.T("high").move_to([0, -2.6, 0])
    issues = theme.layout_issues([low, high], band=1.0)
    assert [issue.kind for issue in issues] == ["in-band"]
    assert issues[0].describe() == 'in the subtitle band: "low"'
    assert theme.layout_issues([low]) == []   # without a band, the frame ends at -4


def test_text_under_the_logo_is_reported():
    under = theme.T("corner").move_to([6.3, 3.2, 0])
    below = theme.T("lower").move_to([6.3, 1.0, 0])
    issues = theme.layout_issues([under, below], corner=(5.9, 2.3))
    assert [issue.kind for issue in issues] == ["under-logo"]
    assert issues[0].describe() == 'under the logo: "corner"'
    assert theme.layout_issues([under]) == []   # without a logo, the frame ends in the corner


def test_ass_subtitles_carry_the_style():
    red = video_config.SubtitleStyle(font="Inter", size=88, color="#FF0000")
    text = subtitles.ass_text([(0.0, 1.5, "Ciao, mondo."), (62.0, 63.25, "Seconda riga")], red, limit=64.0)
    lines = text.splitlines()
    assert "PlayResX: 1920" in lines and "PlayResY: 1080" in lines
    (style_line,) = [line for line in lines if line.startswith("Style:")]
    assert style_line.startswith("Style: Default,Inter,88,&H000000FF,")
    assert style_line.endswith(",2,60,60,36,1")   # at the bottom, in the center, 36 pixels from the edge
    assert "Dialogue: 0,0:00:00.00,0:00:01.50,Default,,0,0,0,,Ciao, mondo." in lines
    assert "Dialogue: 0,0:01:02.00,0:01:03.25,Default,,0,0,0,,Seconda riga" in lines
    blue = subtitles.ass_text([], video_config.SubtitleStyle(font="Inter", size=40, color="#0000FF"), 1.0)
    assert ",40,&H00FF0000," in blue   # the format of these subtitles writes blue before red
    corrected = subtitles.ass_text([], red, 1.0, factor=0.743)
    assert ",Inter,118," in corrected   # 88 / 0.743: the letters come out as a size of 88


def test_the_font_file_is_found_by_its_family_name(tmp_path):
    source = a_font_file()
    if not source:
        pytest.skip("no TrueType font on this computer")
    (tmp_path / "fonts").mkdir()
    family = ImageFont.truetype(str(source), 20).getname()[0]
    shutil.copy(source, tmp_path / "fonts" / "renamed-regular.ttf")
    assert subtitles.font_file(family.upper(), tmp_path / "fonts") == tmp_path / "fonts" / "renamed-regular.ttf"
    assert subtitles.font_file("a family that is not here", tmp_path / "fonts") is None
    assert subtitles.font_file(family, None) is None and subtitles.font_file(family, tmp_path / "no-folder") is None


def test_the_size_is_the_size_of_the_font(tmp_path):
    """A size of 88 gives letters as tall as in the font at 88, although the filter that draws
    the subtitles scales each font with its own metrics."""
    need_ffmpeg_with_subtitles()
    source = a_font_file()
    if not source:
        pytest.skip("no TrueType font on this computer")
    (tmp_path / "fonts").mkdir()
    family = ImageFont.truetype(str(source), 20).getname()[0]
    shutil.copy(source, tmp_path / "fonts" / "regular.ttf")
    style = video_config.SubtitleStyle(font=family, size=88, color="#FF0000", fonts="fonts")
    factor = subtitles.letters_factor(family, tmp_path / "fonts")
    assert 0.5 < factor < 1.6
    film = tmp_path / "film.mp4"
    black = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=1920x1080:r=15:d=1"]
    subprocess.run([*black, str(film)], check=True)
    ass = tmp_path / "film.ass"
    ass.write_text(subtitles.ass_text([(0.2, 0.9, "H")], style, 1.0, factor), encoding="utf-8")
    subtitles.burn(film, ass, tmp_path / "fonts")
    for moment in (0.05, 0.5):
        command = ["ffmpeg", "-v", "error", "-y", "-ss", str(moment), "-i", str(film), "-frames:v", "1"]
        subprocess.run([*command, str(tmp_path / "frame.png")], check=True)
        picture = Image.open(tmp_path / "frame.png").convert("RGB")
        # Only the pixels that are really red: the coding of the film leaves a dark halo around the letters.
        box = picture.getchannel("R").point(lambda value: 255 if value > 180 else 0).getbbox()
        if moment == 0.05:
            assert box is None   # before the line: nothing
    left, top, right, bottom = box
    wanted = ImageFont.truetype(str(source), 88)
    assert abs((bottom - top) - (wanted.getbbox("H")[3] - wanted.getbbox("H")[1])) <= 2   # as tall as in the font
    # in the center, at the bottom, above the margin of 36
    assert abs((left + right) / 2 - 960) <= 3 and 1000 <= bottom <= 1044


def test_a_subtitle_stops_before_the_next_one():
    """Two lines that the voice says without a pause: in the film there is one line at a time."""
    red = video_config.SubtitleStyle(font="Inter", size=88, color="#FF0000")
    text = subtitles.ass_text([(0.0, 1.5, "first line,"), (1.3, 3.0, "second line.")], red, limit=64.0)
    first, second = [line for line in text.splitlines() if line.startswith("Dialogue:")][-2:]
    assert first == "Dialogue: 0,0:00:00.00,0:00:01.25,Default,,0,0,0,,first line,"
    assert second == "Dialogue: 0,0:00:01.30,0:00:03.00,Default,,0,0,0,,second line."


def test_background_covers_the_frame_with_the_logo_at_the_top_right(tmp_path):
    half(tmp_path / "bg.png", (40, 20), GREEN, RED)
    Image.new("RGB", (10, 10), BLUE).save(tmp_path / "logo.png")
    path = style.background_image(project(tmp_path, STYLE), width=160, height=90)
    assert path == tmp_path / "build" / "style" / "background_160x90.png"
    frame = Image.open(path).convert("RGB")
    assert frame.size == (160, 90)
    assert frame.getpixel((40, 45)) == GREEN and frame.getpixel((120, 45)) == RED   # the image covers the frame
    assert frame.getpixel((150, 8)) == BLUE and frame.getpixel((158, 2)) == RED     # the logo at the top right


def test_background_is_composed_again_when_a_source_changes(tmp_path):
    half(tmp_path / "bg.png", (40, 20), GREEN, RED)
    Image.new("RGB", (10, 10), BLUE).save(tmp_path / "logo.png")
    config = project(tmp_path, STYLE)
    path = style.background_image(config, width=160, height=90)
    composed = path.stat().st_mtime_ns
    time.sleep(0.02)
    style.background_image(config, width=160, height=90)
    assert path.stat().st_mtime_ns == composed   # nothing changed: the composed image stays
    half(tmp_path / "bg.png", (40, 20), YELLOW, YELLOW)
    style.background_image(config, width=160, height=90)
    assert Image.open(path).convert("RGB").getpixel((40, 45)) == YELLOW


def test_background_with_a_logo_only_and_a_transparent_logo(tmp_path):
    half(tmp_path / "logo.png", (10, 10), (0, 0, 0, 0), (0, 0, 255, 255), mode="RGBA")
    config = project(tmp_path, '[style]\nlogo = "logo.png"\nlogo_height = 108\n')
    frame = Image.open(style.background_image(config, width=160, height=90)).convert("RGBA")
    assert frame.getpixel((40, 45)) == NIGHT + (255,)
    assert frame.getpixel((148, 8)) == NIGHT + (255,) and frame.getpixel((154, 8)) == (0, 0, 255, 255)


def test_background_changes_only_with_a_complete_image(tmp_path, monkeypatch):
    """The scenes of a video render at the same time and share the background: none of them
    reads a file that another is still writing."""
    half(tmp_path / "bg.png", (40, 20), GREEN, RED)
    config = project(tmp_path, '[style]\nbackground = "bg.png"\n')
    path = style.background_image(config, width=160, height=90)

    half(tmp_path / "bg.png", (40, 20), YELLOW, YELLOW)   # a newer source: the image is composed again

    def interrupted_save(self, target, *args, **kwargs):
        Path(target).write_bytes(b"the first half of an image")
        raise OSError("no space left")

    monkeypatch.setattr(Image.Image, "save", interrupted_save)
    with pytest.raises(OSError, match="no space"):
        style.background_image(config, width=160, height=90)
    with Image.open(path) as picture:
        assert picture.convert("RGB").getpixel((40, 45)) == GREEN   # the image of before, whole
    assert list(path.parent.iterdir()) == [path]                     # and nothing half written next to it


def test_background_with_no_style_and_with_a_missing_file(tmp_path):
    assert style.background_image(project(tmp_path), width=160, height=90) is None
    config = project(tmp_path, '[style]\nbackground = "nope.png"\n')
    with pytest.raises(LookupError, match="nope.png"):
        style.background_image(config, width=160, height=90)


def test_the_camera_shows_the_background(tmp_path, monkeypatch):
    half(tmp_path / "bg.png", (40, 20), GREEN, RED)
    Image.new("RGB", (10, 10), BLUE).save(tmp_path / "logo.png")
    monkeypatch.setattr(manim.config, "pixel_width", 160)
    monkeypatch.setattr(manim.config, "pixel_height", 90)
    camera = manim.Camera()
    theme.apply_background(camera, project(tmp_path, STYLE))
    assert [int(value) for value in camera.background[8, 150][:3]] == [0, 0, 255]
    assert [int(value) for value in camera.background[45, 120][:3]] == [255, 0, 0]
    empty = manim.Camera()
    theme.apply_background(empty, project(tmp_path))
    assert [int(value) for value in empty.background[45, 120][:3]] == [0, 0, 0]   # the camera does not change


def test_subtitles_are_drawn_into_the_film(tmp_path):
    need_ffmpeg_with_subtitles()
    film = tmp_path / "film.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=320x180:r=15:d=1",
         "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-shortest", str(film)], check=True,
    )
    line_style = video_config.SubtitleStyle(font="Inter", size=88, color="#FF0000")
    ass = tmp_path / "film.ass"
    ass.write_text(subtitles.ass_text([(0.2, 0.9, "ROSSO")], line_style, 1.0), encoding="utf-8")
    subtitles.burn(film, ass)
    frame = tmp_path / "frame.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "0.5", "-i", str(film), "-frames:v", "1", str(frame)],
                   check=True)
    picture = Image.open(frame).convert("RGB")
    top, bottom = picture.crop((0, 0, 320, 120)), picture.crop((0, 120, 320, 180))

    def red(color):
        return color[0] > 100 and color[0] > 2 * color[1] and color[0] > 2 * color[2]

    assert any(red(color) for color in bottom.get_flattened_data()), "the subtitle is not in the film"
    assert all(color == (0, 0, 0) for color in top.get_flattened_data())
    command = ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(film)]
    probe = subprocess.run(command, capture_output=True, text=True)
    assert probe.stdout.split() == ["video", "audio"]   # the voice stays in the film


def test_check_reports_text_in_the_band_and_under_the_logo(tmp_path):
    folder = tmp_path / "video"
    done = new_project(folder)
    assert done.returncode == 0, done.stderr
    Image.new("RGB", (10, 10), BLUE).save(folder / "logo.png")
    (folder / "video.toml").write_text(
        'title = "Prova"\nlanguage = "it"\nengine = "edge-tts"\nrate = "+0%"\n'
        '[style]\nlogo = "logo.png"\nsubtitle_band = 250\n', encoding="utf-8",
    )
    (folder / "narration.py").write_text(
        "from collections import namedtuple\nBeat = namedtuple('Beat', 'key text visual')\n"
        "SCENE_ORDER = ['ch00']\nCHAPTERS = {'ch00': ('', '')}\n"
        "NARRATION = {'ch00': [Beat('a1', 'Una battuta.', 'due righe da spostare')]}\n", encoding="utf-8",
    )
    timing = folder / "build" / "timing" / "ch00.json"
    timing.parent.mkdir(parents=True)
    timing.write_text(json.dumps({"beats": {"a1": {"text": "Una battuta.", "dur": 1.0, "words": []}}}),
                      encoding="utf-8")
    (folder / "scenes" / "ch00_intro.py").write_text(
        "from manim import *\nfrom videogen.theme import *\n\n\nclass Low(NarratedScene):\n    scene_key = 'ch00'\n\n"
        "    def build(self):\n        with self.beat('a1'):\n"
        "            self.play(FadeIn(T('in basso').move_to([0, -3.6, 0])), "
        "FadeIn(T('sotto il logo').move_to([6.0, 2.85, 0])), run_time=0.3)\n"
        "            self.play(FadeIn(T('a sinistra del logo').move_to([3.0, 3.2, 0])), "
        "FadeIn(T('sotto, a destra').move_to([5.2, 1.2, 0])), run_time=0.3)\n",
        encoding="utf-8",
    )
    done = subprocess.run([sys.executable, "-m", "videogen.cli", "check", "--root", str(folder)],
                          capture_output=True, text=True)
    assert done.returncode == 1, done.stdout + done.stderr
    assert 'in the subtitle band: "in basso"' in done.stdout and 'under the logo: "sotto il logo"' in done.stdout
    reported = [line for line in done.stdout.splitlines() if line.startswith("  [layout]")]
    assert len(reported) == 2   # the lines to the left of the logo and under it are in their place
