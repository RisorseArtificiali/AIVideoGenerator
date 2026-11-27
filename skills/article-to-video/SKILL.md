---
name: article-to-video
description: 'Make a narrated explainer video in the 3Blue1Brown style (Manim animation, LaTeX, voice-over) from an article, a paper, a blog post, a document, or notes. Use this skill whenever the user asks for a video, an animated explainer, a "3Blue1Brown style" video, a Manim video, a video from a URL or a text, or a video in a language that they select. Use it even when the user does not say "3Blue1Brown", and when the user wants to build the video with you: their focus, their content, other sources. The skill shows one menu at the start (automatic or personalized mode, language and voice, speech engine, coverage), then it makes the video to the end.'
---

# Article to video

Make a narrated video from a source with the AIVideoGenerator template. The work has eight steps. Each step ends when its condition is true.

The user answers at the start, then finds the video ready. Many start the process in the evening and come back in the morning: a question after the first minutes stops the work for hours. Thus collect every question in Step 1. After it, work to the end on your own. When a decision comes up, take the option that agrees with the rules of this skill, and list the decision in the report (Step 7). Stop only when the work cannot continue, and say what is missing. The personalized mode is the exception: there the user builds the plan with you, and that dialogue (Step 3) is made of questions.

## How the template works

Read this before Step 0. It explains the reasons of the rules below.

- A **video project** is a small folder. It has `narration.py` (the script, beat by beat), `scenes/` (one Manim scene for each chapter) and `video.toml` (the language, the voice, the look).
- Every video has **the look of the template**: a background image, a small logo at the top right, and the subtitles drawn into the film, in a band at the bottom. `videogen new` writes the look in `video.toml`, in the sections `[style]` and `[subtitles]`. Keep these sections as they are: they give the videos of the user the same identity. Change them only when the user asks for a different look in one video. The scenes keep the band and the corner of the logo free: `references/scenes.md` says how.
- A **beat** is one or two sentences of the narration: one audio clip. The scene of a chapter shows one beat at a time. The animation continues for the length of the clip. A visual can appear on one word of the clip.
- The template is the engine. It gives the command line `videogen`, drawing helpers, and **blocks**: charts, diagrams and text screens that are ready to use. Make the scenes from the blocks. Write geometry by hand only for what no block gives.
- The expensive part is the scene code and its correction. Two things cut that cost: a plan fixed before the code, and the blocks. In the automatic mode the plan is yours. In the personalized mode you build it with the user.
- The language of the video is a decision of the user. It is independent of the language of the source. The narration, the text on the screen, the subtitles and the voice use the language of the video. You translate and explain from the source.

## Subagents

When your tools can start subagents, use them in the Steps 2, 5 and 6. A video costs a lot of context: the figures, the code of the scenes and the contact sheets are the greater part of it. In subagents, this conversation stays small until the report, and the chapters are made in parallel.

- A subagent knows only its brief, works on one thing (the figures, a chapter) and returns a short report. It does not ask the user.
- `references/subagents.md` says how to start the subagents and what to do with their reports.
- When your tools cannot start subagents, each step says how to do the same in this conversation.

## Step 0 — The tools

`videogen` operates only if the tools are installed. The tools are in the folder `.tools` of the repository of the template (AIVideoGenerator): `tools/setup.sh` puts them there. Thus you need the folder of the template.

Find the command in this order. Stop at the first command that prints a report:

1. `videogen doctor`: the command is on the `PATH`.
2. `tools/videogen doctor`: the current directory is the folder of the template.
3. `$AIVIDEOGEN_HOME/tools/videogen doctor`: the variable `AIVIDEOGEN_HOME` gives the folder of the template.
4. `~/project/AIVideoGenerator/tools/videogen doctor`: the usual folder.

Then use that command in each step below, in place of `videogen`.

If no command operates, the cause is one of these:

