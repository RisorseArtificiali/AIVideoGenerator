"""Opening: the title of the video. Each scene file has one class that inherits from
NarratedScene. The attribute scene_key is the name of the scene in narration.py."""

from manim import *

from videogen.theme import *


class Intro(NarratedScene):
    scene_key = "ch00"

    def build(self):
        with self.beat("a1"):
            rule = Line(LEFT * 2.6, RIGHT * 2.6, color=BRIGHT["orange"], stroke_width=4).move_to([0.4, 0.1, 0])
            title = plain(self.config.title, size=60).move_to([0.4, 1.0, 0])
            self.play(Create(rule), run_time=1.2)
            self.hold_until("a1", "sequence")
            self.play(Write(title), run_time=1.6)

        with self.beat("a2"):
            subtitle = lines("A short tour of the blocks of AIVideoGenerator", size=28, color=INK["secondary"])
            subtitle.move_to([0.4, -0.9, 0])
            self.hold_until("a2", "sample data", lead=0.2)
            self.play(FadeIn(subtitle, shift=UP * 0.08), run_time=0.8)
            chips = VGroup(
                *[LabeledBox(word, color, fill=0.08, size=34) for word, color in (("charts", SERIES["blue"]), ("diagrams", SERIES["orange"]), ("text", SERIES["aqua"]))]
            )
            chips.arrange(RIGHT, buff=0.5).move_to([0.4, -2.4, 0])
            for chip, phrase in zip(chips, ("charts", "diagrams", "text")):
                self.hold_until("a2", phrase, lead=0.1)
                self.play(appear(chip), run_time=0.6)
