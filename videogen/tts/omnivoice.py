"""OmniVoice: a speech engine with a local model, and a sample of a voice.

The model (k2-fsa/OmniVoice: 0.6 billion parameters, 646 languages) needs PyTorch, which is not
in the environment of the tools. It lives in its own environment, `.tools/venv-omnivoice`, and
runs in a worker process (`omnivoice_worker.py`). This class starts the worker, sends it the
words to read, and receives the audio and the time of each word. Nothing leaves the computer: the
worker reads the model and the sample of the voice on the disk, and does not use the network.

A voice is a sample of a voice with its transcript: `voices/<name>.wav` and `voices/<name>.txt`,
in the folder of the video project or in the folder of the template. The model copies the voice,
and also its pauses and its level: use one or two sentences (2 to 20 seconds), in the language of
the video. A third file, `voices/<name>.toml`, is optional: it gives the speed of the voice
(`rate = "+32%"`), and `videogen new` writes it in `video.toml`.

`tools/setup-omnivoice.sh` installs the engine. The license of the model is CC-BY-NC.
"""

from __future__ import annotations

import atexit
import base64
import hashlib
import importlib.util
import json
import os
import re
import select
import shutil
import subprocess
import sys
import tempfile
import threading
import tomllib
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from videogen import paths
from videogen.langs import Language
from videogen.tts import SAMPLE_RATE, Clip, Engine, Status
from videogen.tts import omnivoice_worker as worker

ENVIRONMENT = "venv-omnivoice"                    # the Python environment of the model, in the folder of the tools
MODEL = Path("models", "omnivoice")               # the model of speech
ALIGNER = Path("models", "mms-fa")                # the model that gives the time of each word
WORKER = Path(__file__).with_name("omnivoice_worker.py")
AUDIO = (".wav", ".flac", ".ogg", ".mp3")   # the files accepted for a sample of a voice: the formats that the library of the model reads
RATE = re.compile(r"([+-])(\d+)%")
TIMEOUT = 900.0        # the seconds given to the worker for one clip: without a GPU, the model is slow
START = 240.0         # the seconds given to the worker to start: it loads the model from the disk
GRACE = 10.0          # the seconds given to the worker to stop, before it is killed
LEAD = 0.06           # the words of the subtitles and of the cues come this much before their sound
HELP = ("Put a sample of a voice in voices/<name>.wav, with the words that it says in voices/<name>.txt: "
        "in the folder of the video, or in the folder of the template. `voice` can also be the path of an audio file.")


@dataclass(frozen=True)
class Sample:
    """A voice: a sample of a voice, and the words that it says."""

    name: str
    path: Path
    text: str


def speed_of(rate: str) -> float:
    """The speed of the model for the rate of video.toml: "+10%" gives 1.1."""
    match = RATE.fullmatch(rate.strip())
    if not match:
        return 1.0
    return 1 + int(match.group(2)) / 100 * (1 if match.group(1) == "+" else -1)


def folders_of(project: Path | None) -> list[Path]:
    """The folders with the samples of the voices. The folder of the video comes first."""
    return [folder for folder in (project / "voices" if project else None, paths.template_root() / "voices") if folder]


def find_sample(name: str, folders: list[Path], project: Path | None = None) -> Sample | None:
    """The sample of a voice. `name` is a voice of a folder `voices/`, or the path of an audio
    file (relative to the folder of the video). The transcript is in the text file that has the
    same name."""
    if "/" in name or name.lower().endswith(AUDIO):   # the path of an audio file
        path = Path(name)
        path = path if path.is_absolute() or not project else project / path
        files = [path] if path.suffix.lower() in AUDIO else [path.with_name(path.name + extension) for extension in AUDIO]
        candidates = [(path.stem, file) for file in files]
    else:
        candidates = [(name, folder / f"{name}{extension}") for folder in folders for extension in AUDIO]
    for voice, path in candidates:
        transcript = path.with_name(f"{path.stem}.txt")
        if path.is_file() and transcript.is_file():
            return Sample(voice, path.resolve(), " ".join(transcript.read_text(encoding="utf-8").split()))
    return None


