"""The look of the video and the base class of the scenes.

This module has three parts:

- the palette and the LaTeX template,
- drawing helpers: text, boxes, arrows, stacks, and a small chart kit,
- NarratedScene, the Manim scene whose animations follow the narration clips.
"""

from __future__ import annotations

import json
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass

import numpy as np
from manim import *

from videogen import config as video_config
from videogen import langs, paths, speech
from videogen.narration import Script, load_script
from videogen.speech import track_hash

# Manim looks for latex and dvisvgm on the PATH. Put the portable TeX Live of the cache
# first, so that the scenes compile also when they start without the command line.
_TEX_BIN = paths.tex_bin()
if _TEX_BIN is not None:
    os.environ["PATH"] = str(_TEX_BIN) + os.pathsep + os.environ.get("PATH", "")

BACKGROUND = "#161C20"

# Text and chart chrome. Text never wears a series color.
INK = {
    "primary": "#F0EFEC",
    "secondary": "#C3C2B7",
    "muted": "#8E979E",
    "grid": "#272E34",
    "axis": "#3A444C",
}

# Categorical series colors, in fixed slot order, validated for the dark surface
# (lightness band, chroma floor, colorblind separation, contrast). Assign slots in
# order and never put "amber" next to "orange": that pair fails the separation checks.
SERIES = {
    "blue": "#3F95FD",
    "orange": "#E56F00",
    "aqua": "#18AF7C",
    "amber": "#C98500",
    "magenta": "#E03FA5",
    "green": "#2AA832",
    "violet": "#907FFC",
    "red": "#EF5048",
    "gray": "#6B7780",
}

# Lighter steps of the same families (plus a few illustrative hues) for diagrams,
# where color labels parts of a drawing instead of encoding a data series.
BRIGHT = {
    "blue": "#7FB9FF",
    "orange": "#FF9A4A",
    "aqua": "#45D6A3",
    "amber": "#FFCF5C",
    "violet": "#B8A8FF",
    "red": "#FF7A70",
    "green": "#8FDB8F",
    "cyan": "#7CD6F5",
    "yellow": "#FFE066",
}

TEX_TEMPLATE = TexTemplate()
TEX_TEMPLATE.preamble = "\\usepackage{amsmath}\n\\usepackage{amssymb}\n\\usepackage[T1]{fontenc}\n\\usepackage{lmodern}\n"


# --------------------------------------------------------------------------- text




def T(string, size=36, color=INK["primary"], **kwargs) -> Tex:
    """LaTeX text (text mode). Use $...$ for inline math."""
    return Tex(string, tex_template=TEX_TEMPLATE, font_size=size, color=color, **kwargs)


TEX_SPECIAL = {
    "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
    "~": r"\textasciitilde{}", "^": r"\textasciicircum{}", "\\": r"\textbackslash{}",
}


def plain(string, size=36, color=INK["primary"], **kwargs) -> Tex:
    """Text that comes from the configuration or from data. The characters that LaTeX reads
    as commands keep their normal meaning."""
    escaped = "".join(TEX_SPECIAL.get(character, character) for character in string)
    return Tex(escaped, tex_template=TEX_TEMPLATE, font_size=size, color=color, **kwargs)


def M(string, size=48, color=INK["primary"], **kwargs) -> MathTex:
    """LaTeX math."""
    return MathTex(string, tex_template=TEX_TEMPLATE, font_size=size, color=color, **kwargs)


def lines(*strings, size=34, color=INK["primary"], buff=0.18, aligned_edge=LEFT) -> VGroup:
    """A left-aligned block of text lines."""
    return VGroup(*[T(string, size=size, color=color) for string in strings]).arrange(
        DOWN, buff=buff, aligned_edge=aligned_edge
    )


def rows(*items, buff=0.14, aligned_edge=LEFT) -> VGroup:
    """Left-aligned lines given as (text, size, color) tuples."""
    return VGroup(*[T(string, size=size, color=color) for string, size, color in items]).arrange(
        DOWN, buff=buff, aligned_edge=aligned_edge
    )


def muted(mobject, shade="muted"):
    mobject.set_color(INK[shade])
    return mobject


