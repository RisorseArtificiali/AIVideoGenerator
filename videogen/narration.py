"""The script of a video: narration.py in the folder of the video project.

The script is the single source of truth of the voice-over. It has:

    SCENE_ORDER = ["ch00", "ch01", ...]        the scenes, in order
    CHAPTERS = {"ch01": ("1", "The idea")}     number and title of each scene
    NARRATION = {"ch01": [Beat("a1", "text", "what is on screen"), ...]}

One beat is one or two sentences: one audio clip. The scene animates one beat at a time.
"""

from __future__ import annotations

import importlib.util
import re
from collections import namedtuple
from dataclasses import dataclass, field
from pathlib import Path

Beat = namedtuple("Beat", "key text visual")

SCENE_KEY = re.compile(r"^ch\d{2}$")


@dataclass
class Script:
    root: Path
    order: list[str]
    chapters: dict[str, tuple[str, str]]
    beats: dict[str, list[Beat]]
    spoken_rules: list[tuple[str, str]] = field(default_factory=list)

    @property
    def beat_count(self) -> int:
        return sum(len(beats) for beats in self.beats.values())

    def keys(self, scene: str) -> list[str]:
        return [beat.key for beat in self.beats[scene]]


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise RuntimeError(f"Error in {path}: {error}") from error
    return module


def load_script(root: Path) -> Script:
    """Read and validate narration.py. Optional: spoken_rules.py with RULES = [(pattern, replacement), ...]."""
    path = root / "narration.py"
    if not path.is_file():
        raise LookupError(f"No narration.py in {root}. This is not a video project.")
    module = _load_module(path, "video_narration")
    for name in ("SCENE_ORDER", "CHAPTERS", "NARRATION"):
        if not hasattr(module, name):
            raise RuntimeError(f"{path} does not define {name}.")
    order = list(module.SCENE_ORDER)
    if not order:
        raise RuntimeError(f"{path}: SCENE_ORDER is empty.")
    beats = {}
    for scene in order:
        if not SCENE_KEY.match(scene):
            raise RuntimeError(f"{path}: the scene name '{scene}' is not valid. Use ch00, ch01, ...")
        if scene not in module.CHAPTERS:
            raise RuntimeError(f"{path}: CHAPTERS has no entry for '{scene}'. Use ('', '') for a scene without a title.")
        rows = module.NARRATION.get(scene)
        if not rows:
            raise RuntimeError(f"{path}: NARRATION has no beats for '{scene}'.")
        seen = set()
        beats[scene] = []
        for row in rows:
            if len(row) != 3 or not all(isinstance(part, str) for part in row):
                raise RuntimeError(f"{path}: each beat of '{scene}' is Beat(key, text, visual_note) with three strings.")
            if not row[0] or row[0] in seen:
                raise RuntimeError(f"{path}: the beat key '{row[0]}' of '{scene}' is empty or is used two times.")
            if not row[1].strip():
                raise RuntimeError(f"{path}: the beat '{row[0]}' of '{scene}' has no text.")
            seen.add(row[0])
            beats[scene].append(Beat(*row))
    rules = []
    rules_path = root / "spoken_rules.py"
    if rules_path.is_file():
        rules = [(pattern, replacement) for pattern, replacement in getattr(_load_module(rules_path, "video_spoken_rules"), "RULES", [])]
    return Script(root=root, order=order, chapters=dict(module.CHAPTERS), beats=beats, spoken_rules=rules)