def sample_names(folders: list[Path]) -> list[str]:
    """The voices of the folders, in their order, without the doubles."""
    names = []
    for folder in folders:
        for transcript in sorted(folder.glob("*.txt")) if folder.is_dir() else []:
            sample = find_sample(transcript.stem, folders)
            if sample and sample.name not in names:
                names.append(sample.name)
    return names


class Worker:
    """The process that runs the model. It starts at the first request, and it receives one
    request at a time: the model makes one clip at a time."""

    def __init__(self, command: list[str], environment: dict[str, str] | None = None, timeout: float = TIMEOUT, start: float = START,
                 grace: float = GRACE):
        self.command = command
        self.environment = environment
        self.timeout, self.start, self.grace = timeout, start, grace
        self.lock = threading.Lock()
        self.process: subprocess.Popen | None = None
        self.log = None
        self.device = ""
        atexit.register(self.close)

    def request(self, payload: dict) -> dict:
        """Send a request to the worker, and return its answer."""
        with self.lock:
            process = self.process or self._start()
            try:
                process.stdin.write(json.dumps(payload).encode("utf-8") + b"\n")
                process.stdin.flush()
                answer = self._answer(process, self.timeout)
            except OSError as error:
                answer = {"ok": False, "error": self._stop(f"the worker of OmniVoice stopped: {error}")}
            if answer is None:
                answer = {"ok": False, "error": self._stop(f"the worker of OmniVoice gave no answer in {self.timeout:.0f} seconds.")}
            return answer

    def _start(self) -> subprocess.Popen:
        """Start the worker, and wait for its first answer: it says that the model is ready."""
        log = tempfile.TemporaryFile("w+", encoding="utf-8", errors="replace")
        try:
            self.process = process = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log,
                                                      env=self.environment, cwd=tempfile.gettempdir())
        except OSError as error:
            log.close()
            raise RuntimeError(f"OmniVoice does not start: {error}. Start tools/setup-omnivoice.sh.") from error
        self.log = log
        answer = self._answer(process, self.start)
        if answer is None:
            answer = {"ok": False, "error": self._stop(f"the worker of OmniVoice is not ready after {self.start:.0f} seconds.")}
        if not answer.get("ok"):
            raise RuntimeError(f"OmniVoice does not start: {answer.get('error', 'unknown error')}")
        self.device = answer.get("device", "")
        return process

    def _answer(self, process: subprocess.Popen, seconds: float) -> dict | None:
        """The next answer of the worker, or None when it does not come in `seconds`."""
        if not select.select([process.stdout], [], [], seconds)[0]:
            return None
        line = process.stdout.readline()
        if not line.endswith(b"\n"):                   # the end of the stream: the worker stopped
            return {"ok": False, "error": self._stop("the worker of OmniVoice stopped.")}
        try:
            return json.loads(line)
        except ValueError:
            return {"ok": False, "error": self._stop("the worker of OmniVoice sent an answer that is not JSON.")}

    def _stop(self, message: str) -> str:
        """Stop the worker. Returns the message, with the last lines of its log."""
        process, log, self.process = self.process, self.log, None
        if process is not None:
            self._end(process)
        if log is None:
            return message
        log.seek(0)
        lines = [line for line in log.read().replace("\r", "\n").splitlines() if line.strip()]
        log.close()
        self.log = None
        return message + ("\n" + "\n".join(lines[-6:]) if lines else "")

    def _end(self, process: subprocess.Popen) -> None:
        """Close the input of the worker: it sees the end and stops. If it does not, kill it."""
        try:
            process.stdin.close()
            process.wait(timeout=self.grace)
        except Exception:
            process.kill()
            process.wait()
        finally:
            process.stdout.close()

    def close(self) -> None:
        """Stop the worker, if it runs. `atexit` calls this when videogen ends."""
        if self.process is not None:
            self._stop("")


