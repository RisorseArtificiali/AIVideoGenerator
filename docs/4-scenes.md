# Scenes and blocks

A scene is a Manim scene that inherits from `NarratedScene`. The scene shows one beat of the narration at a time.

## The structure of a scene

```python
from manim import *

from videogen.blocks import pipeline
from videogen.theme import *


class Idea(NarratedScene):
    scene_key = "ch01"

    def build(self):
        with self.beat("b1"):
            self.title("b1", until="pipeline")
            line = pipeline([("input", BRIGHT["violet"]), ("step", BRIGHT["blue"]), ("output", BRIGHT["green"])],
                            loop=(1, 1, "repeat"))
            self.play(appear(line.stages), Create(line.arrows), run_time=1.6)

        with self.beat("b2"):
            self.hold_until("b2", "orange arrow")
            self.play(Create(line.loop), FadeIn(line.loop_label), run_time=1.4)
```

## The methods of NarratedScene

| Method | Operation |
|---|---|
| `with self.beat("key"):` | start a beat. The block continues for the length of the voice clip |
| `self.hold_until("key", "phrase", lead=0.0)` | wait until the voice says the phrase. `lead` starts the wait early |
| `self.title("key", until="phrase")` | show the title of the chapter, then park it at the top left |
| `self.chapter("key")` | use the full beat for the title of the chapter |
| `self.clear_stage()` | fade all, except the title of the chapter |
| `self.dur("key")` | the length of the voice clip, in seconds |
| `self.beat_left()` | the seconds left in the current beat |

In a scene you have `self.config` (the configuration of the video) and `self.lang` (the language). `self.lang.percent(38.26, 1)` gives `38,3\%` for Italian, and `38.3\%` for English.

## The blocks

The blocks are the screens that come back in each video. They are in `videogen.blocks`. A block builds the objects. The scene shows the parts on the words of the narration.

| Block | Screen |
|---|---|
| `column_chart` | columns from zero |
| `ranked_bars` | horizontal bars, the largest first |
| `dot_plot` | points for values that are near each other |
| `line_chart` | a trend, with one or more series |
| `small_multiples` | two to four line charts on the same axis |
| `pipeline` | the steps of a process, with an optional loop |
| `flow` | boxes with names, arrows, loops |
| `compare_table` | a table for a comparison |
| `quote` | a quotation with its source |
| `stat_tiles` | one to three key numbers |
| `card`, `cards` | a note, a definition, a limitation |
| `statement` | the conclusion of a part |
| `takeaways` | the points of the summary |
| `credits` | the last screen |

The complete catalog, with the arguments and the examples, is in [`skills/article-to-video/references/blocks.md`](../skills/article-to-video/references/blocks.md). The demo video `examples/demo/scenes/` uses each block one time.

## Rules for a good scene

- One screen for one beat. A screen with many objects is difficult to read.
- Put a visual on the word that explains it. Use `hold_until`.
- Use the blocks first. Write geometry by hand only for what no block gives.
- Keep the area at the top left free: the title of the chapter stays there.
- Keep the band at the bottom free: the subtitles are there. With the look of the template, the band is 140 pixels at 1080p, which is below `y = -2.9` in the units of a scene. Keep the corner at the top right free too: the logo is there. The blocks keep both free with their default positions.
- Use `plain()` for text that has `_`, `%`, `&`, `#` or `$`. `T()` reads LaTeX, and these characters are commands.
- Use the same color for the same thing in the full video.
- An entrance of 1 to 2 seconds is sufficient.

## Colors

- Data: `SERIES["blue"]`, `SERIES["orange"]`, `SERIES["aqua"]`, in this order. Do not use `SERIES["amber"]` near `SERIES["orange"]`: the two colors are near each other for a person who does not see all the colors.
- Diagrams: `BRIGHT["blue"]`, `["orange"]`, `["violet"]`, `["green"]`, `["amber"]`, `["cyan"]`, `["red"]`.
- Text: `INK["primary"]`. Text of less importance: `INK["secondary"]`. Notes: `INK["muted"]`.

The colors of the data are safe for the three usual types of color blindness, and have sufficient contrast on the dark background.

## The verification of the layout

At the end of each beat, the scene compares the boxes of the lines of text. `videogen check` shows the result:

- `out of frame`: a line of text is outside the frame.
- `overlap`: two lines of text are one on the other.
- `in the subtitle band`: a line of text is in the band at the bottom (with `subtitle_band`).
- `under the logo`: a line of text is in the corner at the top right (with a logo).

The verification sees the lines of text only. It does not see a line on text, a color that does not read, or a visual at a bad position: look at the contact sheets (`videogen sheet`). The subtitles are not in these sheets. After the assembly, `videogen sheet --film --quality h` makes sheets from the film, with the subtitles: there you see if a visual is in the band.
