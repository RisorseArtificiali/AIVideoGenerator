"""Chapter 2: the diagram blocks."""

from manim import *

from videogen.blocks import compare_table, feedback_loop, flow, pipeline
from videogen.theme import *


class Diagrams(NarratedScene):
    scene_key = "ch02"

    def build(self):
        with self.beat("c1"):
            self.title("c1", until="pipeline")
            line = pipeline(
                [("input", BRIGHT["violet"]), ("step 1", BRIGHT["blue"]), ("step 2", BRIGHT["blue"]), ("output", BRIGHT["green"])],
                center=(0.4, 0.4), loop=(2, 1, "repeat this step"),
            )
            self.play(appear(line.stages), Create(line.arrows), run_time=1.6)
            self.hold_until("c1", "orange arrow", lead=0.3)
            self.play(Create(line.loop), FadeIn(line.loop_label, shift=UP * 0.06), run_time=1.4)

        with self.beat("c2"):
            self.clear_stage()
            diagram = flow(
                [
                    ("start", "start", BRIGHT["violet"], -5.0, 0.4),
                    ("model", ["model", "processes the input"], BRIGHT["orange"], 0.4, 0.4),
                    ("result", "result", BRIGHT["green"], 5.8, 0.4),
                ],
                edges=[("start", "model"), ("model", "result")],
            )
            self.play(*[appear(box) for box in diagram.boxes.values()], run_time=1.6)
            self.hold_until("c2", "arrows", lead=0.2)
            self.play(Create(diagram.arrows), run_time=1.2)

        with self.beat("c3"):
            self.clear_stage()
            diagram = flow(
                [
                    ("start", "start", BRIGHT["violet"], -5.0, 0.4),
                    ("model", ["model", "processes the input"], BRIGHT["orange"], 0.4, 0.4),
                    ("result", "result", BRIGHT["green"], 5.8, 0.4),
                    ("check", "check", SERIES["aqua"], 5.8, -2.0),
                ],
                edges=[("start", "model"), ("model", "result"), ("model", "check", INK["secondary"], "dashed")],
                loops=[("model", "below", BRIGHT["orange"])],
            )
            self.play(*[appear(box) for box in diagram.boxes.values()], Create(diagram.arrows[:2]), run_time=1.8)
            self.hold_until("c3", "feedback", lead=0.3)
            self.play(Create(diagram.loops["model"]), run_time=1.2)
            self.hold_until("c3", "dashed", lead=0.2)
            self.play(Create(diagram.arrows[2]), run_time=1.0)

        with self.beat("c4"):
            self.clear_stage()
            table = compare_table([("Option A", "one pass"), ("Option B", "the same blocks two times")], ("Blocks", "Applications", "Parameters"), centers=(-2.6, 3.0), left=-5.4)
            towers = VGroup(
                stack(6, 0.9, 1.7, BRIGHT["blue"], fill=0.16).move_to([-2.6, 1.5, 0]),
                stack(6, 0.9, 1.7, BRIGHT["blue"], fill=0.16).move_to([3.0, 1.5, 0]),
            )
            self.play(Create(table.rules), FadeIn(table.headers), FadeIn(table.subheaders), FadeIn(table.labels), appear(towers), run_time=1.4)
            self.play(Create(feedback_loop(towers[1], "right", BRIGHT["orange"], reach=0.4)), run_time=1.0)
            self.hold_until("c4", "one row", lead=0.6)
            for index, values in enumerate((("22", "22"), ("22", "44"), ("same", "same"))):
                self.play(FadeIn(table.row(index, values), shift=UP * 0.06), run_time=0.5)
                if index < 2:
                    self.wait(0.2)

        with self.beat("c5"):
            self.clear_stage()
            tower = stack(9, 2.0, 3.4, BRIGHT["blue"], fill=0.16, stroke=1.8).move_to([-2.6, -0.1, 0])
            source = LabeledBox("input", BRIGHT["amber"], fill=0.1, size=32).move_to([-2.6, -2.55, 0])
            sink = LabeledBox("output", BRIGHT["green"], fill=0.1, size=32).move_to([-2.6, 2.15, 0])
            up = arr(source.get_top() + UP * 0.05, tower.get_bottom() + DOWN * 0.05, INK["secondary"], buff=0, stroke=4)
            out = arr(tower.get_top() + UP * 0.05, sink.get_bottom() + DOWN * 0.05, INK["secondary"], buff=0, stroke=4)
            note = lines("Nine layers", "The signal goes", "from the bottom", "to the top", size=30, color=INK["secondary"], aligned_edge=ORIGIN)
            note.move_to([3.8, -0.3, 0])
            self.play(appear(source), appear(tower), appear(sink), Create(up), Create(out), run_time=1.4)
            self.hold_until("c5", "from the bottom", lead=0.3)
            self.play(sweep(tower), FadeIn(note, shift=UP * 0.06), run_time=1.8)
