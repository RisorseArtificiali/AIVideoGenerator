# Plan: chapters, storyboard and narration

Read this at Step 2 and Step 3 of the skill.

## 1. Understand the source

As you read, make these notes:

- The main claim, in one sentence.
- The parts of the argument, in the order of the source. The order of the source is usually good: the reader of the source and the viewer of the video learn in the same order.
- Each number that matters, with its source (a table or a figure) and its precision.
- Each figure: what it shows and which block can redraw it (a chart, a pipeline, a table, a quote).
- What the source gives as a rumor, an opinion of the author, or a limitation of a study.

Look at every figure. The figures show the structure of the explanation: a figure with a loop becomes a `pipeline` with a loop, a table becomes a `compare_table`.

## 2. Plan the chapters

- 6 to 12 chapters for a full video. Each chapter has one idea and a short title.
- Chapter 0 is the opening: the title of the video, and the question that the video answers. Chapter `ch00` has no number in `CHAPTERS`.
- The last chapter is the summary, with the credits at the end.
- For a short video: 3 to 5 chapters, and only the core idea.
- A chapter of 5 to 10 beats is easy to build and to correct.

## 3. Write the narration

Write `narration.py` in the language of the video. The file has this form:

```python
from collections import namedtuple

Beat = namedtuple("Beat", "key text visual")

SCENE_ORDER = ["ch00", "ch01"]
CHAPTERS = {"ch00": ("", ""), "ch01": ("1", "The idea")}
NARRATION = {
    "ch00": [Beat("a1", "First sentence of the voice.", "Title of the video.")],
    "ch01": [Beat("b1", "Second sentence.", "A pipeline with a loop.")],
}
```

Rules:

- A beat is one or two short sentences: 10 to 30 words. It is one audio clip.
- The keys are short: `a1`, `a2` in the first chapter, `b1`, `b2` in the second, and so on. The scenes use the keys.
- The `visual` note says what is on the screen during the beat. The note is for the user and for the scenes. One screen for each beat.
- Write the numbers in the format of the language in the text that the voice reads. Write the text for the ear, not for the page: no parentheses, no citations in the middle of a sentence.
- Do not put in the voice what the viewer can read on the screen.
- The voice reads approximately 150 words each minute. A full video of 18 minutes has approximately 2,600 words.

### Names that the voice reads badly

Some names are not words of the language of the video: product names, benchmarks, abbreviations. Two solutions:

1. Say the meaning in the voice, and show the name on the screen. Example: the voice says "a test of common sense", the screen shows "HellaSwag". Use this for names that the voice cannot say.
2. Write a rule in `spoken_rules.py`: a regular expression and the text that the voice reads. The script keeps the normal spelling. Example: `(r"v2\.1", "version 2 point 1")`.

`videogen transcript` (Step 4) shows which names need a rule.

## 4. The storyboard

Show the storyboard to the user in a short table before you write the scenes:

| Chapter | Title | Beats | On screen |
|---|---|---|---|
| ch01 | The idea | 9 | a pipeline with a loop, then two stacks |

Add the total of beats and the estimated duration. The user approves the plan here: a change of the narration is inexpensive, a change of the scene code is expensive.

## 5. After the approval

When the user wants changes, change `narration.py` and show the storyboard again. When the user approves, continue with Step 4 of the skill.