# ------------------------------------------------------------------------- shapes


class LabeledBox(VGroup):
    """A rounded box that hugs its label: box[0] is the frame, box[1] the label."""

    def __init__(self, label, color, fill=0.2, pad_x=0.42, pad_y=0.24, radius=0.14, stroke=2.5,
                 size=34, width=None, height=None, **kwargs):
        text = label if isinstance(label, Mobject) else T(label, size=size)
        frame = RoundedRectangle(
            corner_radius=radius,
            width=width or text.width + 2 * pad_x,
            height=height or text.height + 2 * pad_y,
        )
        frame.set_stroke(color, width=stroke).set_fill(color, opacity=fill)
        text.move_to(frame)
        super().__init__(frame, text, **kwargs)

    @property
    def frame(self):
        return self[0]

    @property
    def label(self):
        return self[1]


def slab(width, height, color, fill=0.22, stroke=2.0, radius=0.06) -> RoundedRectangle:
    rect = RoundedRectangle(corner_radius=radius, width=width, height=height, stroke_width=stroke)
    rect.set_stroke(color).set_fill(color, opacity=fill)
    return rect


def arr(start, end, color, buff=0.1, stroke=5, tip=0.22, arc=0.0) -> Arrow:
    """A straight (or single-arc) arrow whose tip size does not shrink on short arrows."""
    return Arrow(
        start, end, buff=buff, color=color, stroke_width=stroke, tip_length=tip, path_arc=arc,
        max_tip_length_to_length_ratio=1.0, max_stroke_width_to_length_ratio=100.0,
    )


def path_arrow(points, color, stroke=5, tip=0.22) -> Arrow:
    """An arrow that follows an orthogonal polyline `points`, head at points[-1]."""
    points = [np.array(point, dtype=float) for point in points]
    arrow = arr(points[-2], points[-1], color, buff=0, stroke=stroke, tip=tip)
    trunk = VMobject(stroke_color=color, stroke_width=stroke)
    trunk.set_points_as_corners([points[0], *points[1:-1], arrow.points[-1]])
    arrow.points = trunk.points
    return arrow


def wire(points, color, stroke=4) -> VMobject:
    """A plain orthogonal polyline."""
    vmobject = VMobject(stroke_color=color, stroke_width=stroke)
    vmobject.set_points_as_corners([np.array(point, dtype=float) for point in points])
    return vmobject


def marker(point, color, radius=0.07, ring=0.03) -> VGroup:
    """A data-point dot with a ring in the surface color, so it stays legible on a line."""
    return VGroup(
        Dot(point, radius=radius + ring, color=BACKGROUND, fill_opacity=1, stroke_width=0),
        Dot(point, radius=radius, color=color, fill_opacity=1, stroke_width=0),
    )


def stack(count, width, height, color, gap=0.05, fill=0.2, stroke=1.6, radius=0.05) -> VGroup:
    """A vertical stack of `count` slabs; index 0 is the bottom one, so data flows
    through them in index order, bottom to top."""
    slab_height = (height - gap * (count - 1)) / count
    slabs = VGroup(*[slab(width, slab_height, color, fill=fill, stroke=stroke, radius=radius) for _ in range(count)])
    slabs.arrange(DOWN, buff=gap)
    return VGroup(*reversed(slabs))


# --------------------------------------------------------------------- animations


def appear(mobject):
    """A calm entrance that suits the kind of thing being shown."""
    if isinstance(mobject, LabeledBox):
        return Succession(
            DrawBorderThenFill(mobject.frame), FadeIn(mobject.label, shift=UP * 0.06), lag_ratio=0.4
        )
    if isinstance(mobject, VGroup):
        return LaggedStart(*[appear(child) for child in mobject], lag_ratio=0.07)
    if isinstance(mobject, (Tex, MathTex)):
        return FadeIn(mobject, shift=UP * 0.08)
    if isinstance(mobject, VMobject):
        return DrawBorderThenFill(mobject)
    return FadeIn(mobject)