class OmniVoiceEngine(Engine):
    """OmniVoice, a local model that reads the text with a voice cloned from a sample."""

    id = "omnivoice"
    name = "omnivoice"
    optional = True
    voices_help = HELP

    def __init__(self, command: list[str] | None = None, folders: list[Path] | None = None):
        """`command` starts the worker, `folders` have the samples of the voices. The tests change them."""
        self.language: Language | None = None
        self.project: Path | None = None
        self.folders = folders
        environment = None
        if command is None:
            command = self.command()
            # The worker reads everything on the disk: it must never look for a model online.
            environment = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
        self.worker = Worker(command, environment)

    @staticmethod
    def command() -> list[str]:
        """The command that starts the worker in the environment of the model."""
        tools = paths.tools_root()
        command = [str(tools / ENVIRONMENT / "bin" / "python"), "-I", "-W", "ignore", str(WORKER),
                   "--model", str(tools / MODEL), "--aligner", str(tools / ALIGNER)]
        device = os.environ.get("OMNIVOICE_DEVICE")     # another device than the first GPU: for example cuda:1, mps or cpu
        return command + ["--device", device] if device else command

    def configure(self, root: Path, language: Language) -> None:
        self.project, self.language = root, language

    def status(self) -> Status:
        tools = paths.tools_root()
        missing = []
        if not (tools / ENVIRONMENT / "bin" / "python").is_file():
            missing.append(f"the environment {ENVIRONMENT}")
        if not (tools / MODEL / "model.safetensors").is_file():
            missing.append(f"the model in {MODEL.as_posix()}")
        if not (tools / ALIGNER / "checkpoints" / "model.pt").is_file():
            missing.append(f"the model that gives the time of the words, in {ALIGNER.as_posix()}")
        if importlib.util.find_spec("num2words") is None:
            missing.append("the package num2words in the environment of the tools")
        if missing:
            return Status(False, "not installed (" + ", ".join(missing) + "). Start tools/setup-omnivoice.sh: about 11 GB.")
        voices = self.voices(self.language, self.project)
        if voices:
            shown = []
            for name in voices:
                rate = self.default_rate(name, self.project)
                shown.append(f"{name} (rate {rate})" if rate else name)
            detail = "voices: " + ", ".join(shown)
        else:
            detail = "no voice yet: put a sample of a voice in a folder voices/ (docs/5-tts-engines.md)"
        return Status(True, f"a local model on the {self._machine()}, with a sample of a voice; {detail}")

    def voices(self, language, root: Path | None = None) -> list[str]:
        return sample_names(self.folders if self.folders is not None else folders_of(root))

    def default_rate(self, voice: str | None, root: Path | None = None) -> str:
        """The speed of a voice, from its third file: `voices/<name>.toml`, with `rate = "+32%"`.
        Without a voice, it is the speed of the first voice of the folders. An empty string when
        the voice has no file, and when there is no voice."""
        folders = self.folders if self.folders is not None else folders_of(root)
        name = voice or next(iter(sample_names(folders)), None)
        sample = find_sample(name, folders, root) if name else None
        path = sample.path.with_suffix(".toml") if sample else None
        if path is None or not path.is_file():
            return ""
        value = str(tomllib.loads(path.read_text(encoding="utf-8")).get("rate", "")).strip()
        if value and not RATE.fullmatch(value):
            raise ValueError(f"The rate '{value}' in {path} is not valid. Use a value such as '+5%' or '-10%'.")
        return value

    def signature(self, voice: str, rate: str) -> str:
        """The clips change when the sample of the voice changes, or when the worker changes the audio."""
        sample = find_sample(voice, self._folders(), self.project)
        if sample is None:
            return ""
        return f"|clips {worker.CLIPS}|{hashlib.sha1(sample.path.read_bytes()).hexdigest()}|{hashlib.sha1(sample.text.encode('utf-8')).hexdigest()}"

    def synthesize(self, text: str, voice: str, rate: str) -> Clip:
        folders = self._folders()
        sample = find_sample(voice, folders, self.project)
        if sample is None:
            known = ", ".join(sample_names(folders)) or "none"
            raise RuntimeError(f"OmniVoice has no voice '{voice}' (the voices of the folders voices/ are: {known}). {HELP}")
        if not sample.text:
            raise RuntimeError(f"The transcript of the voice '{voice}' is empty: {sample.path.with_name(sample.path.stem + '.txt')}")
        code = self.language.code if self.language else "en"
        try:
            from videogen.tts.numbers import spoken_tokens
        except ImportError as error:
            raise RuntimeError("The package num2words is not in the environment of the tools. Start tools/setup-omnivoice.sh.") from error
        # The model does not read digits well: it receives the numbers in words. The subtitles
        # keep the text as it is written: each token of the text receives the time of its words.
        tokens = spoken_tokens(text, code)
        words = [word for _token, group in tokens for word in group]
        if not words:
            raise RuntimeError("OmniVoice has no words to read in this beat.")
        # The model chooses at random: the seed comes from the text, so that a clip made again is the same.
        seed = int(hashlib.sha256(f"{sample.path}|{rate}|{text}".encode("utf-8")).hexdigest()[:8], 16)
        answer = self.worker.request({
            "op": "synthesize", "text": " ".join(words), "language": code, "ref": str(sample.path), "ref_text": sample.text,
            "speed": speed_of(rate), "seed": seed,
        })
        if not answer.get("ok"):
            raise RuntimeError(f"OmniVoice: {answer.get('error', 'unknown error')}")
        if answer.get("rate") != SAMPLE_RATE:
            raise RuntimeError(f"OmniVoice gave audio at {answer.get('rate')} Hz, not {SAMPLE_RATE} Hz.")
        samples = np.frombuffer(base64.b64decode(answer["samples"]), dtype="<f4").copy()
        return Clip(samples, times_of(tokens, answer.get("spans", []), len(samples) / SAMPLE_RATE))

    def _folders(self) -> list[Path]:
        return self.folders if self.folders is not None else folders_of(self.project)

    @staticmethod
    def _machine() -> str:
        """Where the model runs, said in the answer of `status`."""
        device = os.environ.get("OMNIVOICE_DEVICE")
        if device:
            return f"the device {device} of OMNIVOICE_DEVICE"
        if sys.platform == "darwin":
            return "GPU of the system" if shutil.which("system_profiler") else "processor"
        if shutil.which("nvidia-smi"):
            try:
                names = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True, timeout=20)
                if names.returncode == 0 and names.stdout.strip():
                    return names.stdout.strip().splitlines()[0].strip()
            except (OSError, subprocess.SubprocessError):
                pass
        return "processor (slow)"


def times_of(tokens: list[tuple[str, list[str]]], spans: list, length: float) -> list[tuple[float, float, str]]:
    """The time of each token of the text: from the start of its first word to the end of its
    last one. A token that the voice does not read has no time: it takes the end of the token
    before. The tokens are those of the text of the beat: the subtitles show them as they are written."""
    count = sum(len(group) for _token, group in tokens)
    if len(spans) != count:
        raise RuntimeError(f"OmniVoice gave the time of {len(spans)} words; the text has {count}.")
    timed, index, cursor = [], 0, 0.0
    for token, group in tokens:
        if group:
            start, end = float(spans[index][0]) - LEAD, float(spans[index + len(group) - 1][1]) - LEAD
            index += len(group)
        else:
            start = end = cursor
        start = min(max(start, cursor), length)
        end = min(max(end, start), length)
        timed.append((round(start, 3), round(end - start, 3), token))
        cursor = end
    return timed
