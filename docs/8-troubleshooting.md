# Troubleshooting

## The command `videogen` is not available

The command is in `~/.cache/aivideogen/venv/bin/`. This folder is not on the `PATH`. Use the full path, or add the folder to the `PATH`. See [Install the tools](1-install.md).

## `videogen doctor` shows MISSING lines

Start `tools/setup.sh` in the folder of the template. If a package does not install, read the error of the installer. The usual causes are:

- No network connection.
- A system without Pango or Cairo: Manim needs these libraries. On Fedora: `sudo dnf install pango cairo`.

## The voice: "No audio was received"

`edge-tts` did not get audio from the service. The causes are:

- No network connection.
- The voice name is not correct. Read the list: `videogen options --online`.
- The service refuses the connection for a short time. `videogen tts` tries five times. Start the command again some minutes later.
- The service changed. Read the page of the `edge-tts` project and update the package.

## The voice reads a name badly

`videogen transcript` shows what the voice says. Two solutions:

- Write a rule in `spoken_rules.py`.
- Say the meaning in the narration and show the name on the screen.

## A LaTeX error stops a scene

The error has the form `latex error converting to dvi`. The usual cause is a character that LaTeX reads as a command: `_`, `%`, `&`, `#`, `$`. Use `plain()` for that text. For the other causes, read the `.log` file that the error gives.

## `videogen check` reports many overlaps

- The title of the chapter is at the top left. Keep that area free.
- Two objects at the same position: usually a position that you calculated for a different size of text.
- A line of text with large letters (mathematics) touches the next line: move one of them a little.

## `[cue]`: a phrase is not in the clip

The phrase of `hold_until` is not in the words of the clip. Copy the phrase from the text of the beat. If a rule in `spoken_rules.py` changes the words, write the changed words.

## `[pace]`: the visuals are longer than the voice

The video stays correct, but the voice of the next beat starts late. Make the animations shorter, or divide the visuals between two beats.

## "The voice clip is older than its text"

You changed `narration.py` after `videogen tts`. Start `videogen tts` again.

## "The video is older than the narration"

You changed the narration or the voice after the render. Start `videogen render` again for that scene.

## "No timeline at quality"

You did not render that scene at that quality. Start `videogen render --quality <quality> <scene>`.

## The tools are gone

Some programs delete the content of `~/.cache`. Start `tools/setup.sh` again. To prevent the problem, set `AIVIDEOGEN_CACHE` to a folder that no program deletes.

## The offline recognizer does not read a file

The recognizer of `videogen transcript` reads the samples directly, for this reason: its file reader does not agree with the audio library that Manim uses. If you change the command, keep this operation.

## The skill does not start

- Make sure that the skill is installed: the folder `article-to-video` is in `~/.claude/skills/`, or the plugin is installed.
- The description of the skill must agree with the request. Write "video in the 3Blue1Brown style" in the request, or start the skill with its name.