def sweep(blocks, color=BRIGHT["cyan"], upward=True, lag=0.1):
    """A wave of light running through a stack of slabs, as data would."""
    order = list(blocks) if upward else list(blocks)[::-1]
    return LaggedStart(*[Indicate(slab, color=color, scale_factor=1.0) for slab in order], lag_ratio=lag)


def vanish(mobject):
    return FadeOut(mobject, shift=DOWN * 0.06)


def glow(mobject, color=BRIGHT["yellow"], run_time=1.0):
    return Circumscribe(mobject, color=color, fade_out=True, run_time=run_time, buff=0.1)


def focus(mobject, color=BRIGHT["yellow"], buff=0.12, radius=0.1) -> SurroundingRectangle:
    rect = SurroundingRectangle(mobject, color=color, buff=buff, corner_radius=radius)
    rect.set_stroke(width=3)
    return rect


# ------------------------------------------------------------------------ charts


def make_axes(x_range, y_range, x_length, y_length, center=ORIGIN) -> Axes:
    """Hairline axes, positioned by the center of their box. Ticks and labels are added
    with `chrome` so they can use the LaTeX font."""
    axes = Axes(
        x_range=[x_range[0], x_range[1], 1],
        y_range=[y_range[0], y_range[1], 1],
        x_length=x_length,
        y_length=y_length,
        tips=False,
        axis_config={
            "stroke_color": INK["axis"],
            "stroke_width": 2,
            "include_ticks": False,
            "include_numbers": False,
        },
    )
    axes.move_to([*center, 0, 0][:3])  # accepts (x, y) as well as (x, y, z)
    return axes


def chrome(axes, x_range, y_range, x_ticks=(), y_ticks=(), x_fmt=str, y_fmt=str, x_label=None,
           y_label=None, grid="y", size=24) -> VGroup:
    """Tick marks, tick labels, solid hairline gridlines and axis titles for `make_axes`."""
    parts = []
    x0, x1 = axes.c2p(x_range[0], 0)[0], axes.c2p(x_range[1], 0)[0]
    y0, y1 = axes.c2p(0, y_range[0])[1], axes.c2p(0, y_range[1])[1]
    for value in y_ticks:
        y = axes.c2p(0, value)[1]
        if grid in ("y", "both"):
            parts.append(Line([x0, y, 0], [x1, y, 0], stroke_width=1.4, color=INK["grid"]))
        parts.append(Line([x0 - 0.07, y, 0], [x0, y, 0], stroke_width=2, color=INK["axis"]))
        parts.append(T(y_fmt(value), size=size, color=INK["muted"]).next_to([x0, y, 0], LEFT, buff=0.16))
    y_labels = VGroup(*[part for part in parts if isinstance(part, Tex)])
    for value in x_ticks:
        x = axes.c2p(value, y_range[0])[0]
        if grid in ("x", "both"):
            parts.append(Line([x, y0, 0], [x, y1, 0], stroke_width=1.4, color=INK["grid"]))
        parts.append(Line([x, y0, 0], [x, y0 - 0.07, 0], stroke_width=2, color=INK["axis"]))
        parts.append(T(x_fmt(value), size=size, color=INK["muted"]).next_to([x, y0, 0], DOWN, buff=0.16))
    x_labels = VGroup(*[part for part in parts if isinstance(part, Tex) and part not in y_labels])
    if x_label:
        parts.append(T(x_label, size=size + 4, color=INK["secondary"]).next_to(x_labels, DOWN, buff=0.3))
    if y_label:
        parts.append(
            T(y_label, size=size + 4, color=INK["secondary"]).rotate(PI / 2).next_to(y_labels, LEFT, buff=0.28)
        )
    return VGroup(*parts)


def bar(axes, x, value, baseline=0, width=0.34, color=SERIES["blue"]) -> VGroup:
    """A column with a rounded top and a square baseline, growing from `baseline`."""
    left, right = axes.c2p(x - width / 2, baseline)[0], axes.c2p(x + width / 2, baseline)[0]
    bottom, top = axes.c2p(x, baseline)[1], axes.c2p(x, value)[1]
    w, h = right - left, top - bottom
    radius = min(0.1, w / 2, abs(h) / 2)
    body = RoundedRectangle(corner_radius=radius, width=w, height=h, stroke_width=0).set_fill(color, 1)
    body.move_to([(left + right) / 2, (bottom + top) / 2, 0])
    foot = Rectangle(width=w, height=radius, stroke_width=0).set_fill(color, 1)
    foot.move_to([(left + right) / 2, bottom + radius / 2, 0])
    return VGroup(body, foot)


