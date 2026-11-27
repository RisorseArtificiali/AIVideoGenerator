# AIVideoGenerator

AIVideoGenerator makes narrated explainer videos in the style of 3Blue1Brown: animation with Manim, text with LaTeX, and a voice-over that agrees with the animation. The source is an article, a paper, a document, or notes. The video is in the language that you select. This language is independent of the language of the source.

The repository has two parts:

- **The template**: the engine `videogen`. It has the command line, the scene blocks, and the speech engines: the online service `edge-tts`, and the optional local model `omnivoice` that reads the text with a sample of a voice.
- **The skill** `article-to-video`: the procedure for the agent. It shows one menu at the start: the mode (automatic, or personalized to build the plan with you), the language with the voice, the speech engine, the coverage. Then it verifies the tools, writes the narration, makes the scenes, verifies them, and renders the film.

## What you get

For each video, the folder of the video project has:

| File | Content |
|---|---|
| `out/<name>_1080p.mp4` | the film, 1080p60, with the subtitles drawn into it |
| `out/chapters.txt` | the time of each chapter |
| `out/voice.wav` | the voice only, to add music |
| `script.md` | the narration with time codes and the visual of each beat |
| `storyboard.md` | the plan of the video: the chapters, the beats, the duration, the choices that you can change |

## The look of the video

Every video has the look of the template:

- a background image behind the scenes;
- a logo, small, at the top right;
- a band at the bottom that the scenes keep free;
- the subtitles drawn into the film, at the bottom of that band.

The images and the font are in the folder `media`. `videogen new` writes the look into the `video.toml` of a new project, in the sections `[style]` and `[subtitles]`.

- To change the look of the next videos: edit `videogen/templates/look.toml`, or the files of `media`.
- To change the look of one video: edit the two sections of its `video.toml`. Without them, the video has the plain dark background, and the subtitles are a `.srt` file in `out/`. The details are in [The video project](docs/3-video-project.md).

## Requirements

- Linux. Tested on Fedora 45, x86_64.
- Python 3.12, or the tool `uv`. `uv` downloads Python.
- `ffmpeg`, `curl`, `perl`, `tar`. ImageMagick (`magick`) for the contact sheets.
- A network connection for the install and for the voice (`edge-tts`).
- Approximately 1.5 GB of disk space for the tools.
- Optional, for the local speech engine `omnivoice` (a sample of your voice): a GPU for a fast voice, approximately 11 GB more of disk space, and no network connection for the voice.

You do not need root access. The script puts the tools in the `.tools` folder of the repository. Thus the tools stay with the project.

## Quick start

1. Install the tools:

   ```bash
   git clone https://github.com/RisorseArtificiali/AIVideoGenerator.git
   cd AIVideoGenerator
   tools/setup.sh
   ```

   `tools/setup.sh` installs the Python environment and a portable TeX Live in the folder `.tools` of the repository. At the end, `videogen doctor` verifies the tools. If `videogen` is not on the `PATH`, use `tools/videogen` in the folder of the repository.

2. Install the skill in Claude Code. Use one of these procedures:

   - Plugin: `/plugin marketplace add RisorseArtificiali/AIVideoGenerator`, then `/plugin install aivideogenerator@aivideogenerator`.
   - Copy: `cp -r skills/article-to-video ~/.claude/skills/`.

3. Start Claude Code and write, for example:

   > Make a video in the 3Blue1Brown style from this article: https://...

   The skill shows one menu at the start, then it makes the video. In the automatic mode it decides alone and lists its decisions in the final report. In the personalized mode it asks for the focus of the video and agrees on the plan with you: your angle, your content, other sources.

4. Optional: read the text with a sample of your voice, on your computer. Put a sample of 2 to 20 seconds in `voices/<name>.wav`, with the words that it says in `voices/<name>.txt`, then:

   ```bash
   tools/setup-omnivoice.sh
   videogen new videos/my-video --language en --engine omnivoice --voice <name> --title "Title of the video"
   ```

   The install downloads approximately 11 GB. The engine `omnivoice` is optional: the videos with `edge-tts` do not need it. The details are in [Speech engines](docs/5-tts-engines.md).

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
| 8 | `videogen render`, `videogen assemble` and `videogen sheet --film --quality h` | the film at 1080p60 with its subtitles, and the contact sheets of the film |

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
- [Speech engines: the online service, the local model with your voice, your recordings](docs/5-tts-engines.md)
- [Languages](docs/6-languages.md)
- [How the engine works](docs/7-architecture.md)
- [Troubleshooting](docs/8-troubleshooting.md)

The documentation uses the rules of ASD-STE100, Simplified Technical English.

## Limits

- `edge-tts` is not an official API of Microsoft. It is free and needs no key, but the service can change or stop. The text of the narration goes to the servers of Microsoft.
- The model of `omnivoice` has the license CC-BY-NC: it permits a use that is not commercial. A sample of a voice is personal data: the folder `voices` stays out of git.
- The agent cannot hear the audio. It verifies the pronunciation with an offline speech recognizer. Listen to the voice and the rhythm yourself.
- The automatic verification of the layout finds text out of the frame and text on text. It does not find a line on text or a bad position: look at the contact sheets of the scenes and of the film (`videogen sheet --film`).
- The subtitles in the film are part of the image: the viewer cannot turn them off.

## License

Apache License 2.0. See `LICENSE`.
