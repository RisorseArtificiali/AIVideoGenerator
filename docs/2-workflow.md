# The workflow, step by step

This document shows the complete procedure for one video, with the commands. The skill does the same procedure with menus.

The commands need the folder of a video project. Go to that folder first, or use `--root <folder>`. If `videogen` is not on the `PATH`, use `tools/videogen` of the repository of the template in place of `videogen`.

## Step 1 — Start the video project

```bash
videogen new videos/my-video --language en --title "Title of the video"
```

The command makes the folder with:

- `video.toml`: the configuration.
- `narration.py`: the script, with two beats as an example.
- `spoken_rules.py`: how the voice reads some names.
- `scenes/ch00_intro.py`: the first scene, as an example.
- `.gitignore`: the generated files stay out of git.

`--language` is the language of the video: `en` or `it`. It is independent of the language of the source. `--engine` selects the speech engine. `--voice` selects a voice. If you do not give a voice, the engine uses the first voice of the language.

## Step 2 — Read the source

For a web page:

```bash
videogen extract https://example.org/the-article
```

The command makes `build/source/article.md` with the text of the article, and `build/source/figures/` with the figures. `figures/index.md` has the list of the figures with their addresses.

For a local file:

```bash
videogen extract ~/Documents/report.pdf
videogen extract ~/Documents/notes.md
```

Read the complete text. Look at each figure: the video must redraw the diagrams of the figures.

## Step 3 — Write the narration

Write `narration.py`: the chapters, and the beats of each chapter. One beat is one or two short sentences, with a note on what is on the screen. For the rules, see [The video project](3-video-project.md).

## Step 4 — Make the voice clips

```bash
videogen tts
videogen transcript
```

- `tts` makes one clip for each beat, and records the length of the clip and the time of each word.
- `transcript` transcribes the clips with an offline speech recognizer, and compares the result with the script. When a clip is different from the script, the voice reads a name badly. Write a rule in `spoken_rules.py`, then start `videogen tts` again.

`tts` makes only the clips that are new or that changed.

## Step 5 — Write the scenes

Write one file for each chapter in `scenes/`. Use the blocks. For the rules, see [Scenes and blocks](4-scenes.md).

## Step 6 — Verify the scenes without a video

```bash
videogen check
```

The command runs the scenes and reports:

- `[layout]`: text out of the frame, or text on text.
- `[cue]`: a phrase of `hold_until` that is not in the clip.
- `[pace]`: a beat with visuals longer than the voice clip.

Correct the scenes. Start the command again until the report is clean.

## Step 7 — Look at the preview

```bash
videogen render --quality l
videogen sheet
```

`render --quality l` makes a video at 480p. `sheet` makes contact sheets in `build/sheets/l/`: one frame at the end of each beat. Open and look at each sheet. Correct the scenes, then start Steps 6 and 7 again.

## Step 8 — Make the film

```bash
videogen render
videogen assemble
videogen sync
videogen script --quality h
```

- `render` makes the scenes at 1080p60.
- `assemble` joins the scenes, adds the voice, and makes `out/<name>_1080p.mp4`, the subtitles, and `chapters.txt`.
- `sync` verifies that each voice clip starts at the correct time in the film.
- `script` makes `script.md`: the narration with time codes.

## A different voice, or your voice

- To change the voice: change `voice` in `video.toml`, then start `videogen tts --force`. The scenes follow the new length of the clips.
- To use your recordings: see [Speech engines](5-tts-engines.md).

## The duration of the steps

| Step | Duration |
|---|---|
| `tts` | seconds |
| `check` | 10 to 30 seconds for each chapter |
| `render --quality l` | 1 to 3 minutes for each chapter |
| `render` at 1080p60 | 3 to 8 minutes for each chapter, in parallel |
| `assemble` | seconds |
| Writing the narration and the scenes | the largest part of the work |
