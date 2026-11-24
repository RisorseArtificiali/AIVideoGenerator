# How the engine works

This document explains the operation of the engine. Read it when you want to change the template.

## The principle

The voice is the clock of the video. Each beat of the narration is one audio clip. The scene of a chapter shows one beat at a time, and the block of the beat continues for the length of the clip.

```
narration.py  ──tts──▶  clip.wav + time of each word  ──▶  NarratedScene.beat()  ──render──▶  time line + video
```

## The steps in detail

### 1. The voice clips

`videogen tts` reads `narration.py`. For each beat, it applies the rules of `spoken_rules.py`, and sends the text to the speech engine. The engine gives the audio and the time of each word. The results are:

- `build/audio/<scene>/<beat>.wav`: mono, 16 bit, at 48000 Hz. The long silence at the end is removed.
- `build/timing/<scene>.json`: for each beat, the text, the fingerprint, the length of the clip, and the time of each word.

The fingerprint contains the name of the engine, the voice, the speed, and the text. `tts` makes a clip again only when the fingerprint changes.

### 2. The scene

`NarratedScene.beat()` does these operations:

1. It records the time at the start of the beat.
2. It runs the animations of the block.
3. If the voice clip is longer, it waits for the difference. If the visuals are longer, it prints `[pace]`.
4. It compares the boxes of the lines of text and prints `[layout]`.
5. It adds the beat to the time line of the scene.

`hold_until()` reads the time of the phrase in the data of step 1, and waits until that time.

At the end of the scene, the time line is saved in `build/timing/<quality>/<scene>.json`. It has the start and the end of each beat, and the fingerprint of the narration.

### 3. The render

`videogen render` starts one Manim process for each scene. The processes operate in parallel (`--jobs`). Each scene is a separate video.

`videogen check` starts the same processes with `--dry_run`. Manim does not write a video, but the scene operates completely. Thus the report is available in seconds.

### 4. The assembly

`videogen assemble`:

1. Reads the time line of each scene.
2. Compares the fingerprint of the time line with the fingerprint of the narration. If they are different, the video is older than the narration: the command stops and gives the correction.
3. Makes the audio track of the scene: each clip at its start time.
4. Joins the videos of the scenes, and adds the audio. A filter sets the loudness to -16 LUFS.
5. Groups the timed words in subtitle lines, and writes the `.srt` file.

## The folders of the tools

The tools are in the folder `.tools` of the repository: they stay with the project. Set `AIVIDEOGEN_TOOLS` to use a different folder.

| Folder | Content |
|---|---|
| `.tools/venv/` | the Python environment, with the template installed |
| `.tools/texlive/` | a portable TeX Live. It has only the packages that Manim needs |
| `.tools/models/whisper/` | the model of the offline speech recognizer |

`videogen` adds the folder of TeX Live to the `PATH` when the theme starts. Manim finds `latex` and `dvisvgm` there.

## The code

| Module | Content |
|---|---|
| `videogen/cli.py` | the commands |
| `videogen/theme.py` | the palette, the LaTeX template, the drawing helpers, the chart kit, `NarratedScene`, the verification of the layout |
| `videogen/blocks.py` | the blocks: charts, diagrams, text |
| `videogen/speech.py` | the voice clips, the fingerprints, the recordings of the user |
| `videogen/tts.py` | the speech engines, the `.env` files |
| `videogen/langs.py` | the languages |
| `videogen/narration.py` | the load and the verification of `narration.py` |
| `videogen/config.py` | `video.toml` |
| `videogen/subtitles.py` | the line breaks of the subtitles, the `.srt` file |
| `videogen/paths.py` | the folders |
| `videogen/templates/` | the files of a new video project |

## The palette of the charts

The colors of the data are in `SERIES`. They agree with the dark background `#161C20`:

- Each color has a luminosity in the range for a dark background.
- The first three colors are different for the usual types of color blindness.
- Each color has a contrast of at least 3 to 1 with the background.

If you change the background or the colors, verify the palette again with a validator of colors for color blindness.
