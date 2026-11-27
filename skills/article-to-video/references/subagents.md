# Subagents: the figures, the chapters, the film

Read this at the Steps 2, 5 and 6 of the skill, when your tools can start subagents. The first
part is for the main agent: the agent that talks with the user. The last three parts are for the
subagents: each subagent reads its own part, and it knows only its brief.

In this file, the brief gives the names between `<` and `>`: `<videogen>` is the command of the
template, `<project>` the folder of the video, `<skill>` the folder of this skill and `<template>`
the folder of the template.

## For the main agent: how to work with the subagents

The figures, the code of the scenes and the contact sheets are the greater part of the context of
a video. In subagents, they leave the conversation with the user, that stays small until the
report; and the chapters are made in parallel. You know a chapter through the report of its
subagent.

- **A fresh context.** Start a subagent that knows only its brief. A copy of this conversation
  carries its whole context, and defeats the purpose. (In Claude Code: the Agent tool, with the
  type `general-purpose`.)
- **The brief.** A few lines: the role, the chapter, the folders, and the part of this file to
  read. The subagent reads that part, and the files that the part names. For example, for a
  builder:

      You are the builder of the chapter ch03 of a video made with AIVideoGenerator.
      Read <skill>/references/subagents.md, part "The builder", and do what it says.
      The command of the template is <videogen>. The video is in <project>.
      The template is in <template>.

  For the other subagents, change the role and the part. Give `<videogen>` with its full path,
  or its name when it is on the PATH.
- **All at the same time.** Start all the subagents of a step together, and wait for every report
  before the next step. When your tool limits how many subagents run at the same time, start them
  in batches of that number.
- **A plan that is ready.** The subagents read the plan (`narration.py` and `storyboard.md`): they
  do not make it. It is complete before Step 5.
- **Data of the plan.** When the plan needs data (values computed, or read from a figure), write
  them in `scenes/video_data.py` before Step 5. The builders read that file and leave it as it
  is: say in the brief that the data of the chapter is there.
- **Decisions without the user.** A subagent does not ask the user: it decides, and it writes its
  doubts in its report.

A chapter is **open** when its report says PROBLEMS, or when its subagent ended without a report.
The report has the form of the next part.

### At Step 5

1. Copy `narration.py`, `storyboard.md` and `spoken_rules.py` of the project into `build/plan/`.
   A builder changes only the file of its scene: the copies put back what one of them changed.
2. Start one builder for each chapter.
3. For each open chapter, start a second builder, with the lines `not solved` of its first report
   in its brief. Its context is new, so it is not anchored on the errors of the first. When more
   than a third of the chapters are open, the cause is probably common (the template, the
   narration, the tools): look for that cause before you go on.
4. When every builder has returned, compare `narration.py`, `storyboard.md` and `spoken_rules.py`
   with their copies in `build/plan/`, and put a copy back where the file changed. When a report
   asks for a rule in `spoken_rules.py`, write the rule, then start `videogen tts` and
   `videogen transcript` again: that chapter is open, like the others.
5. A chapter that is open after its second builder is yours: read the file of its scene, run the
   three commands on that scene, and open the sheets of that chapter.
6. Run `videogen check --root <project>` once, on all the scenes.

### At Step 6

1. Run the commands of the step on all the scenes. Then open the first sheet of the film once, to
   see the look with your own eyes. It is the only sheet of the film that you open, unless you
   take a chapter.
2. Start one reviewer for each chapter.
3. For each chapter that a reviewer corrected, run `videogen assemble`, `videogen sync` and
   `videogen script` again, then `videogen sheet --film --quality h --root <project>` on the
   corrected chapters. Start a second reviewer for each of them.
4. A chapter whose report says PROBLEMS and was not corrected, or whose reviewer ended without a
   report, is yours: open the sheets of the film of that chapter, and correct what is wrong. The
   same for a chapter that is open after its second reviewer.

In the report of Step 7, say that subagents verified the contact sheets, and where the sheets are
(`build/sheets/` of the project). Copy the lines `notes for the report` of the builders into it.

## The report

A subagent ends its work with this report, in English, in about fifteen lines. The report is
plain text in the answer: no code fence, no title, no line more than these. The main agent reads
many reports, and looks for these lines. This is the report of a builder:

```
ch03: CLEAN
check: 0 layout, 0 cue, 0 pace
file: scenes/ch03_indice.py
beats: d1 OK (the arrow and the title) | d2 OK (the box of the MCI) | ...
notes for the report: the values of d4 come from figure 3 | none
not solved: none
```

- The first line says `CLEAN`, or `PROBLEMS` when something is left.
- `beats` has one item for each beat of the chapter, and says what is on the screen at the end of
  the beat. It is the proof that the subagent looked at its frames.
- `notes for the report` has what the user can want to know: a value read from a figure, a visual
  that comes from a figure, a choice made with a doubt. It is `none` when there is nothing.
- `not solved` has what is left, with its cause. It is `none` when the chapter is clean.
- The report of a reviewer has no line `check`, and has one line more: `fixed: d5 (the note was in
  the band)`.
- The reader returns a text of a few lines, as its part says.

## The reader (Step 2)