def hbar(axes, value, y, baseline=0, thickness=0.36, color=SERIES["blue"]) -> VGroup:
    """A horizontal bar with a rounded end and a square baseline."""
    left, right = axes.c2p(baseline, y)[0], axes.c2p(value, y)[0]
    low, high = axes.c2p(0, y - thickness / 2)[1], axes.c2p(0, y + thickness / 2)[1]
    w, h = right - left, high - low
    radius = min(0.1, abs(w) / 2, h / 2)
    body = RoundedRectangle(corner_radius=radius, width=w, height=h, stroke_width=0).set_fill(color, 1)
    body.move_to([(left + right) / 2, (low + high) / 2, 0])
    foot = Rectangle(width=radius, height=h, stroke_width=0).set_fill(color, 1)
    foot.move_to([left + radius / 2, (low + high) / 2, 0])
    return VGroup(body, foot)


def data_line(axes, points, color, stroke=4) -> VMobject:
    """Straight segments through (x, y) data points."""
    line = VMobject(stroke_color=color, stroke_width=stroke)
    line.set_points_as_corners([axes.c2p(x, y) for x, y in points])
    return line


def legend(entries, key="line", size=26, buff=0.55) -> VGroup:
    """entries: (color, label) pairs. Labels stay in text ink; the key carries identity."""
    items = []
    for color, label in entries:
        if key == "line":
            glyph = Line(ORIGIN, RIGHT * 0.42, color=color, stroke_width=5)
        elif key == "dot":
            glyph = Dot(radius=0.075, color=color, fill_opacity=1, stroke_width=0)
        else:
            glyph = RoundedRectangle(corner_radius=0.04, width=0.24, height=0.24, stroke_width=0).set_fill(color, 1)
        items.append(VGroup(glyph, T(label, size=size)).arrange(RIGHT, buff=0.14))
    return VGroup(*items).arrange(RIGHT, buff=buff)


# ------------------------------------------------------------------ narration sync


# ------------------------------------------------- synchronization with the voice


def _letters(word: str) -> str:
    return "".join(character for character in word.lower() if character.isalnum())


class BeatTrack:
    """The narration clips of one scene: their length, and the time of each word."""

    def __init__(self, script: Script, scene_key: str):
        path = speech.timing_path(script.root, scene_key)
        if not path.is_file():
            raise FileNotFoundError(f"No voice clips for {scene_key} ({path}). Do: videogen tts")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.scene_key = scene_key
        self.beats = script.beats[scene_key]
        self.keys = [beat.key for beat in self.beats]
        self.durations = {}
        self.words = {}
        for beat in self.beats:
            entry = data["beats"].get(beat.key)
            if entry is None or entry.get("text") != beat.text:
                raise RuntimeError(f"The voice clip of {scene_key}/{beat.key} is older than its text. Do: videogen tts")
            self.durations[beat.key] = float(entry["dur"])
            self.words[beat.key] = entry.get("words", [])
        self.hash = track_hash(script, scene_key, data)
        self.cursor = 0

    def spoken_at(self, key: str, phrase: str) -> float:
        """Seconds from the start of clip `key` to the first word of `phrase`."""
        words = self.words.get(key, [])
        target = [_letters(word) for word in phrase.split()]
        target = [word for word in target if word]
        if target:
            for index in range(len(words) - len(target) + 1):
                if [_letters(word[2]) for word in words[index:index + len(target)]] == target:
                    return float(words[index][0])
            for word in words:
                if _letters(word[2]) == target[0]:
                    return float(word[0])
        print(f"[cue] {self.scene_key}/{key}: '{phrase}' is not in the word timings of the clip")
        return 0.5 * self.durations[key]


# --------------------------------------------------------- verification of the layout

FRAME_MARGIN = 0.1


