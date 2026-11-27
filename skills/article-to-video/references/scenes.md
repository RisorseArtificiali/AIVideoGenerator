# Scenes: how to write a chapter

Read this at Step 5 of the skill. The demo video `examples/demo/scenes/` of the template has one example for each case.

## 1. The file of a scene

One file for each chapter: `scenes/chNN_name.py`. The file has one class that inherits from `NarratedScene`. `scene_key` is the name of the chapter in `narration.py`.

```python
from manim import *

from videogen.blocks import column_chart
from videogen.theme import *


class Charts(NarratedScene):
    scene_key = "ch01"

    def build(self):
        with self.beat("b1"):
            self.title("b1", until="column chart")
            chart = column_chart(...)
            self.play(*[FadeIn(part) for part in chart.shell()], run_time=1.4)
```

In the scene you have `self.config` (the configuration), `self.lang` (the language: `self.lang.percent(38.26)`, `self.lang.number(x)`), `self.script` and `self.config.title`.

## 2. The beats

- Put the visuals of each beat in `with self.beat("key"):`. Use the keys in the order of `narration.py`.
- The block continues for the full length of the clip: you do not calculate the length. When the visuals are longer than the clip, `videogen check` reports `[pace]`. Make the animations shorter, or divide the visuals between two beats.
- `self.hold_until("key", "a phrase")` waits until the voice says the phrase. Use a phrase of 2 to 5 words of the text of the beat. Put the visual on the word that explains it: this is what makes the video easy to follow. The `lead` argument starts the animation before the phrase, so that the visual is complete when the voice says it.
- `check` reports `[cue]` when the phrase is not in the clip. Write the phrase in the form that the voice reads (a rule in `spoken_rules.py` changes the words).
- `self.title("key", until="phrase")` shows the title of the chapter, then parks it at the top left. Use it in the first beat of a chapter, and use the rest of the beat for the first visual. `self.chapter("key")` uses the full beat for the title.
- `self.clear_stage()` fades all before a new screen. It keeps the title of the chapter.
- `self.dur("key")` gives the length of the clip.

## 3. What is on the screen

- One screen for each beat, or a screen that changes a little during the beat. A screen with many objects is difficult to read.
- Use the blocks first. For the rest, use the helpers of `videogen.theme`: `T` (LaTeX text), `M` (math), `lines`, `LabeledBox`, `arr` (arrow), `path_arrow`, `stack`, `sweep`, `appear`.
- `T()` reads LaTeX. Use `plain()` for text with `_`, `%`, `&`, `#` or `$`: these characters are commands for LaTeX.
- The title of the chapter stays at the top left: keep that area free. Put content at `y < 3.0` on the left side.
- **The band at the bottom is for the subtitles.** Keep all the content above `y = -2.9`: with the look of the template, the band is 140 pixels at 1080p, and the subtitles are drawn there. The logo is in the corner at the top right: keep free the area with `x > 5.8` and `y > 2.2`. The blocks keep both free with their default positions. When you give a position or a height to a block, or you write geometry by hand, stay above the band.
- `videogen check` reports the lines of text that are in the band (`[layout] … in the subtitle band`) and under the logo (`[layout] … under the logo`). It does not see a visual without text: the sheets of the film (`videogen sheet --film`, Step 6 of the skill) show the band with its subtitles.
- Colors: `SERIES["blue"]`, `["orange"]`, `["aqua"]` for data, in this order. `BRIGHT[...]` for diagrams. `INK["secondary"]` and `INK["muted"]` for text of less importance.
- Keep the same color for the same thing in the full video: the `visual` notes of the plan say the color of what comes back in several chapters.

## 4. The entrance of the objects

- `appear(object)`: the entrance that agrees with the type of the object (a box, text, a line).
- `FadeIn(object, shift=UP * 0.08)`: text.
- `Create(arrow)`: an arrow or a line. `GrowFromEdge(bar, DOWN)`: a bar from its base.
- `Write(text)`: only for a title.
- `Indicate`, `Circumscribe`: to point at an object on a word of the voice.
- To show one part of a block, use the parts that the block gives, as `points.row(2)` in the example of `takeaways`. `get_part_by_tex("a phrase")` gives None on a `T()` made from one string, and `FadeIn(None)` does nothing, without an error: `videogen check` cannot see it. Only the contact sheet shows the missing line.
- An entrance of 1 to 2 seconds. A list of objects: `LaggedStart` with `lag_ratio` 0.1 to 0.3.

## 5. Charts

- A bar starts at zero. When the values are near each other, use `dot_plot`.
- Put a note on the chart when the values are approximate or illustrative.
- The blocks put the colors, the axes, the labels and the legend in the correct form: do not rebuild them by hand.
- `references/blocks.md` has the catalog.

## 6. The end of a chapter

The scene fades all at the end. For the last chapter of the video, the credits stay on the screen:

```python
class Summary(NarratedScene):
    scene_key = "ch10"
    lead_out = 4.0

    def wrap_up(self):
        super().wrap_up(fade=False)
```
