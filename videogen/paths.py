"""Where things live: the template, the tools, and the video project."""

from __future__ import annotations

import os
from pathlib import Path

CONFIG_NAME = "video.toml"
TOOLS_FOLDER = ".tools"


def template_root() -> Path:
    """The folder of the AIVideoGenerator repository that holds this package."""
    return Path(__file__).resolve().parent.parent


def tools_root() -> Path:
    """The folder that `tools/setup.sh` makes: the Python environment, TeX Live, and the
    models of the offline speech recognizer.

    Default: `.tools` in the repository, so that the tools stay with the project. A sandbox
    that keeps the folder of the project also keeps the tools. Set AIVIDEOGEN_TOOLS to use
    a different folder.
    """
    if os.environ.get("AIVIDEOGEN_TOOLS"):
        return Path(os.environ["AIVIDEOGEN_TOOLS"]).expanduser().resolve()
    return template_root() / TOOLS_FOLDER


def venv_bin() -> Path:
    return tools_root() / "venv" / "bin"


def tex_bin() -> Path | None:
    """The binaries of the portable TeX Live, if TeX Live is installed."""
    for dvisvgm in sorted((tools_root() / "texlive" / "bin").glob("*/dvisvgm")):
        if os.access(dvisvgm, os.X_OK):
            return dvisvgm.parent
    return None


def models_root() -> Path:
    """The models that the commands download. They stay with the tools."""
    return tools_root() / "models"


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
