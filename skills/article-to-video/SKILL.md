---
name: article-to-video
description: Make a narrated explainer video in the 3Blue1Brown style (Manim animation, LaTeX, voice-over) from an article, a paper, a blog post, a document, or notes. Use this skill whenever the user asks for a video, an animated explainer, a "3Blue1Brown style" video, a Manim video, a video from a URL or a text, or a video in a language that they select. Use it even when the user does not say "3Blue1Brown". The skill asks for the source, the language of the video, and the speech engine with menus.
---

# Article to video

Make a narrated video from a source with the AIVideoGenerator template. The work has eight steps. Each step ends when its condition is true. Show a menu (AskUserQuestion) at each point where the user makes a decision, and after each step that the user can want to change.

## How the template works

Read this before Step 0. It explains the reasons of the rules below.

- A **video project** is a small folder. It has `narration.py` (the script, beat by beat), `scenes/` (one Manim scene for each chapter) and `video.toml` (language, speech engine, voice).
- A **beat** is one or two sentences of the narration: one audio clip. The scene of a chapter shows one beat at a time. The animation continues for the length of the clip. A visual can appear on one word of the clip.
- The template is the engine. It gives the command line `videogen`, drawing helpers, and **blocks**: charts, diagrams and text screens that are ready to use. Make the scenes from the blocks. Write geometry by hand only for what no block gives.
- The expensive part is the scene code and its correction. Two things cut that cost: a storyboard that the user approves before the code, and the blocks.
- The language of the video is a decision of the user. It is independent of the language of the source. The narration, the text on the screen, the subtitles and the voice use the language of the video. You translate and explain from the source.

## Step 0 — The tools

The command `videogen` must be on this computer before any other step.

1. Try `videogen doctor`. If the command is not available, try `~/.cache/aivideogen/venv/bin/videogen doctor`.
2. If `videogen` is not installed, the template is not on this computer or its tools are missing. Ask with a menu: "The AIVideoGenerator tools are not installed. Install them now?" Options: "Install now (Recommended)" and "Stop". For "Install now": ask for the folder of the template if the repository was not cloned, clone `https://github.com/RisorseArtificiali/AIVideoGenerator.git`, then start `tools/setup.sh` in that folder.
3. If `doctor` shows MISSING lines, offer the same menu. `doctor --fix` starts `tools/setup.sh`.
4. Show the result of `doctor --online` to the user in one line.

Condition: `doctor` prints "All the necessary tools are ready." The `--online` test needs a network connection: if it fails, tell the user that the voice needs the network.

## Step 1 — The menu: source, language, engine

Ask the source in the conversation: "Which article, document or text is the source? Give a link or a path." The source can be a URL, a local file, or text that the user pastes.

Then show one menu with these questions:

1. **Language of the video.** Read the languages from `videogen options` (field `languages`). Make one option for each language: label = name of the language, description = "Narration, text on the screen and voice in <name>. Default voice: <first voice>". The description must say that the choice is independent of the language of the source. The user can select "Other" for a language that is not in the list: in that case read `references/tts-and-languages.md`.
2. **Speech engine.** Read the engines from `videogen options` (field `engines`). Make one option for each engine: label = engine name, description = `detail` of the engine. Add the option "My own recordings" with the description "You record each beat: the scenes follow your recordings". An engine that is not available (field `available` is false) is an option with "not available" in its description.
3. **Voice.** Start `videogen options --online` and read `online_voices` for the selected language. Offer the first three voices of the language (the default voice first) as options. The user can select "Other" and write a voice name. If the engine is "My own recordings", do not ask this question.
4. **Coverage.** Options: "Full video (Recommended)" with the description "All the content of the source", and "Short video" with the description "Only the core idea, 2 to 4 minutes".

AskUserQuestion shows all the questions at the same time. Thus offer the voices of the first language of the list. If the user selects a different language, use the default voice of that language and tell the user. The user can write a voice with "Other".

Condition: you know the source, the language of the video, the engine, the voice and the coverage.

Then start the project. The folder is the folder that the user gave, or `videos/<slug>` in the current directory:

