"""Chapter 3: the text blocks, and the credits."""

from manim import *

from videogen.blocks import cards, credits, quote, statement, stat_tiles, takeaways
from videogen.theme import *


class Text(NarratedScene):
    scene_key = "ch03"
    lead_out = 4.0   # the credits stay on the screen

    def wrap_up(self):
        super().wrap_up(fade=False)

    def build(self):
        with self.beat("d1"):
            self.title("d1", until="quotation")
            text = quote(
                [r"“A sample quotation: {{the important phrase}} is here,", r"and the source stays on the screen.”"],
                "Sample text, for this demo. Use a real quotation and its source.", center=(0.6, 0.7),
            )
            self.play(Create(text.mark), FadeIn(text.text, shift=RIGHT * 0.1), run_time=1.4)
            self.hold_until("d1", "quotation", lead=0.2)
            self.play(Indicate(text.part(0, 1), color=BRIGHT["yellow"], scale_factor=1.12), run_time=0.7)
            self.hold_until("d1", "source", lead=0.2)
            self.play(FadeIn(text.who), run_time=0.8)

        with self.beat("d2"):
            self.clear_stage()
            tiles = stat_tiles(
                [(r"1{,}920", "samples"), ("48", "features"), (r"92\%", "accuracy")], [(-4.2, 0.3), (0.4, 0.3), (5.0, 0.3)]
            )
            note = T("Sample data", size=22, color=INK["muted"]).move_to([0.4, -1.2, 0])
            self.hold_until("d2", "key numbers", lead=0.4)
            self.play(LaggedStart(*[FadeIn(tile, shift=UP * 0.08) for tile in tiles], lag_ratio=0.3), run_time=1.6)
            self.hold_until("d2", "note", lead=0.3)
            self.play(FadeIn(note), run_time=0.6)

        with self.beat("d3"):
            self.clear_stage()
            group = cards(
                [("Definition", ["A card holds a short", "definition, or a note."], BRIGHT["violet"]),
                 ("Limitation", ["It also holds a limitation,", "with its source."], BRIGHT["orange"])],
                [(-3.4, 0.0), (3.8, 0.0)],
            )
            self.hold_until("d3", "definition", lead=0.3)
            self.play(appear(group[0]), run_time=1.1)
            self.hold_until("d3", "limitation", lead=0.3)
            self.play(appear(group[1]), run_time=1.1)

        with self.beat("d4"):
            self.clear_stage()
            main = statement(["A statement at the center", "gives the conclusion of a part"], size=40, center=(0.4, 0.4))
            self.hold_until("d4", "statement", lead=0.2)
            self.play(FadeIn(main, shift=UP * 0.08), run_time=1.1)
            self.hold_until("d4", "conclusion", lead=0.2)
            self.play(Circumscribe(main, color=BRIGHT["yellow"], buff=0.3), run_time=1.5)

        with self.beat("d5"):
            self.clear_stage()
            points = takeaways(
                [("First point", "one line of detail", BRIGHT["green"]), ("Second point", "one line of detail", BRIGHT["orange"]),
                 ("Third point", "one line of detail", BRIGHT["blue"])],
                top=1.4,
            )
            self.hold_until("d5", "takeaways", lead=0.2)
            self.play(FadeIn(points.row(0), shift=UP * 0.08), run_time=0.8)
            self.hold_until("d5", "each one", lead=0.1)
            self.play(FadeIn(points.row(1), shift=UP * 0.08), run_time=0.8)
            self.hold_until("d5", "its turn", lead=0.1)
            self.play(FadeIn(points.row(2), shift=UP * 0.08), run_time=0.8)

        with self.beat("d6"):
            self.clear_stage()
            last = credits(
                "Scene blocks: a tour",
                [("Content", ["A video that shows the blocks of AIVideoGenerator.", "All the numbers are sample data."]), ("Block reference", "The skill folder of AIVideoGenerator has the list of the blocks.")],
            )
            self.hold_until("d6", "where", lead=0.3)
            self.play(FadeIn(last, shift=UP * 0.08), run_time=1.4)
