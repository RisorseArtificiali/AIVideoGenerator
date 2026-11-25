"""The full pipeline on the demo video. It is slow, and it needs the network for the voice:
start it with AIVIDEOGEN_SELFTEST=1, or use the command `videogen selftest`."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest
from PIL import Image

pytestmark = [pytest.mark.pipeline, pytest.mark.skipif(
    not os.environ.get("AIVIDEOGEN_SELFTEST"), reason="Set AIVIDEOGEN_SELFTEST=1 to start the full pipeline.",
)]


def videogen(*arguments: str) -> str:
    done = subprocess.run([sys.executable, "-m", "videogen.cli", *arguments], capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr
    return done.stdout


def test_selftest():
    print(videogen("selftest"))


def test_a_project_with_a_style_shows_its_background_and_its_subtitles(tmp_path):
    """The pipeline on a project with a background image, a logo, a band and subtitles to draw."""
    folder = tmp_path / "clip"
    videogen("new", str(folder), "--language", "it", "--title", "Prova")
    (folder / "video.toml").write_text(
        'title = "Prova"\nlanguage = "it"\nengine = "edge-tts"\nrate = "+0%"\n'
        '[style]\nbackground = "bg.png"\nlogo = "logo.png"\nlogo_height = 108\nsubtitle_band = 250\n'
        '[subtitles]\nfont = "Inter"\nsize = 88\ncolor = "#FF0000"\n', encoding="utf-8",
    )
    picture = Image.new("RGB", (40, 20), (0, 255, 0))
    picture.paste(Image.new("RGB", (20, 20), (0, 0, 255)), (20, 0))   # red is only in the subtitles
    picture.save(folder / "bg.png")
    Image.new("RGB", (10, 10), (255, 255, 255)).save(folder / "logo.png")
    (folder / "narration.py").write_text(
        "from collections import namedtuple\nBeat = namedtuple('Beat', 'key text visual')\n"
        "SCENE_ORDER = ['ch00']\nCHAPTERS = {'ch00': ('', '')}\n"
        "NARRATION = {'ch00': [Beat('a1', 'Una frase lunga abbastanza da riempire la fascia in basso.', 'una riga'), "
        "Beat('a2', 'E una seconda frase.', 'la stessa riga')]}\n", encoding="utf-8",
    )
    (folder / "scenes" / "ch00_intro.py").write_text(
        "from manim import *\nfrom videogen.theme import *\n\n\nclass Clip(NarratedScene):\n    scene_key = 'ch00'\n\n"
        "    def build(self):\n        with self.beat('a1'):\n"
        "            self.play(FadeIn(T('una riga')), run_time=0.5)\n"
        "        with self.beat('a2'):\n            pass\n",
        encoding="utf-8",
    )
    videogen("tts", "--root", str(folder))
    assert "The scenes are clean." in videogen("check", "--root", str(folder))
    videogen("render", "--quality", "l", "--root", str(folder))
    out = folder / "out"
    out.mkdir()
    (out / "clip_480p.srt").write_text("old subtitles, from before the style", encoding="utf-8")
    videogen("assemble", "--quality", "l", "--root", str(folder))
    film = out / "clip_480p.mp4"
    # No file of subtitles with the film, not even in a folder under it: a player looks for one
    # there, and shows it over the subtitles that are in the film.
    assert [path for path in out.rglob("*") if path.suffix in (".srt", ".ass")] == []
    frame = tmp_path / "frame.png"
    command = ["ffmpeg", "-v", "error", "-y", "-ss", "1.5", "-i", str(film), "-frames:v", "1"]
    subprocess.run([*command, str(frame)], check=True)
    picture = Image.open(frame).convert("RGB")
    assert picture.size == (854, 480)

    def near(color, expected, tolerance=12):
        return all(abs(actual - wanted) <= tolerance for actual, wanted in zip(color, expected))

    # the logo, small, at the top right
    assert near(picture.getpixel((810, 44)), (255, 255, 255))
    # the background covers the frame
    assert near(picture.getpixel((200, 120)), (0, 255, 0)) and near(picture.getpixel((650, 120)), (0, 0, 255))
    band = picture.crop((0, 369, 854, 480))

    def red(color):
        return color[0] > 150 and color[0] > 2 * color[1] and color[0] > 2 * color[2]

    assert any(red(color) for color in band.get_flattened_data()), "no subtitle in the film"
    # The sheets of the film take their frames from the film: they show the subtitles.
    videogen("sheet", "--film", "--quality", "l", "--root", str(folder))
    sheet = Image.open(folder / "build" / "sheets" / "l-film" / "ch00_01.png").convert("RGB")
    assert sum(1 for color in sheet.get_flattened_data() if red(color)) > 50, "the sheet does not show the subtitles"
