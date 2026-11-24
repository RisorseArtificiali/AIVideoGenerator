"""Where things live: the template, the tools, and the video project."""

from __future__ import annotations

import os
from pathlib import Path

CONFIG_NAME = "video.toml"


def template_root() -> Path:
    """The folder of the AIVideoGenerator repository that holds this package."""
    return Path(__file__).resolve().parent.parent


def cache_root() -> Path:
    """The tools: the Python environment and TeX Live. Set AIVIDEOGEN_CACHE to move them."""
    return Path(os.environ.get("AIVIDEOGEN_CACHE") or Path.home() / ".cache" / "aivideogen")


def venv_bin() -> Path:
    return cache_root() / "venv" / "bin"


def tex_bin() -> Path | None:
    """The binaries of the portable TeX Live, if TeX Live is installed."""
    for dvisvgm in sorted((cache_root() / "texlive" / "bin").glob("*/dvisvgm")):
        if os.access(dvisvgm, os.X_OK):
            return dvisvgm.parent
    return None


def in_video(root: str | Path | None = None) -> Path:
    """The folder of the video project: `root`, or VIDEO_ROOT, or the nearest parent with
    a video.toml file."""
    if root is not None:
        return Path(root).resolve()
    if os.environ.get("VIDEO_ROOT"):
        return Path(os.environ["VIDEO_ROOT"]).resolve()
    for folder in [Path.cwd(), *Path.cwd().parents]:
        if (folder / CONFIG_NAME).is_file():
            return folder
    raise LookupError(
        "This is not a video project. Start one with `videogen new <folder>`, or go to the folder of a video."
    )