- **The template is not on this computer.** No folder of the list has `tools/setup.sh` and `videogen/`. Ask with a menu: "The repository AIVideoGenerator is not on this computer. Where is it?" Options: "Clone it in `~/project/AIVideoGenerator` (Recommended)" and "Stop". The user can write the path of a different folder. Then clone `https://github.com/RisorseArtificiali/AIVideoGenerator.git`, and start `tools/setup.sh` in the clone.
- **The template is on this computer, but the tools are not complete.** `tools/videogen` prints "The tools of AIVideoGenerator are not installed", or `doctor` shows MISSING lines. Ask with a menu: "The tools of AIVideoGenerator are not complete. Install them now?" Options: "Install now (Recommended)" and "Stop". For "Install now", start `tools/setup.sh` in the folder of the template. The install needs 5 to 15 minutes.

Last, start `<command> doctor --online` and tell the result to the user in one line. `--online` needs a network connection: if it fails, say that the voice needs the network.

Condition: `doctor` prints "All the necessary tools are ready."

`tools/setup.sh` puts the tools in the folder of the template, not in the home directory: a sandbox that keeps the folder of the project also keeps the tools. If `doctor` prints a NOTE that the tools are in a different folder, tell the user that a sandbox can delete that folder between two sessions.

## Step 1 — The first minutes: the source, the menu, the project

Look at the source before the menu. The request usually gives it: a link, a path, or text. If it does not, ask: "Which article, document or text is the source? Give a link or a path." Read enough of the source to know what it is. Some sources need a question, and this is the moment for it: a link to a reply of a longer post (which of the two is the source?), or more than one document when the request does not say which one is the source. Ask that question in a menu of its own. If you cannot read the source at all, stop here and say it: the user is present now, and can paste the text or give another link. Step 2 reads the complete source.

If the source is not public (a local file, pasted text, an internal page), say before the menu that the voice of the online engine sends the text of the narration to its service. It happens with "My own recordings" too: that list starts from the synthesized clips. The user needs to know it before the choice, and after the menu they may be away. If that is not acceptable, the user can say it now: the engine `omnivoice` keeps the text on the computer, when it is installed (`references/tts-and-languages.md`).

Then show one menu, in the language of the conversation. AskUserQuestion takes four questions at the same time, and the menu is full. The request can already give an answer: for example the language of the video with its voice, or that the user records the voice. Then use that answer and take that question out of the menu. If the request gives the language and a condition on the voice (a female voice, a male voice) but not the voice, keep the question with the voices of that language that satisfy the condition. If only one voice satisfies it, use that voice and take the question out of the menu. Ask the mode always.

1. **Mode.** Two options. "Automatic": "After this menu I work alone to the end. I save the plan in the project, and my decisions are in the report." "Personalized (interactive)": "Before the video we build the plan together: the focus, the cut, your content, other sources. Then I make the video to the end." Put first the mode that agrees with the request: a request with only a link points to the automatic mode, a request that tells an opinion or a purpose points to the personalized mode.
2. **Language and voice.** One option joins the language and its voice, because the menu cannot ask the voice after the answer on the language. Read the languages from `videogen options` (field `languages`). Make one option for each language, with its first voice (the default): label = "<language> · <voice>", description = "Narration, text on the screen and voice in <language>, with the voice <voice>. This choice is independent of the language of the source." Then, if there are fewer than four options, add the second voice of the first language, of the second language, and so on, until there are four options. Each option has the same description. In the description, say also whether the voice is male or female, when you know it. The user can write a language that is not in the list in "Other": then read `references/tts-and-languages.md`. The user can write another voice in "Other": check that it speaks the language of the video (`videogen options --online` has the voices of each language). If it does not, use the default voice of the language and list the decision in the report.
3. **Speech engine.** Read the engines from `videogen options` (field `engines`). Make one option for each engine: label = engine name, description = `detail` of the engine. Add the option "My own recordings" with the description "You record each beat: the scenes follow your recordings". An engine that is not available (field `available` is false) is an option with "not available" in its description. When the user selects an engine with `voices_help` (`omnivoice`), its voices are not those of the language: read `references/tts-and-languages.md` for the voice of the video.
4. **Coverage.** Options: "Full video (Recommended)" with the description "All the content of the source", and "Short video" with the description "Only the core idea, 2 to 4 minutes".

