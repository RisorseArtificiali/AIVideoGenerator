"""Scene blocks: the screens that come back in each explainer video.

A block builds the mobjects. It does not animate them: the scene keeps the control of the
timing, and shows each part on the word of the narration that explains it
(NarratedScene.hold_until). The examples/demo video uses each block at least one time.

Charts use the validated palette of the theme, hairline axes, and direct labels.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from manim import *

from videogen.theme import (
    BRIGHT, INK, SERIES, LabeledBox, T, M, arr, bar, chrome, data_line, hbar, legend, make_axes, marker, path_arrow,
)

Color = str


@dataclass
class Chart:
    """A chart and its parts. Show `shell()` first, then `marks`, then `labels`."""

    axes: Axes
    frame: VGroup           # ticks, grid lines, tick labels, axis titles
    marks: VGroup           # the data
    labels: VGroup          # direct labels: values and names
    title: Mobject | None = None
    legend: VGroup | None = None
    note: Mobject | None = None
    reference: VGroup | None = None    # an optional reference line

    def shell(self) -> list:
        """The parts to show before the data: axes, frame, title, legend, note."""
        return [part for part in (self.axes, self.frame, self.title, self.legend, self.note) if part is not None]

    def everything(self) -> VGroup:
        return VGroup(*self.shell(), self.marks, self.labels, *([self.reference] if self.reference else []))


def _heading(axes: Axes, frame: VGroup, title: str | None, legend_entries, note: str | None) -> tuple:
    """The title above the chart, the legend below the title, and the note below the chart."""
    left, top = axes.get_left()[0], axes.get_top()[1]
    level = top
    legend_mobject = None
    if legend_entries:
        legend_mobject = legend(legend_entries, key="square", size=22).move_to([left, level + 0.25, 0], aligned_edge=LEFT)
        legend_mobject.shift(UP * legend_mobject.height / 2)
        level = legend_mobject.get_top()[1]
    title_mobject = None
    if title:
        title_mobject = T(title, size=28).move_to([left, level + 0.2, 0], aligned_edge=LEFT)
        title_mobject.shift(UP * title_mobject.height / 2)
    note_mobject = None
    if note:
        note_mobject = T(note, size=20, color=INK["muted"]).move_to([left, frame.get_bottom()[1] - 0.25, 0], aligned_edge=LEFT)
        note_mobject.shift(DOWN * note_mobject.height / 2)
    return title_mobject, legend_mobject, note_mobject


def _auto_legend(names, colors) -> list:
    entries = []
    for name, color in zip(names, colors):
        if (color, name) not in entries:
            entries.append((color, name))
    return entries


def _name(label: str, sublabel: str | None) -> VGroup:
    items = [T(label, size=24)]
    if sublabel:
        items.append(T(sublabel, size=20, color=INK["muted"]))
    return VGroup(*items).arrange(DOWN, buff=0.06)


def column_chart(
    categories, values, y_range, y_ticks=(), colors=None, y_fmt=str, value_fmt=None, y_label=None, x_label=None,
    title=None, legend_entries=None, note=None, center=(0.0, -0.7), width=5.4, height=3.6, bar_width=0.42,
) -> Chart:
    """Columns from a zero baseline. `categories` names the columns, `values` are numbers.
    `y_range` is (minimum, maximum) and starts at 0 for a true bar length.
    `legend_entries` is a list of (color, label); use True to make it from the colors."""
    count = len(categories)
    colors = colors or [SERIES["blue"]] * count
    axes = make_axes([0, count], y_range, width, height, center=center)
    frame = chrome(axes, [0, count], y_range, y_ticks=y_ticks, y_fmt=y_fmt, y_label=y_label)
    marks = VGroup(
        *[bar(axes, index + 0.5, value, width=bar_width, color=color) for index, (value, color) in enumerate(zip(values, colors))]
    )
    value_fmt = value_fmt or str
    value_labels = VGroup(*[T(value_fmt(value), size=24).next_to(piece, UP, buff=0.12) for piece, value in zip(marks, values)])
    names = VGroup(
        *[T(str(category), size=20, color=INK["secondary"]).next_to(axes.c2p(index + 0.5, 0), DOWN, buff=0.45) for index, category in enumerate(categories)]
    )
    labels = VGroup(value_labels, names)
    if x_label:
        labels.add(T(x_label, size=22, color=INK["secondary"]).next_to(names, DOWN, buff=0.3))
    if legend_entries is True:
        legend_entries = _auto_legend(categories, colors)
    title_mobject, legend_mobject, note_mobject = _heading(axes, frame, title, legend_entries, note)
    return Chart(axes, frame, marks, labels, title_mobject, legend_mobject, note_mobject)


def ranked_bars(
    rows, x_range, x_ticks=(), x_fmt=str, value_fmt=None, x_label=None, title=None, legend_entries=None, note=None,
    center=(1.4, -0.5), width=6.8, height=None, thickness=0.42,
) -> Chart:
    """Horizontal bars, the largest first. Each row is (label, sublabel or None, value, color).
    `x_range` starts at 0 for a true bar length."""
    count = len(rows)
    axes = make_axes(x_range, [0, count], width, height or max(1.6, 0.8 * count), center=center)
    frame = chrome(axes, x_range, [0, count], x_ticks=x_ticks, grid="x", x_label=x_label)
    levels = [count - 0.5 - index for index in range(count)]
    marks = VGroup(*[hbar(axes, row[2], level, thickness=thickness, color=row[3]) for row, level in zip(rows, levels)])
    value_fmt = value_fmt or str
    values = VGroup(*[T(value_fmt(row[2]), size=24).next_to(piece, RIGHT, buff=0.2) for piece, row in zip(marks, rows)])
    names = VGroup(*[_name(row[0], row[1]).next_to(axes.c2p(x_range[0], level), LEFT, buff=0.3) for row, level in zip(rows, levels)])
    if legend_entries is True:
        legend_entries = _auto_legend([row[0] for row in rows], [row[3] for row in rows])
    title_mobject, legend_mobject, note_mobject = _heading(axes, frame, title, legend_entries, note)
    return Chart(axes, frame, marks, VGroup(values, names), title_mobject, legend_mobject, note_mobject)


def dot_plot(
    rows, x_range, x_ticks=(), x_fmt=str, value_fmt=None, x_label=None, title=None, legend_entries=None, note=None,
    center=(1.4, -0.5), width=6.8, height=None,
) -> Chart:
    """One point for each row, on an axis that does not start at 0. Use it when the values
    are near each other: a bar on a cut axis gives a wrong proportion. Each row is
    (label, value, color)."""
    count = len(rows)
    axes = make_axes(x_range, [0, count], width, height or max(1.8, 0.8 * count), center=center)
    frame = chrome(axes, x_range, [0, count], x_ticks=x_ticks, grid="x", x_label=x_label)
    levels = [count - 0.5 - index for index in range(count)]
    marks = VGroup(*[marker(axes.c2p(row[1], level), row[2]) for row, level in zip(rows, levels)])
    value_fmt = value_fmt or str
    values = VGroup(*[T(value_fmt(row[1]), size=24).next_to(piece, RIGHT, buff=0.2) for piece, row in zip(marks, rows)])
    names = VGroup(*[T(row[0], size=22).next_to(axes.c2p(x_range[0], level), LEFT, buff=0.3) for row, level in zip(rows, levels)])
    if legend_entries is True:
        legend_entries = _auto_legend([row[0] for row in rows], [row[2] for row in rows])
    title_mobject, legend_mobject, note_mobject = _heading(axes, frame, title, legend_entries, note)
    return Chart(axes, frame, marks, VGroup(values, names), title_mobject, legend_mobject, note_mobject)


def line_chart(
    series, x_range, y_range, x_ticks=(), y_ticks=(), x_fmt=str, y_fmt=str, x_label=None, y_label=None, title=None,
    note=None, legend_entries=None, reference=None, center=(0.0, -0.8), width=6.4, height=3.6, markers=True,
) -> Chart:
    """Line charts with points at the data values. Each series is (label, color, points), and
    each point is (x, y). With one series there is no legend: the title names it.
    `reference` is (y value, label): a dashed line for a threshold or a level."""
    axes = make_axes(x_range, y_range, width, height, center=center)
    frame = chrome(axes, x_range, y_range, x_ticks, y_ticks, x_fmt, y_fmt, x_label=x_label, y_label=y_label)
    marks = VGroup()
    for _label, color, points in series:
        line = data_line(axes, points, color, stroke=4)
        dots = VGroup(*[marker(axes.c2p(x, y), color) for x, y in points]) if markers else VGroup()
        marks.add(VGroup(line, dots))
    if legend_entries is True and len(series) > 1:
        legend_entries = [(color, label) for label, color, _points in series]
    reference_group = None
    if reference is not None:
        level, text = reference
        line = DashedLine(axes.c2p(x_range[0], level), axes.c2p(x_range[1], level), stroke_width=2, color=INK["secondary"], dash_length=0.12)
        reference_group = VGroup(line, T(text, size=20, color=INK["secondary"]).next_to(line, UP, buff=0.1).align_to(line, RIGHT))
    title_mobject, legend_mobject, note_mobject = _heading(axes, frame, title, legend_entries, note)
    return Chart(axes, frame, marks, VGroup(), title_mobject, legend_mobject, note_mobject, reference_group)


def qualitative_curves(axes: Axes, curves) -> VGroup:
    """Smooth curves from functions, for a trend that has no numbers: each curve is
    (color, function). Put a note on the chart that says that the trend is illustrative."""
    return VGroup(*[axes.plot(function, x_range=list(axes.x_range[:2]), color=color, stroke_width=4) for color, function in curves])


@dataclass
class Multiples:
    """Two to four line charts with the same x axis: small multiples."""

    panels: list[Chart]
    legend: VGroup | None = None
    x_title: Mobject | None = None
    note: Mobject | None = None

    def everything(self) -> VGroup:
        return VGroup(*[part for part in (self.legend, self.x_title, self.note) if part is not None], *[panel.everything() for panel in self.panels])


def small_multiples(
    panels, x_range, y_range, x_ticks=(), x_fmt=str, y_ticks=(), y_fmt=lambda value: f"{value:g}", x_label=None,
    note=None, center=(0.0, -0.9), panel_width=2.4, panel_height=2.4, gap=0.9,
) -> Multiples:
    """Each panel is (title, series). `y_range` is one (minimum, maximum) for all the panels,
    or one for each panel. One y axis for all the panels makes the comparison true."""
    count = len(panels)
    total = count * panel_width + (count - 1) * gap
    left = center[0] - total / 2
    charts = []
    for index, (panel_title, series) in enumerate(panels):
        window = y_range[index] if isinstance(y_range[0], (tuple, list)) else y_range
        middle = left + panel_width / 2 + index * (panel_width + gap)
        chart = line_chart(series, x_range, window, x_ticks, y_ticks, x_fmt, y_fmt, center=(middle, center[1]), width=panel_width, height=panel_height)
        chart.title = T(panel_title, size=20, color=INK["secondary"]).next_to(chart.axes, UP, buff=0.35)
        charts.append(chart)
    entries = [(color, label) for label, color, _points in panels[0][1]]
    key = legend(entries, size=20).move_to([center[0], center[1] + panel_height / 2 + 1.25, 0]) if len(entries) > 1 else None
    x_title = T(x_label, size=20, color=INK["secondary"]).move_to([center[0], center[1] - panel_height / 2 - 1.0, 0]) if x_label else None
    note_mobject = T(note, size=18, color=INK["muted"]).move_to([center[0], center[1] - panel_height / 2 - 1.4, 0]) if note else None
    return Multiples(charts, key, x_title, note_mobject)


def stat_tiles(items, centers, value_size=40, label_size=22) -> VGroup:
    """A label over a value. Each item is (value in LaTeX, label); each center is (x, y)."""
    return VGroup(
        *[
            VGroup(T(label, size=label_size, color=INK["muted"]), M(value, size=value_size)).arrange(DOWN, buff=0.12).move_to([x, y, 0])
            for (value, label), (x, y) in zip(items, centers)
        ]
    )


@dataclass
class Quote:
    """A quotation with a colored mark. Put {{two braces}} around a phrase to get it alone
    with `part(line, index)`."""

    mark: Line
    text: VGroup
    who: Mobject | None = None

    def line(self, index: int):
        return self.text[index]

    def part(self, line_index: int, part_index: int):
        return self.text[line_index][part_index]

    def everything(self) -> VGroup:
        return VGroup(*[part for part in (self.mark, self.text, self.who) if part is not None])


def quote(lines, attribution=None, color=BRIGHT["orange"], size=28, center=(0.6, 1.6)) -> Quote:
    text = VGroup(*[T(line, size=size) for line in lines]).arrange(DOWN, aligned_edge=LEFT, buff=0.16)
    text.move_to([center[0], center[1], 0])
    mark = Line(text.get_corner(UL) + LEFT * 0.4, text.get_corner(DL) + LEFT * 0.4, stroke_width=5, color=color)
    who = T(attribution, size=20, color=INK["muted"]).next_to(text, DOWN, buff=0.25).align_to(text, LEFT) if attribution else None
    return Quote(mark, text, who)


@dataclass
class Takeaways:
    """A list of points that the scene shows one at a time. Each point is (title, detail, color)."""

    rows: VGroup = field(default_factory=VGroup)

    def row(self, index: int):
        return self.rows[index]

    def title(self, index: int):
        return self.rows[index][1][0]

    def detail(self, index: int):
        return self.rows[index][1][1]


def takeaways(points, left=-6.3, top=2.0, step=1.5) -> Takeaways:
    rows = VGroup()
    for index, (title, detail, color) in enumerate(points):
        bullet = Dot(radius=0.1, color=color, fill_opacity=1, stroke_width=0)
        block = VGroup(T(title, size=28), T(detail, size=22, color=INK["secondary"])).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        rows.add(VGroup(bullet, block).arrange(RIGHT, buff=0.35).move_to([left, top - index * step, 0], aligned_edge=LEFT))
    return Takeaways(rows)


def card(heading, lines=(), color=INK["secondary"], fill=0.06, center=(0.0, 0.0), size=(28, 24)) -> LabeledBox:
    """A box with a heading and lines of text: a note, a definition, a limitation."""
    lines = [lines] if isinstance(lines, str) else list(lines)
    items = [T(heading, size=size[0], color=INK["secondary"])] + [T(line, size=size[1]) for line in lines]
    label = VGroup(*items).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
    return LabeledBox(label, color, fill=fill, pad_x=0.5, pad_y=0.4, size=size[0], radius=0.14, stroke=2).move_to([center[0], center[1], 0])


def cards(items, centers, **kwargs) -> VGroup:
    """A row of cards. Each item is (heading, lines, color)."""
    return VGroup(*[card(heading, lines, color, center=position, **kwargs) for (heading, lines, color), position in zip(items, centers)])


def statement(lines, color=INK["primary"], size=40, center=(0.4, 0.0)) -> VGroup:
    """Lines of text at the center of the stage: the conclusion of a part."""
    return VGroup(*[T(line, size=size, color=color) for line in lines]).arrange(DOWN, buff=0.22).move_to([center[0], center[1], 0])


def side_brace(x, y_low, y_high, label, color=INK["secondary"]) -> VGroup:
    """A brace at the right of a vertical span, with its label."""
    span = Line([x, y_low, 0], [x, y_high, 0], stroke_width=0)
    brace = Brace(span, RIGHT, buff=0, color=color)
    return VGroup(brace, T(label, size=22, color=color).next_to(brace, RIGHT, buff=0.18))


def _edge_point(box: Mobject, direction) -> np.ndarray:
    """The point of the boundary of a box on the ray from its center in `direction`."""
    half = np.array([box.width / 2, box.height / 2, 0.0])
    scale = min(half[axis] / abs(direction[axis]) for axis in (0, 1) if abs(direction[axis]) > 1e-6)
    return box.get_center() + direction * scale


def feedback_loop(box, side="below", color=BRIGHT["orange"], reach=0.5, inset=0.18) -> Arrow:
    """An arrow that comes out of a box and goes back in: a loop. The arrow starts at the
    right (top) of the box and enters at the left (bottom) on the side of the loop."""
    left, right, top, bottom = box.get_left()[0], box.get_right()[0], box.get_top()[1], box.get_bottom()[1]
    if side in ("below", "above"):
        start_y, sign = (bottom, -1) if side == "below" else (top, 1)
        far_y = start_y + sign * reach
        points = [[right - inset, start_y, 0], [right - inset, far_y, 0], [left + inset, far_y, 0], [left + inset, start_y + sign * 0.06, 0]]
    else:
        start_x, sign = (left, -1) if side == "left" else (right, 1)
        far_x = start_x + sign * reach
        points = [[start_x, top - inset, 0], [far_x, top - inset, 0], [far_x, bottom + inset, 0], [start_x + sign * 0.06, bottom + inset, 0]]
    return path_arrow(points, color, stroke=4.5, tip=0.2)


@dataclass
class Flow:
    """Boxes with names, arrows between them, and loops. `arrows` has the edges in order."""

    boxes: dict[str, LabeledBox]
    arrows: VGroup
    loops: dict[str, Arrow] = field(default_factory=dict)

    def everything(self) -> VGroup:
        return VGroup(*self.boxes.values(), self.arrows, *self.loops.values())


def flow(nodes, edges=(), loops=(), paths=(), size=28, note_size=20, fill=0.12) -> Flow:
    """A diagram of boxes and arrows.

    nodes:  (name, label, color, x, y[, note]). The label is a string or a list of lines.
    edges:  (start, end[, color[, style]]). The style is "arrow", "line" or "dashed".
            The arrow goes from the boundary of one box to the boundary of the other.
    loops:  (name, side, color): feedback_loop(boxes[name], side, color).
    paths:  (points, color): an arrow on a polyline [[x, y], ...] with its tip at the end.
    """
    boxes = {}
    for node in nodes:
        name, label, color, x, y = node[:5]
        note = node[5] if len(node) > 5 else None
        items = [T(line, size=size) for line in ([label] if isinstance(label, str) else label)]
        if note:
            items.append(T(note, size=note_size, color=INK["secondary"]))
        boxes[name] = LabeledBox(VGroup(*items).arrange(DOWN, buff=0.1), color, fill=fill, size=size).move_to([x, y, 0])
    arrows = VGroup()
    for edge in edges:
        start, end, color, style = (list(edge) + [INK["secondary"], "arrow"])[:4]
        unit = boxes[end].get_center() - boxes[start].get_center()
        unit = unit / np.linalg.norm(unit[:2])
        point_a = _edge_point(boxes[start], unit) + unit * 0.06
        point_b = _edge_point(boxes[end], -unit) - unit * 0.06
        if style == "dashed":
            arrows.add(DashedLine(point_a, point_b, stroke_width=3, color=color, dash_length=0.1))
        elif style == "line":
            arrows.add(Line(point_a, point_b, stroke_width=4, color=color))
        else:
            arrows.add(arr(point_a, point_b, color, buff=0, stroke=4, tip=0.2))
    for points, color in paths:
        arrows.add(path_arrow(points, color, stroke=4, tip=0.2))
    loop_arrows = {name: feedback_loop(boxes[name], side, color) for name, side, color in loops}
    return Flow(boxes, arrows, loop_arrows)


@dataclass
class Pipeline:
    """Boxes in a row, with arrows: the steps of a process. `loop` is an arrow that goes back."""

    stages: VGroup
    arrows: VGroup
    loop: Arrow | None = None
    loop_label: Mobject | None = None

    def stage(self, index: int) -> LabeledBox:
        return self.stages[index]

    def everything(self) -> VGroup:
        return VGroup(self.stages, self.arrows, *([self.loop, self.loop_label] if self.loop else []))


def pipeline(stages, center=(0.0, 0.0), size=26, gap=0.5, loop=None, fill=0.14) -> Pipeline:
    """Each stage is (label, color) or (label, color, note).
    `loop` is (from stage, to stage, label): an arrow below the stages from one stage back to
    an earlier stage."""
    boxes = VGroup()
    for stage in stages:
        label, color = stage[:2]
        note = stage[2] if len(stage) > 2 else None
        items = [T(label, size=size)] + ([T(note, size=18, color=INK["secondary"])] if note else [])
        boxes.add(LabeledBox(VGroup(*items).arrange(DOWN, buff=0.1), color, fill=fill, size=size))
    boxes.arrange(RIGHT, buff=gap).move_to([center[0], center[1], 0])
    arrows = VGroup(
        *[arr(a.get_right() + RIGHT * 0.05, b.get_left() + LEFT * 0.05, INK["secondary"], buff=0, stroke=3.5, tip=0.18) for a, b in zip(boxes, boxes[1:])]
    )
    loop_arrow = loop_label = None
    if loop:
        source, target, text = loop
        start, end = boxes[source], boxes[target]
        bottom = boxes.get_bottom()[1]
        x_start, x_end = start.get_center()[0] + 0.35, end.get_center()[0] - 0.35
        loop_arrow = path_arrow(
            [[x_start, bottom - 0.06, 0], [x_start, bottom - 0.5, 0], [x_end, bottom - 0.5, 0], [x_end, bottom - 0.06, 0]],
            BRIGHT["orange"], stroke=4.5, tip=0.2,
        )
        loop_label = T(text, size=20, color=BRIGHT["orange"]).move_to([(x_start + x_end) / 2, bottom - 0.85, 0])
    return Pipeline(boxes, arrows, loop_arrow, loop_label)


@dataclass
class Table:
    """A table for a comparison: column titles at the top, a label for each row, and cells
    that the scene shows one row at a time with `row()`. Columns are 0, 1, 2 from the left."""

    centers: tuple
    rows: tuple
    row_y: tuple
    headers: VGroup
    subheaders: VGroup
    labels: VGroup
    rules: VGroup

    def cell(self, row: int, column: int, text: str, color=INK["primary"], size=30) -> Tex:
        return T(text, size=size, color=color).move_to([self.centers[column], self.row_y[row], 0])

    def row(self, row: int, values, colors=None) -> VGroup:
        colors = colors or [INK["primary"]] * len(values)
        return VGroup(*[self.cell(row, column, value, color) for column, (value, color) in enumerate(zip(values, colors))])


def compare_table(columns, rows, centers=(-3.6, 0.6, 4.8), top=2.85, first_row=-0.65, row_step=0.7, left=-6.9) -> Table:
    """`columns` are (title, subtitle or None); `rows` are the labels of the rows.
    The space above the first row is for a drawing that the scene adds: see examples/demo."""
    centers, rows = tuple(centers), tuple(rows)
    row_y = tuple(first_row - index * row_step for index in range(len(rows)))
    headers = VGroup(*[T(title, size=26).move_to([x, top, 0]) for (title, _sub), x in zip(columns, centers)])
    subheaders = VGroup(*[
        T(sub, size=20, color=INK["muted"]).move_to([x, top - 0.35, 0])
        for (_title, sub), x in zip(columns, centers) if sub
    ])
    labels = VGroup(*[T(label, size=22, color=INK["secondary"]).move_to([left, y, 0], aligned_edge=LEFT) for label, y in zip(rows, row_y)])
    lines_y = [first_row + row_step / 2] + [y - row_step / 2 for y in row_y]
    right = max(centers) + 2.1
    rules = VGroup(*[Line([left, y, 0], [right, y, 0], stroke_width=1.4, color=INK["axis"]) for y in lines_y])
    return Table(centers, rows, row_y, headers, subheaders, labels, rules)


def credits(title, blocks, center=(0.4, 0.0)) -> VGroup:
    """The last screen: where the content comes from. Each block is (heading, lines)."""
    def group(heading, lines):
        lines = [lines] if isinstance(lines, str) else list(lines)
        return VGroup(T(heading, size=20, color=INK["muted"]), *[T(line, size=20, color=INK["secondary"]) for line in lines]).arrange(DOWN, aligned_edge=LEFT, buff=0.1)

    groups = VGroup(*[group(heading, lines) for heading, lines in blocks]).arrange(DOWN, aligned_edge=LEFT, buff=0.45)
    return VGroup(T(title, size=36), groups).arrange(DOWN, buff=0.6).move_to([center[0], center[1], 0])
