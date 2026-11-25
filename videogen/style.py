"""The look of a video project: the background image with the logo that the scenes show.

Manim does not resize the background image: it cuts it to the pixels of the render. Thus the
image is composed at the exact size of each render (1080p for the film, 480p for the preview).
"""

from __future__ import annotations

import math
import os
from pathlib import Path

from PIL import Image

from videogen import config as video_config

LOGO_MARGIN = 44     # the pixels between the logo and the top and right edges, at 1080p
LOGO_AIR = 20        # the pixels of air around the logo, where the scenes put no text


def background_image(config: video_config.VideoConfig, width: int, height: int, base: str = "#161C20") -> Path | None:
    """The image that the scenes show behind their content, at the size of the render. The
    background image covers the frame, and the logo is small at the top right. The image is
    composed once for each size, and again when the background or the logo changes. None when
    the project has neither."""
    if not config.background and not config.logo:
        return None
    sources = []
    for name in (config.background, config.logo):
        if name:
            path = (config.root / name).resolve()
            if not path.is_file():
                raise LookupError(f"No image: {path}")
            sources.append(path)
    target = config.root / "build" / "style" / f"background_{width}x{height}.png"
    if target.is_file() and all(target.stat().st_mtime >= path.stat().st_mtime for path in sources):
        return target
    frame = Image.new("RGB", (width, height), base)
    if config.background:
        with Image.open(sources[0]) as picture:
            picture = picture.convert("RGB")
            scale = max(width / picture.width, height / picture.height)
            size = (math.ceil(picture.width * scale), math.ceil(picture.height * scale))
            frame.paste(picture.resize(size, Image.LANCZOS), ((width - size[0]) // 2, (height - size[1]) // 2))
    if config.logo:
        with Image.open(sources[-1]) as picture:
            logo = picture.convert("RGBA")
            tall = max(1, round(config.logo_height * height / 1080))
            wide = max(1, round(logo.width * tall / logo.height))
            margin = round(LOGO_MARGIN * height / 1080)
            small = logo.resize((wide, tall), Image.LANCZOS)
            frame.paste(small, (width - margin - wide, margin), small)   # the alpha of the logo is the mask
    target.parent.mkdir(parents=True, exist_ok=True)
    # The scenes of a video render at the same time. The image takes its place in one operation,
    # so that a scene never reads a file that another scene is still writing.
    partial = target.with_name(f"{target.stem}.{os.getpid()}.partial.png")
    try:
        frame.save(partial)
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)
    return target


def logo_corner(config: video_config.VideoConfig, width: int, height: int) -> tuple[float, float] | None:
    """The corner of the logo in the units of a scene of `width` by `height` units: the point
    (x, y) of its bottom-left corner, with 20 pixels of air around it. The scenes keep their
    text to the left and below this point. None when the project has no logo."""
    if not config.logo:
        return None
    path = (config.root / config.logo).resolve()
    if not path.is_file():
        raise LookupError(f"No image: {path}")
    with Image.open(path) as picture:
        wide = config.logo_height * picture.width / picture.height
    unit = height / 1080
    return (
        width / 2 - (LOGO_MARGIN + wide + LOGO_AIR) * unit,
        height / 2 - (LOGO_MARGIN + config.logo_height + LOGO_AIR) * unit,
    )