Condition: you know the source, the mode, the language, the voice, the engine and the coverage.

Then start the project. The folder is the folder that the user gave, or `videos/<slug>` in the current directory:

```bash
videogen new <folder> --language <code> --engine <engine> --voice <voice> --title "<title>"
```

With "My own recordings", use `--engine edge-tts` in the command and follow the list "My own recordings" of `references/tts-and-languages.md`, from its point 1: it replaces Step 4. That engine needs the user: the work stops when the recordings are necessary, and starts again when they are there.

## Step 2 — Read the source

Read the complete source. For a web page, start `videogen extract <url> --root <folder>`: it makes `build/source/article.md` with the text, and `build/source/figures/` with the figures. For a local file, start `videogen extract <path> --root <folder>`. For pasted text, save it in `build/source/article.md`.

The figures show the diagrams that the video must redraw:

- **With subagents:** when the folder of the figures has files, start the figure reader (`references/subagents.md`). Read the text while the reader works. When it has returned, read `build/source/figures.md`: it says what each figure shows and which block can redraw it. Open a figure only when you have a doubt.
- **Without subagents:** read the text and look at each figure.

If `extract` cannot read the page (a login, a block), read the page with your tools and save the text in `build/source/article.md`. When the source has formulas that `extract` loses (for example a page with MathML: a sentence ends with a colon, and nothing follows), read the source with your tools and save the formulas in `build/source/formulas.md`. If you can read only a part of the source (a preview, a page that needs a login), stop and say what you could not read: the user can paste it. A video made on a part of the source would miss the argument, and nobody would know it.

Condition: you know the main claim, the parts of the argument, the numbers and their sources, and what each figure shows.

## Step 3 — The plan: the storyboard and the narration

The plan is made once, here, and it is not submitted for an approval. The user decided at the start how the plan is made, and a question now would stop the work.

- **Automatic mode.** Read `references/plan.md` and do what it says. In short: plan the chapters (6 to 12, each with one idea), write `narration.py` in the language of the video, then write `storyboard.md` in the project. If the request brings content of the user or other sources, integrate them as section 4 of `references/personalized.md` says.
- **Personalized mode.** Read `references/personalized.md` first and do what it says: with the user, it fixes the focus of the video, the cut, and the additions (the content of the user, other sources). Then plan and write `storyboard.md` in the same way.

Condition: `narration.py` and `storyboard.md` are written. In the personalized mode, the user confirmed the plan as `personalized.md` says.

## Step 4 — The voice

```bash
videogen tts --root <folder>
videogen transcript --root <folder>
```

`tts` makes one clip for each beat. `transcript` transcribes the clips with an offline speech recognizer and compares the result with the script: it finds the names that the voice reads badly. You cannot hear the clips: this is your test of the pronunciation. When a clip is different from the script, read what the voice says (`--show`). A name that the small recognizer hears badly can be right: verify it with `--model medium`. When the voice does not read a list of letters, or a formula, in a clear way, write the sentence in another way. Write a rule in `spoken_rules.py` for a name that the voice reads badly. Then start the two commands again.

With the engine `omnivoice`, keep the numbers of the narration as they are written: the engine reads them in words, and the subtitles show the digits.

Condition: `transcript` prints "The voice says the script."

## Step 5 — The scenes

**With subagents**, each chapter goes to a builder. The builder writes the scene of its chapter and corrects it, on its chapter, with the loop below, until the chapter is clean. Start one builder for each chapter, all at the same time. Then follow `references/subagents.md` ("At Step 5") for the chapters that are open. The code of the scenes and their sheets stay out of this conversation: you know each chapter through the report of its builder.

Condition: `videogen check --root <folder>` is clean on all the scenes, and every chapter has a report that says CLEAN, or is clean in your hands (`references/subagents.md` says when you take a chapter).

