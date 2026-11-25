"""Chapter 1: the chart blocks. All the numbers are sample data."""

from manim import *

from videogen.blocks import column_chart, dot_plot, line_chart, ranked_bars, small_multiples
from videogen.theme import *

BLUE, ORANGE, AQUA = SERIES["blue"], SERIES["orange"], SERIES["aqua"]


class Charts(NarratedScene):
    scene_key = "ch01"

    def build(self):
        percent = self.lang.percent
        with self.beat("b1"):
            self.title("b1", until="column chart")
            chart = column_chart(
                ["A", "B", "C", "D"], [42, 58, 35, 71], (0, 80), y_ticks=[0, 20, 40, 60, 80], y_fmt=percent, y_label="score",
                x_label="condition", value_fmt=percent, title="Sample data: four conditions", width=5.6, height=3.2,
            )
            self.play(*[FadeIn(part, shift=UP * 0.06) for part in chart.shell()], run_time=1.4)
            self.play(LaggedStart(*[GrowFromEdge(piece, DOWN) for piece in chart.marks], lag_ratio=0.15), run_time=1.4)
            self.hold_until("b1", "value on top", lead=0.8)
            self.play(FadeIn(chart.labels, shift=UP * 0.06), run_time=0.9)

        with self.beat("b2"):
            self.clear_stage()
            chart = ranked_bars(
                [("Model D", "large", 71, AQUA), ("Model B", "medium", 58, ORANGE), ("Model A", "small", 42, BLUE)], (0, 80),
                x_ticks=[0, 20, 40, 60, 80], x_fmt=percent, value_fmt=percent, x_label="score", title="Sample data: three models",
                legend_entries=True, center=(2.4, -0.9), width=6.0,
            )
            self.play(*[FadeIn(part, shift=UP * 0.06) for part in chart.shell()], run_time=1.3)
            self.play(LaggedStart(*[FadeIn(piece, shift=RIGHT * 0.2) for piece in chart.marks], lag_ratio=0.25), FadeIn(chart.labels, shift=LEFT * 0.1), run_time=1.8)

        with self.beat("b3"):
            self.clear_stage()
            chart = dot_plot(
                [("Model D", 71, AQUA), ("Model B", 68, ORANGE), ("Model A", 66, BLUE)], (60, 75), x_ticks=[60, 65, 70, 75],
                x_fmt=percent, value_fmt=percent, x_label="score", title="Near values: points, not bars", legend_entries=True,
                center=(2.4, -0.9), width=6.0,
            )
            self.play(*[FadeIn(part, shift=UP * 0.06) for part in chart.shell()], run_time=1.3)
            self.hold_until("b3", "dot plot", lead=0.6)
            self.play(LaggedStart(*[FadeIn(piece, scale=0.5) for piece in chart.marks], lag_ratio=0.3), FadeIn(chart.labels, shift=LEFT * 0.1), run_time=1.6)
            self.hold_until("b3", "cut axis", lead=0.2)
            self.play(Indicate(chart.axes, color=BRIGHT["yellow"], scale_factor=1.03), run_time=1.4)

        with self.beat("b4"):
            self.clear_stage()
            chart = line_chart(
                [("Model A", BLUE, [(1, 20), (2, 35), (3, 44), (4, 50)]), ("Model B", ORANGE, [(1, 18), (2, 40), (3, 62), (4, 70)])],
                (0, 5), (0, 80), x_ticks=[1, 2, 3, 4], y_ticks=[0, 20, 40, 60, 80], y_fmt=percent, x_label="steps", y_label="score",
                title="Sample data: score after each step", legend_entries=True, reference=(50, r"target 50\%"), width=6.4,
            )
            self.play(*[FadeIn(part, shift=UP * 0.06) for part in chart.shell()], run_time=1.2)
            self.play(*[Create(series) for series in chart.marks], run_time=1.5)
            self.hold_until("b4", "dashed line", lead=0.2)
            self.play(Create(chart.reference), run_time=0.6)

        with self.beat("b5"):
            self.clear_stage()
            before = ("before", BLUE, [(1, 10), (2, 24), (3, 33), (4, 40)])
            after = ("after", ORANGE, [(1, 14), (2, 38), (3, 58), (4, 70)])
            charts = small_multiples(
                [("small model", [before, after]), ("medium model", [before, after]), ("large model", [before, after])], (0, 5), (0, 80), x_ticks=[1, 2, 3, 4],
                y_ticks=[0, 40, 80], y_fmt=percent, x_label="steps", note="Sample data. The three panels share one y axis.",
                panel_width=2.6, panel_height=2.4, gap=0.8,
            )
            self.play(*[FadeIn(part, shift=UP * 0.06) for panel in charts.panels for part in panel.shell()], FadeIn(charts.legend), FadeIn(charts.x_title), FadeIn(charts.note), run_time=1.6)
            self.play(*[Create(series) for panel in charts.panels for series in panel.marks], run_time=2.0)