```bash
videogen new <folder> --language <code> --engine <engine> --voice <voice> --title "<title>"
```

With "My own recordings", use `--engine edge-tts` in the command and continue with Step 4 of `references/tts-and-languages.md`.

## Step 2 — Read the source

Read the complete source. For a web page, start `videogen extract <url> --root <folder>`: it makes `build/source/article.md` with the text, and `build/source/figures/` with the figures. Read the text and look at each figure: the figures show the diagrams that the video must redraw.

For a local file, start `videogen extract <path> --root <folder>`. For pasted text, save it in `build/source/article.md`.

Condition: you know the main claim, the parts of the argument, the numbers and their sources, and what each figure shows.

## Step 3 — The storyboard and the narration

Read `references/plan.md` and do what it says. In short:

1. Plan the chapters: 6 to 12, each with one idea.
2. Write `narration.py` in the language of the video: the beats of each chapter, with a note on what is on the screen.
3. Write the first words of each beat in the storyboard. Show the storyboard to the user: the chapters, the number of beats, the estimated duration, and the visual of each chapter.
4. Ask with a menu: "Is this storyboard approved?" Options: "Approved", "Change the chapters", "Too long", "Too short".

Condition: the user selected "Approved".

## Step 4 — The voice

```bash
videogen tts --root <folder>
videogen transcript --root <folder>
```

`tts` makes one clip for each beat. `transcript` transcribes the clips with an offline speech recognizer and compares the result with the script: it finds the names that the voice reads badly. You cannot hear the clips: this is your test of the pronunciation. When a clip is different from the script, write a rule in `spoken_rules.py` and start the two commands again.

Condition: `transcript` prints "The voice says the script."

## Step 5 — The scenes

Read `references/scenes.md` and `references/blocks.md`. Write one scene file for each chapter in `scenes/`. Use the blocks before you write geometry.

Then correct the scenes with this loop, until the scene is **clean**:

1. `videogen check --root <folder>` runs the scenes without a video. It reports four problems: text out of the frame, text on text, a phrase that the clip does not contain, and visuals longer than the voice. Condition: "The scenes are clean."
2. `videogen render --quality l --root <folder>` makes a preview. `videogen sheet --root <folder>` makes **contact sheets**: one frame at the end of each beat. Open and look at every sheet with the Read tool. The layout verification finds text problems only. Your eyes find the other problems: a wrong position, a color that does not read, a visual that does not agree with the narration.
3. Correct, then start again.

Show the sheets to the user only if they ask: the sheets are many.

Condition: `check` is clean and you looked at every sheet of every chapter.

## Step 6 — The final video

```bash
videogen render --root <folder>            # 1080p60
videogen assemble --root <folder>          # the film, the subtitles, the chapters
videogen sync --root <folder>              # voice and video agree
videogen script --root <folder>            # script.md: the narration with time codes
```

The commands make the files in `out/`: the film `.mp4`, the subtitles `.srt`, `chapters.txt` and `voice.wav` (the voice only).

Condition: `sync` prints "OK", and the film exists.

## Step 7 — The report

Tell the user:

1. The path of the film and of `script.md`.
2. The chapters with their time (from `out/chapters.txt`).
3. What you verified: layout, pronunciation (with the recognizer), agreement of voice and video. Say that you cannot listen to the audio: the user must hear the voice and the rhythm.
4. What is approximate: numbers read from figures, illustrative curves. These need a note on the screen.
5. What is not confirmed in the source: the video shows it as not confirmed.

Then ask with a menu: "What do you want to do next?" Options: "Nothing, the video is good", "Another language", "A different voice", "Correct a chapter".

## Rules for the content

- Report the source correctly. A number that you read from a figure is approximate: put a note on the screen. If the source contradicts itself, tell the user in the report.
- Show the source of each quotation on the screen.
- A claim that the source gives as a rumor stays a rumor in the video.
- Invent no data. When a trend has no numbers, draw illustrative curves and put a note on the screen.
- Keep the voice-over in short sentences: the clips are the clock of the video.