@dataclass(frozen=True)
class LayoutIssue:
    kind: str                 # "overlap" or "out-of-frame"
    first: str
    second: str = ""

    def describe(self) -> str:
        if self.kind == "overlap":
            return f'overlap: "{self.first}" on "{self.second}"'
        return f'out of frame: "{self.first}"'


def _text_lines(mobject: Mobject, inside_text: bool, found: list) -> None:
    """Collect the text lines: the highest Tex or MathTex object of each branch."""
    is_text = isinstance(mobject, (Tex, MathTex))
    if is_text and not inside_text:
        opacities = [submobject.get_fill_opacity() or 0.0 for submobject in mobject.get_family()]
        if max(opacities, default=0.0) >= 0.2:
            text = getattr(mobject, "text", None) or getattr(mobject, "tex_string", "")
            if not isinstance(text, str):
                text = " ".join(str(part) for part in text)
            corners = (mobject.get_left()[0], mobject.get_bottom()[1], mobject.get_right()[0], mobject.get_top()[1])
            found.append((text[:40], corners))
    for child in mobject.submobjects:
        _text_lines(child, inside_text or is_text, found)


def text_boxes(mobjects) -> list[tuple[str, tuple]]:
    """The visible lines of text: (text, (left, bottom, right, top)).
    Objects redrawn at each frame are not stable: they are not included."""
    found = []
    for mobject in mobjects:
        if not mobject.updaters:
            _text_lines(mobject, False, found)
    return found


def overlaps(first: tuple, second: tuple, tolerance: float = 0.05) -> bool:
    """True when two boxes share more than a thin strip. A box is (left, bottom, right, top)."""
    width = min(first[2], second[2]) - max(first[0], second[0]) - 2 * tolerance
    height = min(first[3], second[3]) - max(first[1], second[1]) - 2 * tolerance
    return width > 0 and height > 0


def layout_issues(mobjects, width: float | None = None, height: float | None = None, margin: float = FRAME_MARGIN) -> list[LayoutIssue]:
    """Text that goes out of the frame, and lines of text that are one on the other."""
    width = config.frame_width if width is None else width
    height = config.frame_height if height is None else height
    items = text_boxes(mobjects)
    limit_x, limit_y = width / 2 - margin, height / 2 - margin
    issues = []
    for text, (left, bottom, right, top) in items:
        if left < -limit_x or right > limit_x or bottom < -limit_y or top > limit_y:
            issues.append(LayoutIssue("out-of-frame", text))
    for index, (text, box) in enumerate(items):
        for other_text, other_box in items[index + 1:]:
            if overlaps(box, other_box):
                issues.append(LayoutIssue("overlap", text, other_text))
    return issues


# ---------------------------------------------------------------------- the scene


