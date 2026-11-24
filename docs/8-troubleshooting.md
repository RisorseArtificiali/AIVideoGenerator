# Troubleshooting

## The command `videogen` is not available

The command is in `.tools/venv/bin/` in the folder of the repository. This folder is not on the `PATH`. In the folder of the repository, use `tools/videogen`. Or use the full path. Or add the folder to the `PATH`. See [Install the tools](1-install.md).

## `tools/videogen` does not start

- "The tools of AIVideoGenerator are not installed": a new clone of the repository has no folder `.tools`. Start `tools/setup.sh`.
- "The Python environment has the path of a different folder": you moved the repository. The Python environment has the old path in its files. Start `tools/setup.sh` again in the new location.

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

## The tools are gone between two sessions

The tools are in the folder `.tools` of the repository. If that folder is gone, the sandbox does not keep the folder of the repository. The command `git clean -fdx` also deletes that folder. In these cases, start `tools/setup.sh` again. If `AIVIDEOGEN_TOOLS` points to a folder outside the project, a sandbox can delete that folder. Remove the variable, then start `tools/setup.sh` again.

## The offline recognizer does not read a file

The recognizer of `videogen transcript` reads the samples directly, for this reason: its file reader does not agree with the audio library that Manim uses. If you change the command, keep this operation.

## The skill does not start

- Make sure that the skill is installed: the folder `article-to-video` is in `~/.claude/skills/`, or the plugin is installed.
- The description of the skill must agree with the request. Write "video in the 3Blue1Brown style" in the request, or start the skill with its name.
