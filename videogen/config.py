"""The configuration of a video project: the video.toml file."""

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from videogen import paths
from videogen.langs import LANGS, Language
from videogen.tts import ENGINES


def slugify(text: str) -> str:
    """A name for files: small letters, digits and hyphens."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "video"


@dataclass(frozen=True)
class SubtitleStyle:
    """How `videogen assemble` draws the subtitles into the film (section `[subtitles]`)."""

    font: str                     # the name of the family, as the font file declares it
    size: int                     # in pixels at 1080p
    color: str = "#FFFFFF"        # "#RRGGBB"
    fonts: str | None = None      # a folder with the font files, if the system does not have the font


@dataclass
class VideoConfig:
    root: Path
    title: str
    language: str = "en"
    engine: str = "edge-tts"
    voice: str | None = None      # None: the default voice of the language
    rate: str = "+0%"             # the speed of the voice: for example "+10%" or "-5%"
    out_name: str = ""            # the base name of the output files
    background: str | None = None         # an image behind the scenes (section `[style]`): it covers the frame
    logo: str | None = None               # a small logo at the top right
    logo_height: int = 140                # in pixels at 1080p
    subtitle_band: int = 0                # the pixels at the bottom (at 1080p) that the scenes keep free
    subtitles: SubtitleStyle | None = None   # None: the subtitles are only the .srt file

    @property
    def lang(self) -> Language:
        return LANGS[self.language]

    @property
    def out(self) -> str:
        return self.out_name or slugify(self.root.name)

    @property
    def resolved_voice(self) -> str:
        if self.voice:
            return self.voice
        engine = ENGINES[self.engine]
        voices = self.lang.voices.get(self.engine) or engine.voices(self.lang, self.root)
        if not voices:
            raise ValueError(f"The engine '{self.engine}' has no voice for the language '{self.language}'. "
                             f"Set a voice in video.toml. {engine.voices_help}".strip())
        return voices[0]


def load(root: Path | None = None) -> VideoConfig:
    root = Path(root).resolve() if root else paths.in_video()
    path = root / paths.CONFIG_NAME
    if not path.is_file():
        raise LookupError(f"No {paths.CONFIG_NAME} in {root}. This is not a video project.")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    config = VideoConfig(
        root=root,
        title=data.get("title") or root.name,
        language=data.get("language", "en"),
        engine=data.get("engine", "edge-tts"),
        voice=data.get("voice") or None,
        rate=data.get("rate", "+0%"),
        out_name=data.get("out_name", ""),
    )
    if config.language not in LANGS:
        raise ValueError(f"Unknown language '{config.language}' in {path}. Available: {', '.join(LANGS)}")
    if config.engine not in ENGINES:
        raise ValueError(f"Unknown engine '{config.engine}' in {path}. Available: {', '.join(ENGINES)}")
    if not re.fullmatch(r"[+-]\d+%", config.rate):
        raise ValueError(f"The rate '{config.rate}' in {path} is not valid. Use a value such as '+5%' or '-10%'.")
    style, shown = data.get("style") or {}, data.get("subtitles") or {}
    config.background, config.logo = style.get("background"), style.get("logo")
    config.logo_height = style.get("logo_height", config.logo_height)
    config.subtitle_band = style.get("subtitle_band", 0)
    if config.logo_height <= 0 or config.subtitle_band < 0:
        raise ValueError(f"The style in {path} is not valid: 'logo_height' must be above 0 "
                         "and 'subtitle_band' at least 0.")
    if shown:
        config.subtitles = SubtitleStyle(
            font=shown.get("font") or "", size=shown.get("size") or 0,
            color=shown.get("color") or "#FFFFFF", fonts=shown.get("fonts"),
        )
        if not config.subtitles.font or config.subtitles.size <= 0:
            raise ValueError(f"The subtitles in {path} are not valid: give a 'font' and a 'size' above 0.")
    return config


def render(config: VideoConfig) -> str:
    """The text of the video.toml file."""
    voice = f'\nvoice = "{config.voice}"' if config.voice else ""
    out = f'\nout_name = "{config.out_name}"' if config.out_name else ""
    return (
        f'# The configuration of this video. For the permitted values, see the documentation.\n'
        f'title = "{config.title}"\n'
        f'language = "{config.language}"\n'
        f'engine = "{config.engine}"{voice}{out}\n'
        f'rate = "{config.rate}"\n'
    )


def look_text(folder: Path) -> str:
    """The look of a new project in `folder`: the file `look.toml` of the template, with paths
    relative to the folder of the project. An empty string when the template has no look."""
    source = paths.template_root() / "videogen" / "templates" / "look.toml"
    if not source.is_file():
        return ""
    look = tomllib.loads(source.read_text(encoding="utf-8"))
    style, subtitles = look.get("style") or {}, look.get("subtitles") or {}

    def relative(name: str) -> str:
        # In the repository, the path is relative: the project moves with the repository.
        target = paths.template_root() / name
        if folder == paths.template_root() or paths.template_root() in folder.parents:
            return Path(os.path.relpath(target, folder)).as_posix()
        return target.as_posix()

    lines = [
        "", "# The look of the video: the background with the logo, the band at the bottom for the subtitles,",
        "# and the subtitles drawn into the film. The paths are relative to the folder of this project.", "[style]",
    ]
    for key in ("background", "logo"):
        if key in style:
            lines.append(f'{key} = "{relative(style[key])}"')
    for key in ("logo_height", "subtitle_band"):
        if key in style:
            lines.append(f"{key} = {style[key]}")
    if subtitles:
        lines += ["", "[subtitles]", f'font = "{subtitles["font"]}"']
        if subtitles.get("fonts"):
            lines.append(f'fonts = "{relative(subtitles["fonts"])}"')
        if "size" in subtitles:
            lines.append(f"size = {subtitles['size']}")
        if "color" in subtitles:
            lines.append(f'color = "{subtitles["color"]}"')
    return "\n".join(lines) + "\n"
