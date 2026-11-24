# AIVideoGenerator

AIVideoGenerator makes narrated explainer videos in the style of 3Blue1Brown: animation with Manim, text with LaTeX, and a voice-over that agrees with the animation. The source is an article, a paper, a document, or notes. The video is in the language that you select. This language is independent of the language of the source.

The repository has two parts:

- **The template**: the engine `videogen`. It has the command line, the scene blocks, and the speech engines.
- **The skill** `article-to-video`: the procedure for the agent. It asks for the source, the language of the video, and the speech engine with menus. Then it verifies the tools, writes the narration, makes the scenes, verifies them, and renders the film.

## What you get

For each video, the folder of the video project has:

| File | Content |
|---|---|
| `out/<name>_1080p.mp4` | the film, 1080p60 |
| `out/<name>_1080p.srt` | the subtitles, from the time of each word |
| `out/chapters.txt` | the time of each chapter |
| `out/voice.wav` | the voice only, to add music |
| `script.md` | the narration with time codes and the visual of each beat |

## Requirements

- Linux. Tested on Fedora 45, x86_64.
- Python 3.12, or the tool `uv`. `uv` downloads Python.
- `ffmpeg`, `curl`, `perl`, `tar`. ImageMagick (`magick`) for the contact sheets.
- A network connection for the install and for the voice (`edge-tts`).
- Approximately 2 GB of disk space for the tools.

You do not need root access. The tools are in `~/.cache/aivideogen`.

## Quick start

1. Install the tools:

   ```bash
   git clone https://github.com/RisorseArtificiali/AIVideoGenerator.git
   cd AIVideoGenerator
   tools/setup.sh
   ```

   `tools/setup.sh` installs the Python environment and a portable TeX Live. At the end, `videogen doctor` verifies the tools.

2. Install the skill in Claude Code. Use one of these procedures:

   - Plugin: `/plugin marketplace add RisorseArtificiali/AIVideoGenerator`, then `/plugin install aivideogenerator@aivideogenerator`.
   - Copy: `cp -r skills/article-to-video ~/.claude/skills/`.

3. Start Claude Code and write, for example:

   > Make a video in the 3Blue1Brown style from this article: https://...

   The skill shows the menus.

## How it works

| Step | Command | Result |
|---|---|---|
| 1 | `videogen new <folder>` | the folder of the video project |
| 2 | `videogen extract <url>` | the text and the figures of the source |
| 3 | — | you write `narration.py`: the script, beat by beat |
| 4 | `videogen tts` | one audio clip for each beat |
| 5 | — | you write the scenes with the blocks |
| 6 | `videogen check` | a report: text out of the frame, text on text, cues, pace |
| 7 | `videogen render --quality l` and `videogen sheet` | the preview and the contact sheets |
| 8 | `videogen render` and `videogen assemble` | the film at 1080p60 |

A **beat** is one or two sentences of the narration: one audio clip. The scene of a chapter shows one beat at a time. The animation continues for the length of the clip. A visual can appear on one word of the clip. Thus the voice and the video agree when you change the text, the voice, or the speed.

## The demo video

`examples/demo` is a complete video of 1.7 minutes. It uses each block one time. To see the complete pipeline on your computer:

```bash
videogen selftest
```

## Documentation

- [Install the tools](docs/1-install.md)
- [The workflow, step by step](docs/2-workflow.md)
- [The video project: narration, scenes, configuration](docs/3-video-project.md)
- [Scenes and blocks](docs/4-scenes.md)
- [Speech engines: keys, local models, your voice](docs/5-tts-engines.md)
- [Languages](docs/6-languages.md)
- [How the engine works](docs/7-architecture.md)
- [Troubleshooting](docs/8-troubleshooting.md)

The documentation uses the rules of ASD-STE100, Simplified Technical English.

## Limits

- `edge-tts` is not an official API of Microsoft. It is free and needs no key, but the service can change or stop. The text of the narration goes to the servers of Microsoft.
- The agent cannot hear the audio. It verifies the pronunciation with an offline speech recognizer. Listen to the voice and the rhythm yourself.
- The automatic verification of the layout finds text out of the frame and text on text. It does not find a line on text or a bad position: look at the contact sheets.

## License

Apache License 2.0. See `LICENSE`.
