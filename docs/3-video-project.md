# The video project

A video project is one folder. It contains the narration, the scenes and the configuration. The generated files are in `build/` and `out/`.

```
my-video/
├── video.toml          the configuration: the language, the voice and the look of the video
├── narration.py        the script: the source of truth of the voice-over
├── storyboard.md       the plan of the video: chapters, beats, duration
├── spoken_rules.py     how the voice reads some names
├── scenes/             one Manim scene for each chapter
│   ├── ch00_intro.py
│   └── ch01_idea.py
├── build/              voice clips, time lines, preview, sheets (generated)
└── out/                the film with its subtitles, the chapters (generated)
```

## video.toml

```toml
title = "Scene blocks: a tour"
language = "en"
engine = "edge-tts"
rate = "+0%"
out_name = "scene-blocks-tour"

[style]
background = "../../media/background.png"
logo = "../../media/logo_risorse.png"
logo_height = 180
subtitle_band = 140

[subtitles]
font = "Inter"
fonts = "../../media/fonts"
size = 62
color = "#FF0000"
```

| Key | Meaning | Default |
|---|---|---|
| `title` | the title of the video. The scenes read it in `self.config.title` | the name of the folder |
| `language` | the language of the video: `en`, `it` | `en` |
| `engine` | the speech engine: `edge-tts` | `edge-tts` |
| `voice` | a voice of the engine | the first voice of the language |
| `rate` | the speed of the voice: `"+10%"` or `"-5%"` | `"+0%"` |
| `out_name` | the base name of the output files | the name of the folder |

The sections `[style]` and `[subtitles]` are the look of the video. `videogen new` writes them at the end of the file.

## The look of the video

Every video has the look of the template: a background image, a logo at the top right, a band at the bottom for the subtitles, and the subtitles drawn into the film. The look is defined in one file, `videogen/templates/look.toml`, and its files are in the folder `media` of the repository. `videogen new` copies the two sections into the `video.toml` of a new project, with paths relative to the folder of the project (absolute, when the project is outside the repository).

- To change the look of the next videos: edit `look.toml`, or the files of `media`.
- To change the look of one video: edit the two sections of its `video.toml`.
- A video without the look: delete the two sections from its `video.toml`. The video has then the plain dark background, and the subtitles are a `.srt` file in `out/`.

| Key | Meaning | Default |
|---|---|---|
| `style.background` | an image behind the scenes. It covers the frame | none: the color of the template |
| `style.logo` | a small image at the top right. An image with transparency agrees with the background | none |
| `style.logo_height` | the height of the logo, in pixels at 1080p | 140 |
| `style.subtitle_band` | the pixels at the bottom, at 1080p, that the scenes keep free for the subtitles | 0 |
| `subtitles.font` | the family of the font of the subtitles, as the font file declares it | — |
| `subtitles.fonts` | a folder with the font files | none |
| `subtitles.size` | the size of the subtitles, in pixels at 1080p | — |
| `subtitles.color` | the color of the subtitles: `"#RRGGBB"` | `"#FFFFFF"` |

The paths are relative to the folder of the project.

- With the section `[subtitles]`, `videogen assemble` draws the subtitles into the film, at the bottom and in the center. Then no `.srt` file is written: a player looks for a file of subtitles next to the film and in the folders under it, and shows it over the subtitles that are in the film. Without the section, the subtitles are only the `.srt` file, in `out/`. Do you need the `.srt` file of a video with the subtitles in the film? Assemble a second time without the section: the command is fast, because the scenes do not render again.
- `size` is the size of the font when the file of the font is in the folder of `fonts`: with Inter, a size of 62 gives letters as tall as in Inter at 62. Without the file of the font, the letters can come out smaller, because the library that draws the subtitles scales each font with the metrics of that font.
- With `subtitle_band`, put the content of the scenes above the band, and away from the corner of the logo. `videogen check` reports the text in the band (`[layout] … in the subtitle band`) and under the logo (`[layout] … under the logo`). The blocks keep both free with their default positions.
- The background with the logo is composed for each size of render, in `build/style/`.

## narration.py

```python
from collections import namedtuple

Beat = namedtuple("Beat", "key text visual")

SCENE_ORDER = ["ch00", "ch01"]

CHAPTERS = {
    "ch00": ("", ""),
    "ch01": ("1", "The idea"),
}

NARRATION = {
    "ch00": [
        Beat("a1", "The first sentence that the voice says.", "Title of the video."),
    ],
    "ch01": [
        Beat("b1", "The second sentence.", "A pipeline with a loop."),
    ],
}
```

- `SCENE_ORDER` lists the scenes in order. The names are `ch00`, `ch01`, and so on.
- `CHAPTERS` gives the number and the title of each scene. Use `("", "")` for a scene without a title.
- `NARRATION` gives the beats of each scene. A beat is `Beat(key, text, visual)`.
- `key` is a short name. The scene uses it: `with self.beat("a1"):`.
- `text` is the sentence that the voice reads. Write it in the language of the video.
- `visual` is a note for the person who reads the script: what is on the screen.

`videogen` verifies the file when a command starts it. The errors give the file and the line of the problem.

## spoken_rules.py

```python
RULES = [
    (r"MyProduct", "My Product"),
    (r"v2\.1", "version 2 point 1"),
]
```

Each rule is a regular expression and its replacement. The voice gets the changed text. The script and the subtitles keep the normal text. Write a rule only when the voice reads a name badly: `videogen transcript` finds these names.

## The scene files

The name of each file is `scenes/chNN_name.py`. Each file has one class that inherits from `NarratedScene`. The attribute `scene_key` gives the chapter. See [Scenes and blocks](4-scenes.md).

## The generated files

| Folder | Content |
|---|---|
| `build/audio/<scene>/<beat>.wav` | one voice clip for each beat |
| `build/timing/<scene>.json` | the text of each beat, the length of its clip, the time of each word |
| `build/timing/<quality>/<scene>.json` | the time line that a scene records when it renders |
| `build/media/<quality>/<scene>/` | the video of each scene |
| `build/sheets/<quality>/` | the contact sheets of the scenes |
| `build/sheets/<quality>-film/` | the contact sheets of the film, with the subtitles (`videogen sheet --film`) |
| `build/source/` | the text and the figures of the source |
| `build/style/` | the background with the logo, at the size of each render |
| `build/subtitles/` | the subtitles to draw into the film |
| `out/` | the film with its subtitles, the chapters, the voice |

`build/` and `out/` are in the `.gitignore` file of the video project. The folder `videos/` is in the `.gitignore` file of the repository: a video project there stays out of git, source files included. To keep the sources of a video in git, start the project in a different folder. To move a video project to a different computer, copy only the source files. Then start `videogen tts` and the render again.