**Without subagents**, read `references/scenes.md` and `references/blocks.md`. Write one scene file for each chapter in `scenes/`. Use the blocks before you write geometry.

Then correct the scenes with this loop, until the scene is **clean**:

1. `videogen check --root <folder>` runs the scenes without a video. It reports: text out of the frame, text on text, text in the band of the subtitles or under the logo, a phrase that the clip does not contain, and visuals longer than the voice. Condition: "The scenes are clean."
2. `videogen render --quality l --root <folder>` makes a preview. `videogen sheet --root <folder>` makes **contact sheets**: one frame at the end of each beat. Open and look at every sheet with the Read tool. The layout verification finds text problems only. Your eyes find the other problems: a wrong position, a color that does not read, a visual that does not agree with the narration. The preview has the background and the logo, but not the subtitles: Step 6 shows them.
3. Correct, then start again.

Show the sheets to the user only if they ask: the sheets are many.

Condition: `check` is clean and you looked at every sheet of every chapter.

## Step 6 — The final video

```bash
videogen render --root <folder>                      # 1080p60
videogen assemble --root <folder>                    # the film with its subtitles, the chapters
videogen sync --root <folder>                        # voice and video agree
videogen script --root <folder>                      # script.md: the narration with time codes
videogen sheet --film --quality h --root <folder>    # the film, frame by frame, with the subtitles
```

The commands make the files in `out/`: the film `.mp4` with the subtitles drawn into it, `chapters.txt` and `voice.wav` (the voice only).

The sheets of the film are in `build/sheets/h-film/`: one frame at the end of each beat, taken from the film. It is the only place where you see the subtitles and what is under them.

With subagents: open the first sheet once, to see the look with your own eyes. Then start one reviewer for each chapter, all at the same time, and follow `references/subagents.md` ("At Step 6"): the reviewers verify every frame.

Without subagents: open and look at every sheet. When a frame is wrong, correct the scene. Then render only that scene (`videogen render --root <folder> <scene>`), and start `assemble` and this verification again.

In each frame, the three points to verify are:

- the background and the logo at the top right are there;
- the subtitle is in the band at the bottom, in the font and the color of the look;
- no content is in the band or under the logo.

Condition: `sync` prints "OK", the film exists, and every sheet of the film shows the look of the template: you saw it, or the reviewer of that chapter said CLEAN.

## Step 7 — The report

The report ends the work. Tell the user:

1. The path of the film, of `script.md` and of `storyboard.md`.
2. The chapters with their time (from `out/chapters.txt`).
3. What you verified: layout, pronunciation (with the recognizer), agreement of voice and video, the look of the film (background, logo, subtitles) on the sheets of the film. With subagents, say that they verified the contact sheets, and where the sheets are (`build/sheets/` of the project). Say that you cannot listen to the audio: the user must hear the voice and the rhythm. With "My own recordings", say that the recognizer did not verify the clips of the user.
4. The decisions that you took after the menu, each with the place where the user can change it: for example a beat that comes from a figure, a name that the voice says in another form, a sentence that you changed for the subtitles, a contradiction in the source.
5. What is approximate: numbers read from figures, illustrative curves. These need a note on the screen.
6. What is not confirmed in the source: the video shows it as not confirmed.
7. In the personalized mode: where the content of the user is in the video, and which beats come from the other sources.

Then say what the user can ask for now: another language, a different voice, a change in a chapter. Write this in the report. The user reads the report when they come back.

## Rules for the content

- Report the source correctly. A number that you read from a figure is approximate: put a note on the screen. If the source contradicts itself, follow the version that the rest of the source supports, and tell the user in the report.
- Show the source of each quotation on the screen.
- A claim that the source gives as a rumor stays a rumor in the video.
- Invent no data. When a trend has no numbers, draw illustrative curves and put a note on the screen.
- Keep the voice-over in short sentences: the clips are the clock of the video.
