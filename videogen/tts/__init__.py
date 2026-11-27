"""Speech synthesis engines. An engine changes one line of text to audio, and gives the
time of each word. To add an engine (a service with an API key, or a local model on the
GPU), write a subclass of Engine and put it in ENGINES. See docs/5-tts-engines.md."""

from __future__ import annotations

import asyncio
import io
import os
import re
import subprocess
import tempfile
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from videogen.langs import Language

SAMPLE_RATE = 48000


@dataclass
class Clip:
    samples: np.ndarray                                   # mono, float32, from -1 to 1
    words: list[tuple[float, float, str]] = field(default_factory=list)   # (start s, duration s, word)


@dataclass
class Status:
    available: bool
    detail: str = ""


def decode_audio(path: Path) -> np.ndarray:
    """Any audio file to mono float32 at SAMPLE_RATE: the mean of its channels.

    The file goes through ffmpeg as a WAV in a pipe, with its channels side by side. The change to
    mono of ffmpeg (`-ac 1`) is not the mean: it multiplies each channel by 0.707. A stereo file
    gains 3 decibels, and a loud recording clips in a file of 16 bits.
    """
    try:
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(path), "-f", "wav", "-c:a", "pcm_s16le", "-ar", str(SAMPLE_RATE), "-"],
            check=True, capture_output=True,
        ).stdout
    except subprocess.CalledProcessError as error:
        reason = error.stderr.decode("utf-8", "replace").strip()[-200:]
        raise RuntimeError(f"ffmpeg does not read '{path}': {reason}") from error
    with wave.open(io.BytesIO(raw)) as handle:
        # The file comes from a pipe: its length is not in the header, so all the frames are read.
        frames = np.frombuffer(handle.readframes(handle.getnframes()), dtype="<i2").astype(np.float32) / 32768
        channels = handle.getnchannels()
    return frames.reshape(-1, channels).mean(axis=1)


class Engine:
    """The interface of a speech engine."""

    id = ""
    name = ""
    needs_env: tuple[str, ...] = ()     # variables that the engine reads from .env
    optional = False                    # an engine that tools/setup.sh does not install: `videogen doctor` does not count it
    voices_help = ""                    # how to give the engine a voice, when its voices are not a list

    def configure(self, root: Path, language: Language) -> None:
        """The folder of the video project and its language, before the first call of `synthesize`.
        An engine that needs them keeps them in an attribute: `videogen tts` calls this one time."""

    def status(self) -> Status:
        missing = [name for name in self.needs_env if not os.environ.get(name)]
        if missing:
            return Status(False, "no " + ", ".join(missing) + " in .env")
        return Status(True)

    def voices(self, language, root: Path | None = None) -> list[str]:
        """The voices of the engine for one videogen.langs.Language. `root` is the folder of the
        video project, when the command knows it: an engine can keep its voices in that folder."""
        return list(language.voices.get(self.id, ()))

    def signature(self, voice: str, rate: str) -> str:
        """What the fingerprint of a clip adds when the voice depends on files that can change,
        as a sample of a voice. Then `videogen tts` makes the clips again when the file changes.
        An empty string for most engines."""
        return ""

    def default_rate(self, voice: str | None, root: Path | None = None) -> str:
        """The speed of a voice of the engine, as `videogen new` writes it in `video.toml`. An empty
        string when the voice has none, as for most engines: the project starts at `+0%`."""
        return ""

    def synthesize(self, text: str, voice: str, rate: str) -> Clip:
        raise NotImplementedError


class EdgeEngine(Engine):
    """edge-tts: the Read Aloud service of Microsoft Edge. It is online and needs no key.

    It is not an official API: the service can change or stop without notice.
    """

    id = "edge-tts"
    name = "edge-tts"

    def __init__(self, retries: int = 5):
        self.retries = retries

    def status(self) -> Status:
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            return Status(False, "the package edge-tts is not installed")
        return Status(True, "online service of Microsoft Edge, no key necessary")

    def online_voices(self, locale: str) -> list[dict]:
        """The voices that the service offers for a language. This needs a network connection."""
        import edge_tts

        voices = asyncio.run(edge_tts.list_voices())
        chosen = [voice for voice in voices if voice["ShortName"].lower().startswith(locale.lower())]
        return sorted(chosen, key=lambda voice: voice["ShortName"])

    async def _stream(self, text: str, voice: str, rate: str, target: Path) -> list:
        import edge_tts

        words = []
        communicate = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
        with open(target, "wb") as handle:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    handle.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    words.append((round(chunk["offset"] / 1e7, 3), round(chunk["duration"] / 1e7, 3), chunk["text"]))
        return words

    def synthesize(self, text: str, voice: str, rate: str) -> Clip:
        for attempt in range(1, self.retries + 1):
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    target = Path(tmp) / "clip.mp3"
                    words = asyncio.run(self._stream(text, voice, rate, target))
                    if target.stat().st_size < 1000:
                        raise RuntimeError("the service returned no audio")
                    samples = decode_audio(target)
                return Clip(samples, words)
            except Exception as error:   # the service drops some connections: try again
                if attempt == self.retries:
                    raise
                print(f"  edge-tts: attempt {attempt} failed ({error}); try again")
                asyncio.run(asyncio.sleep(1.5 * attempt))


ENGINES: dict[str, Engine] = {engine.id: engine for engine in (EdgeEngine(),)}


def get_engine(engine_id: str) -> Engine:
    try:
        return ENGINES[engine_id]
    except KeyError:
        raise KeyError(f"Unknown speech engine '{engine_id}'. Available: {', '.join(ENGINES)}") from None


ENV_LINE = re.compile(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


def load_env(*paths: Path) -> list[str]:
    """Put the variables of .env files in the environment. A variable that is already set
    keeps its value. Returns the names of the variables that were set."""
    loaded = []
    for path in paths:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            match = ENV_LINE.match(line)
            if not match or line.lstrip().startswith("#"):
                continue
            name, value = match.groups()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            if name not in os.environ:
                os.environ[name] = value
                loaded.append(name)
    return loaded


# The local engine comes after the base class, because its module imports the names defined above.
from videogen.tts.omnivoice import OmniVoiceEngine  # noqa: E402

ENGINES["omnivoice"] = OmniVoiceEngine()
