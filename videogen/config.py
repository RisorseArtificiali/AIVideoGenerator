"""The configuration of a video project: the video.toml file."""

from __future__ import annotations

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


@dataclass
class VideoConfig:
    root: Path
    title: str
    language: str = "en"
    engine: str = "edge-tts"
    voice: str | None = None      # None: the default voice of the language
    rate: str = "+0%"             # the speed of the voice: for example "+10%" or "-5%"
    out_name: str = ""            # the base name of the output files

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
        voices = self.lang.voices.get(self.engine)
        if not voices:
            raise ValueError(f"The engine '{self.engine}' has no voice for the language '{self.language}'. Set a voice in video.toml.")
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