class NarratedScene(Scene):
    """A scene that follows its narration clips.

    Put the visuals of each beat (one or two sentences of the script) in
    `with self.beat("key"):`. The block continues for the full length of the clip, however
    long the animations are. Inside the block, `self.hold_until("key", "a phrase")` waits
    for the voice to say that phrase: use it to put a visual on the word that explains it.

    Scenes have `self.config` (video.toml), `self.lang` (the language) and `self.script`.
    """

    scene_key = ""
    lead_in = 1.3     # silence before the first clip
    lead_out = 0.9    # the time of the fade at the end
    tail = 0.3        # a pause after each clip

    def setup(self):
        self.camera.background_color = BACKGROUND
        self.root = paths.in_video()
        self.config = video_config.load(self.root)
        self.lang = self.config.lang
        self.script = load_script(self.root)
        self.track = BeatTrack(self.script, self.scene_key)
        self.timeline = []
        self._beat_end = None
        self._beat_start = {}

    def construct(self):
        self.wait(self.lead_in)
        self.build()
        self.wrap_up()

    def build(self):
        raise NotImplementedError

    def wrap_up(self, fade: bool = True):
        """Fade all (or only wait), then save the real timeline for the assembly step."""
        for mobject in self.mobjects:
            mobject.clear_updaters()
        if self.mobjects and fade:
            self.play(*[FadeOut(mobject) for mobject in list(self.mobjects)], run_time=self.lead_out)
        else:
            self.wait(self.lead_out)
        leftover = self.track.keys[self.track.cursor:]
        if leftover:
            raise RuntimeError(f"{self.scene_key}: narration beats never played: {leftover}")
        out = self.root / "build" / "timing" / os.environ.get("VIDEOGEN_QUALITY", "l")
        out.mkdir(parents=True, exist_ok=True)
        payload = {
            "track_hash": self.track.hash,
            "lead_in": self.lead_in,
            "lead_out": self.lead_out,
            "total": round(self.time, 4),
            "beats": self.timeline,
        }
        (out / f"{self.scene_key}.json").write_text(json.dumps(payload, indent=1), encoding="utf-8")

    @contextmanager
    def beat(self, key: str, tail: float | None = None):
        position = self.track.cursor
        expected = self.track.keys[position] if position < len(self.track.keys) else None
        if key != expected:
            raise RuntimeError(f"{self.scene_key}: beat '{key}' is out of order (expected '{expected}')")
        start = self.time
        self._beat_end = start + self.dur(key) + (self.tail if tail is None else tail)
        self._beat_start[key] = start
        yield
        slack = self._beat_end - self.time
        if slack < -0.05:
            print(f"[pace] {self.scene_key}/{key}: the visuals are {-slack:.2f} s longer than the voice clip")
        self.pause(slack)
        for issue in layout_issues(self.mobjects):
            print(f"[layout] {self.scene_key}/{key}: {issue.describe()}")
        self.timeline.append([key, round(start, 4), round(self.time, 4)])
        self.track.cursor += 1

    def dur(self, key: str) -> float:
        """The length of a narration clip: use it to divide one beat into timed steps."""
        return self.track.durations[key]

    def beat_left(self, reserve: float = 0.0) -> float:
        """Seconds left in the current beat, less `reserve`."""
        return max(0.0, self._beat_end - self.time - reserve)

    def spoken_at(self, key: str, phrase: str) -> float:
        """The scene time at which the voice says `phrase` in clip `key`."""
        return self._beat_start.get(key, self.time) + self.track.spoken_at(key, phrase)

    def hold_until(self, key: str, phrase: str, lead: float = 0.0) -> float:
        """Wait until the voice says `phrase` in the clip of the current beat (no wait if
        the voice said it already). `lead` starts the wait early, so that the visual is
        complete when the voice says the phrase."""
        left = self.spoken_at(key, phrase) - lead - self.time
        self.pause(left)
        return left

    def pause(self, seconds: float) -> None:
        """Wait, unless the time is so short that it is not worth a frame."""
        if seconds > 0.08:
            self.wait(seconds)

    def title(self, key: str, until: str | None = None):
        """Show the title of the chapter, then park it at the top left. Use inside the beat
        `key`. With `until` (a phrase of the clip), the title parks on that phrase and the
        rest of the beat is available. Without `until`, the title uses the full beat."""
        number, chapter_title = self.script.chapters[self.scene_key]
        heading = T(f"{number}.\\ {chapter_title}" if number else chapter_title, size=60)
        self.play(Write(heading), run_time=1.4)
        if until:
            self.hold_until(key, until, lead=1.4)
        else:
            self.pause(self.beat_left(reserve=1.3))
        parked = heading.copy().scale(0.6).set_color(INK["muted"]).to_corner(UL, buff=0.6)
        self.play(heading.animate.scale(0.6).set_color(INK["muted"]).move_to(parked), run_time=1.1)
        self.heading = heading
        return heading

    def chapter(self, key: str):
        """Play a beat that only introduces the chapter."""
        with self.beat(key):
            return self.title(key)

    def clear_stage(self, run_time: float = 0.7, shift=DOWN * 0.1):
        """Fade all, except the title of the chapter."""
        heading = getattr(self, "heading", None)
        keep = []
        for mobject in list(self.mobjects):
            if mobject is heading:
                continue
            if mobject.updaters:
                mobject.clear_updaters()
                self.remove(mobject)   # this object is redrawn at each frame: it cannot fade
            else:
                keep.append(mobject)
        if keep:
            self.play(*[FadeOut(mobject, shift=shift) for mobject in keep], run_time=run_time)