You read the figures of a source, and you write what each one shows. The main agent plans the
video from your text, and opens a figure only when it has a doubt.

1. Read `build/source/article.md` in `<project>`: it says what each figure is about. Read section 1
   of `plan.md` (the notes that a figure must give) and `blocks.md` (the blocks that can redraw a
   figure): both are in the folder of this file.
2. Open every file of `build/source/figures/` in `<project>`, with the Read tool. A figure can be
   an animation (a GIF: the Read tool shows one frame): take its frames with
   `ffmpeg -i <figure> /tmp/<a folder of yours>/frame_%02d.png`, and open them. An icon or a logo
   is not a figure of the explanation: one line of `figures.md` says so.
3. Write `build/source/figures.md` in `<project>`, in the language of the source. One section for
   each figure, in the order of the text, with:
   - the file of the figure, and the part of the text that it illustrates;
   - what it shows;
   - the numbers that it adds to the text, with their precision: a value read from an image is
     approximate;
   - the block that can redraw it (a chart, a pipeline, a table, a quote), and what that block
     needs: the series, the labels, the axes.
4. Return a text of a few lines: the number of the figures; the ones that matter most for a video,
   with a reason for each; the figures that you could not read, or that no block can redraw.

The main agent reads the file: write it before you return.

## The builder (Step 5)

You write the scene of one chapter of the video, and you correct it until the chapter is clean.
The other chapters have their own builder, at the same time as you: each scene is one file.

Read first:

- **The plan**, in `<project>`: your chapter in `narration.py`, where each beat has a `visual`
  note that says what is on the screen; and the row of your chapter in `storyboard.md`. The colors
  of the `visual` notes are those of the full video: use them, because you do not see the other
  chapters.
- **How to write a scene**: `scenes.md`, and `blocks.md` for the catalog, in the folder of this
  file. Make the scene from the blocks: write geometry by hand only for what no block gives.
- **The examples**: `examples/demo/scenes/` in `<template>` has one example for each block, and
  for each case of `scenes.md`. Read the examples of the blocks that your chapter uses.
- **The corrections**: `review.md`, in the folder of this file. It says what `videogen check`
  reports, and what to look for on the contact sheets.
- **The words of the voice**: `spoken_rules.py` in `<project>`. A phrase of `hold_until` is written
  as the voice reads it.
- **A visual that comes from a figure**: read that figure in `build/source/figures.md`, and open
  the file of the figure in `build/source/figures/`, both in `<project>`.
- **The data of the plan**: `scenes/video_data.py` in `<project>`, when it is there. Leave it as
  it is.

Write the scene: one file, `scenes/<chapter>_<name>.py`, in `<project>`. When the project already
has a file for your chapter (the template of a new project, or the work of the builder before
you), work in that file. Your helper functions stay in that file. The plan, the rules, the
configuration and the scenes of the other chapters are the work of other agents: leave them as
they are.

Then correct the scene, in rounds (at most four):

1. Run `<videogen> check --root <project> <chapter>`, and correct what it reports. `review.md` says
   how.
2. Run `<videogen> render --quality l --root <project> <chapter>`, then
   `<videogen> sheet --root <project> <chapter>`. Open every sheet of your chapter with the Read
   tool: they are in `build/sheets/l/` of `<project>`, and their names start with your chapter.
   For each frame, compare the frame with the `visual` note of its beat and with its text, and
   with the list of `review.md` ("What to look for on the contact sheets"). Correct what is wrong.
3. Stop when `check` reports nothing, the scene renders, and every frame is right. After the
   fourth round, stop and report what is left.

Two cases go to the main agent, through the report:

- **A phrase that the voice reads badly.** When `hold_until` needs a rule that is not in
  `spoken_rules.py`, you do not write the rule: put the phrase in `not solved`. The main agent
  writes the rule and makes the voice again.
- **A value read from a figure.** It is approximate: the chart has its note, and the report says
  it.

When you have a doubt, decide and write the doubt in `notes for the report`: the user is away.

Return the report.

## The reviewer (Step 6)

You verify the look of the template in one chapter of the film. The film is assembled: the contact
sheets of the film have one frame at the end of each beat of your chapter.

1. Open every sheet of your chapter with the Read tool: they are in `build/sheets/h-film/` of
   `<project>`, and their names start with your chapter.
2. In each frame, verify three points (`review.md`, in the folder of this file, has them):
   - the background and the logo at the top right are there;
   - the subtitle is in the band at the bottom, in the font and the color of the look;
   - no visual is in the band, under the subtitles, or under the logo.

   To know whether a frame agrees with its beat, compare it with the narration of the beat in
   `narration.py`.
3. When a frame is wrong and the cause is the scene, correct the file of the scene
   (`scenes/<chapter>_*.py` in `<project>`; `scenes.md`, in the folder of this file, says how).
   Then verify the scene and render your chapter alone:

       <videogen> check --root <project> <chapter>
       <videogen> render --root <project> <chapter>

   The main agent assembles the film again. You correct once in a report.
4. When the cause is not the scene (the configuration of the look in `video.toml`, the voice, the
   film itself), change nothing: write it in `not solved`.

Return the report, with the line `fixed` for each correction.
