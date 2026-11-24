# The video project

A video project is one folder. It contains the narration, the scenes and the configuration. The generated files are in `build/` and `out/`.

```
my-video/
├── video.toml          the configuration
├── narration.py        the script: the source of truth of the voice-over
├── spoken_rules.py     how the voice reads some names
├── scenes/             one Manim scene for each chapter
│   ├── ch00_intro.py
│   └── ch01_idea.py
├── build/              voice clips, time lines, preview, sheets (generated)
└── out/                the film, the subtitles, the chapters (generated)
```

## video.toml

```toml
title = "Scene blocks: a tour"
language = "en"
engine = "edge-tts"
rate = "+0%"
out_name = "scene-blocks-tour"
```

| Key | Meaning | Default |
|---|---|---|
| `title` | the title of the video. The scenes read it in `self.config.title` | the name of the folder |
| `language` | the language of the video: `en`, `it` | `en` |
| `engine` | the speech engine: `edge-tts` | `edge-tts` |
| `voice` | a voice of the engine | the first voice of the language |
| `rate` | the speed of the voice: `"+10%"` or `"-5%"` | `"+0%"` |
| `out_name` | the base name of the output files | the name of the folder |

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
| `build/sheets/<quality>/` | the contact sheets |
| `build/source/` | the text and the figures of the source |
| `out/` | the film, the subtitles, the chapters, the voice |

`build/` and `out/` are in the `.gitignore` file of the video project. To move a video project to a different computer, copy only the source files. Then start `videogen tts` and the render again.
