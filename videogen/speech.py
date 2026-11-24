"""The voice-over of a video: one audio clip for each narration beat."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from videogen import paths
from videogen.config import VideoConfig
from videogen.narration import Script
from videogen.tts import SAMPLE_RATE, Engine

TAIL_KEEP = 0.14   # seconds of silence kept after the last word
FLOOR = 0.004      # amplitude below which a sample is silence


def spoken(text: str, rules) -> str:
    """The text as the voice reads it: the rules replace the names that the voice reads badly."""
    for pattern, replacement in rules:
        text = re.sub(pattern, replacement, text)
    return text


def trim_tail(samples: np.ndarray, floor: float = FLOOR, keep: float = TAIL_KEEP) -> np.ndarray:
    """Remove the long silence at the end of a clip."""
    loud = np.flatnonzero(np.abs(samples) > floor)
    if loud.size == 0:
        return samples
    return samples[: min(len(samples), loud[-1] + int(keep * SAMPLE_RATE))]


def write_wav(path: Path, samples: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes((np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes())


def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path)) as handle:
        if (handle.getframerate(), handle.getnchannels(), handle.getsampwidth()) != (SAMPLE_RATE, 1, 2):
            raise ValueError(f"{path} is not mono 16-bit PCM at {SAMPLE_RATE} Hz")
        return np.frombuffer(handle.readframes(handle.getnframes()), dtype="<i2").astype(np.float32) / 32767


def timing_path(root: Path, scene: str) -> Path:
    return root / "build" / "timing" / f"{scene}.json"


def clip_path(root: Path, scene: str, key: str) -> Path:
    return root / "build" / "audio" / scene / f"{key}.wav"


def load_timing(root: Path, scene: str) -> dict:
    return json.loads(timing_path(root, scene).read_text(encoding="utf-8"))


def track_hash(script: Script, scene: str, timing: dict) -> str:
    """A fingerprint of the narration of a scene (the text and the length of the clips).
    A scene saves it when it renders. The assembly step uses it to find an old render."""
    digest = hashlib.sha1()
    for beat in script.beats[scene]:
        digest.update(f"{beat.key}|{beat.text}|{timing['beats'][beat.key]['dur']}".encode("utf-8"))
    return digest.hexdigest()[:16]


def _rules(script: Script, config: VideoConfig):
    return list(config.lang.spoken_rules) + list(script.spoken_rules)


def synthesize(script: Script, config: VideoConfig, engine: Engine, scenes=None, force: bool = False, workers: int = 4, log=print) -> None:
    """Make the clips that are missing, or older than their text."""
    voice, rate = config.resolved_voice, config.rate
    stale, timings = [], {}
    for scene in scenes or script.order:
        path = timing_path(config.root, scene)
        timing = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"beats": {}}
        timing["beats"] = {key: value for key, value in timing["beats"].items() if key in script.keys(scene)}
        timings[scene] = timing
        for beat in script.beats[scene]:
            text = spoken(beat.text, _rules(script, config))
            digest = hashlib.sha1(f"{engine.id}|{voice}|{rate}|{text}".encode("utf-8")).hexdigest()[:16]
            entry = timing["beats"].get(beat.key)
            clip = clip_path(config.root, scene, beat.key)
            if entry and entry.get("hash") == "manual" and clip.is_file():
                continue     # a recording of the user
            if not force and entry and entry.get("hash") == digest and entry.get("words") and clip.is_file():
                continue
            stale.append((scene, beat, text, digest, clip))
    if stale:
        log(f"{len(stale)} clips to synthesize with {engine.id} ({voice}, {rate})")

        def make(item):
            scene, beat, text, digest, clip = item
            clip_data = engine.synthesize(text, voice, rate)
            samples = trim_tail(clip_data.samples)
            write_wav(clip, samples)
            return scene, beat, digest, text, samples, clip_data.words

        with ThreadPoolExecutor(max_workers=workers) as pool:
            for scene, beat, digest, text, samples, words in pool.map(make, stale):
                timings[scene]["beats"][beat.key] = {
                    "text": beat.text, "spoken": text, "hash": digest,
                    "dur": round(len(samples) / SAMPLE_RATE, 3), "words": words,
                }
                log(f"  {scene}/{beat.key}: {len(samples) / SAMPLE_RATE:.2f} s")
    for scene, timing in timings.items():
        timing.update(engine=engine.id, voice=voice, rate=rate)
        save_timing(config.root, scene, timing)


def save_timing(root: Path, scene: str, timing: dict) -> None:
    path = timing_path(root, scene)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(timing, ensure_ascii=False, indent=1), encoding="utf-8")


def adopt_recordings(script: Script, config: VideoConfig, folder: Path, force: bool = False, log=print) -> tuple[int, int]:
    """Use the recordings of the user as the voice-over. The folder has one audio file for
    each beat, named <scene>_<beat>.<extension>: for example ch02_c8.wav."""
    adopted = skipped = 0
    for path in sorted(folder.iterdir()):
        scene, _, key = path.stem.partition("_")
        beats = {beat.key: beat for beat in script.beats.get(scene, [])}
        if scene not in script.order or key not in beats:
            skipped += 1
            log(f"Skip (unknown beat): {path.name}")
            continue
        timing = load_timing(config.root, scene) if timing_path(config.root, scene).is_file() else {"beats": {}}
        if timing["beats"].get(key, {}).get("hash") == "manual" and not force:
            skipped += 1
            log(f"Skip (already a recording; use --force): {path.name}")
            continue
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(SAMPLE_RATE), "-"],
            check=True, capture_output=True,
        ).stdout
        samples = np.frombuffer(raw, dtype=np.float32).copy()
        loud = np.flatnonzero(np.abs(samples) > FLOOR)
        if loud.size == 0:
            raise ValueError(f"{path.name} has no sound")
        samples = trim_tail(samples[max(0, loud[0] - int(0.12 * SAMPLE_RATE)):])
        write_wav(clip_path(config.root, scene, key), samples)
        timing["beats"][key] = {
            "text": beats[key].text, "hash": "manual", "dur": round(len(samples) / SAMPLE_RATE, 3), "words": [],
        }
        save_timing(config.root, scene, timing)
        adopted += 1
        log(f"Adopted {scene}/{key}: {len(samples) / SAMPLE_RATE:.2f} s")
    return adopted, skipped
