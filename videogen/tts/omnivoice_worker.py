"""The worker of the OmniVoice engine. It runs in the environment of the model, not in the
environment of the tools: it imports nothing from videogen.

    python -I omnivoice_worker.py --model <folder> --aligner <folder> [--device cuda:0] [--check]

Without `--check`, the worker reads one JSON request for each line of the standard input, and
writes one JSON answer for each one on the standard output. Everything else goes to the
standard error.

    {"op": "ping"}
    gives {"ok": true, "device": "cuda:0"}

    {"op": "synthesize", "text": "...", "language": "it", "ref": "voice.wav", "ref_text": "...",
     "speed": 1.0, "stretch": 1.0, "seed": 7}
    gives {"ok": true, "rate": 48000, "samples": "<float32 in base64>", "spans": [[start, end], ...]}

`spans` has the start and the end of each word of `text`, in seconds, in the audio of the answer.
`speed` is the speed of the model. `stretch` makes the clip shorter in time after the generation:
1.1 gives a clip 10 per cent shorter, with the same pitch.
An error gives {"ok": false, "error": "..."}. With `--check`, the worker loads the model and the
aligner, says whether they operate, and stops.

The model gives the audio only. The worker:

- reads the time of each word with a forced alignment of the text on the audio (MMS_FA, the model
  of torchaudio);
- makes the clip shorter in time when `stretch` is above 1: made to speak faster than 20 per cent,
  the model stops saying some words clearly, so the engine keeps it there and compresses the time;
- removes the long silences: the model copies the pauses of the sample of the voice, and a sample
  with a long pause gives clips with pauses of one or two seconds;
- sets the level of the audio: the model copies the level of the sample too, and a quiet sample
  gives a quiet clip.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import time
import traceback
import unicodedata
import warnings
from pathlib import Path

import numpy as np

CLIPS = 1                 # the form of the clips: change it when this file changes the audio that it gives
TIME_STRETCH = 1          # the form of the compression in time: the same, when the way to compress changes
RATE_OUT = 48000          # the sample rate of the clips of videogen
LEAD = 0.15               # the seconds of silence before the first word
TAIL = 0.15               # the seconds of silence after the last word
LONG_PAUSE = 0.7          # a pause longer than this...
SHORT_PAUSE = 0.5         # ...becomes this
FLOOR = 25.0              # a frame is speech when its level is less than this under the loud speech (decibels)
LEVEL = 0.10              # the RMS of a clip, as the clips of edge-tts
PEAK = 0.95               # the highest sample of a clip
SAMPLE_SECONDS = (2.0, 20.0)   # the length accepted for a sample of a voice


# ---------------------------------------------------------------- the audio, without the model


def _frames(wave: np.ndarray, rate: int) -> tuple[np.ndarray, int]:
    """The level of each frame of 20 milliseconds, every 10 milliseconds, and the samples between two frames."""
    size, hop = max(1, int(0.02 * rate)), max(1, int(0.01 * rate))
    count = max(0, (len(wave) - size) // hop + 1)
    if not count:
        return np.zeros(0), hop
    blocks = np.lib.stride_tricks.as_strided(wave, shape=(count, size), strides=(wave.strides[0] * hop, wave.strides[0]))
    return 10 * np.log10(np.mean(blocks.astype(np.float64) ** 2, axis=1) + 1e-12), hop


def _without_clicks(flags: np.ndarray, shortest: int) -> np.ndarray:
    """The flags without the runs shorter than `shortest` frames: a click in a pause is not a word."""
    result, start = flags.copy(), None
    for index, flag in enumerate(list(flags) + [False]):
        if flag and start is None:
            start = index
        elif not flag and start is not None:
            if index - start < shortest:
                result[start:index] = False
            start = None
    return result


def _voiced(wave: np.ndarray, rate: int) -> tuple[np.ndarray, int]:
    """For each frame: True when it has the energy of a sound. The model leaves a little noise
    in the pauses, so the threshold follows the level of the clip."""
    levels, hop = _frames(wave, rate)
    if len(levels) < 5:
        return np.ones(len(levels), dtype=bool), hop
    return levels > np.percentile(levels, 95) - FLOOR, hop


def clean(wave: np.ndarray, rate: int, lead: float = LEAD, tail: float = TAIL, longest: float = LONG_PAUSE,
          shortest: float = SHORT_PAUSE) -> np.ndarray:
    """The silences of an audio: `lead` seconds before the first word, and `tail` seconds after
    the last one. A pause longer than `longest` seconds becomes `shortest` seconds: a click in
    the pause does not stop the shortening, and it is never cut."""
    wave = np.ascontiguousarray(wave, dtype=np.float32)
    sound, hop = _voiced(wave, rate)
    click = max(1, round(0.05 * rate / hop))          # a sound shorter than 50 milliseconds is not a word
    speech = _without_clicks(sound, click)
    if not len(speech) or not speech.any():
        return wave
    first, last = int(np.flatnonzero(speech)[0]), int(np.flatnonzero(speech)[-1])
    keep, limit = max(1, round(shortest / 2 * rate / hop)), round(longest * rate / hop)
    stays, quiet, pause = np.ones(len(sound), dtype=bool), 0, 0      # the frames that stay in the clip
    stays[:max(0, first - round(lead * rate / hop))] = False          # the silence before the first word
    for index in range(first, last + 1):
        if speech[index]:
            if quiet >= limit and 2 * keep < quiet:
                # A long pause ends here. It keeps its first half and its last half: in the middle, only the silent frames go.
                middle = np.flatnonzero(~sound[pause + keep:index - keep])
                stays[pause + keep + middle] = False
            quiet = 0
        else:
            quiet, pause = quiet + 1, (pause if quiet else index)
    kept = np.ones(len(wave), dtype=bool)
    kept[:len(stays) * hop] = np.repeat(stays, hop)
    out = wave[kept]
    # The model leaves a little noise in the silences. The start of the clip is silent, because
    # `videogen sync` looks for the first sound of a clip at its start; the end goes to zero.
    voiced = _without_clicks(_voiced(out, rate)[0], click)
    if voiced.any():
        start = int(np.flatnonzero(voiced)[0]) * hop
        fade = min(start, round(0.02 * rate))
        out[:start - fade] = 0
        out[start - fade:start] *= np.linspace(0, 1, fade, dtype=np.float32)
        last = (int(np.flatnonzero(voiced)[-1]) + 1) * hop
        end = min(len(out), last + round(tail * rate))
        out[last:end] *= np.linspace(1, 0, end - last, dtype=np.float32)
        out = out[:end]
    return out


def pauses(wave: np.ndarray, rate: int, shortest: float = 0.15) -> list[float]:
    """The silences of at least `shortest` seconds between the words of an audio, in seconds. A
    click in a silence does not split it, and the silence at the start and at the end does not
    count. `videogen voice-compare` counts the pauses: a clone copies those of its sample."""
    sound, hop = _voiced(wave, rate)
    speech = _without_clicks(sound, max(1, round(0.05 * rate / hop)))   # a sound shorter than 50 milliseconds is not a word
    loud = np.flatnonzero(speech)
    if not len(loud):
        return []
    found, start = [], None
    for index, flag in enumerate(list(speech[loud[0]:loud[-1] + 1]) + [False]):
        if not flag and start is None:
            start = index
        elif flag and start is not None:
            if (index - start) * hop / rate >= shortest:
                found.append((index - start) * hop / rate)
            start = None
    return found


def set_level(wave: np.ndarray, level: float = LEVEL, peak: float = PEAK) -> np.ndarray:
    """An audio with the RMS at `level`, when its highest sample stays under `peak`."""
    wave = np.asarray(wave, dtype=np.float32)
    rms = float(np.sqrt(np.mean(wave.astype(np.float64) ** 2))) if len(wave) else 0.0
    highest = float(np.abs(wave).max()) if len(wave) else 0.0
    if rms <= 0 or highest <= 0:
        return wave
    return (wave * min(level / rms, peak / highest)).astype(np.float32)


def squeeze(wave: np.ndarray, rate: int, factor: float) -> np.ndarray:
    """The same audio, shorter in time: `factor` 1.1 gives a clip 10 per cent shorter, and the
    pitch does not change. `ffmpeg atempo` does it: its algorithm keeps the words clear, where the
    model made to speak faster does not."""
    try:
        done = subprocess.run(
            ["ffmpeg", "-v", "error", "-f", "f32le", "-ac", "1", "-ar", str(rate), "-i", "pipe:0",
             "-af", f"atempo={factor:.4f}", "-f", "f32le", "-ac", "1", "-ar", str(rate), "pipe:1"],
            input=np.ascontiguousarray(wave, dtype="<f4").tobytes(), capture_output=True, check=True,
        )
    except FileNotFoundError as error:
        raise RuntimeError("ffmpeg is not installed: it makes the clips shorter in time at a rate over 20 per cent.") from error
    except subprocess.CalledProcessError as error:
        reason = error.stderr.decode("utf-8", "replace").strip()[-300:]
        raise RuntimeError(f"ffmpeg could not make the clip shorter in time: {reason}") from error
    return np.frombuffer(done.stdout, dtype="<f4").copy()


def letters(word: str) -> str:
    """The letters of a word for the aligner: the small Latin letters, without the accents,
    and the apostrophe. A word in another alphabet gives an empty string."""
    text = "".join(character for character in unicodedata.normalize("NFD", word.lower()) if unicodedata.category(character) != "Mn")
    return "".join(character for character in text if "a" <= character <= "z" or character == "'")


# ------------------------------------------------------------------ the model and the aligner


class Speech:
    """The model of speech and the aligner, loaded one time."""

    def __init__(self, model: Path, aligner: Path, device: str | None = None):
        import torch
        import torchaudio

        self.torch, self.torchaudio = torch, torchaudio
        if device is None:
            if torch.cuda.is_available():
                device = "cuda:0"
            elif getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
        self.device = device
        self.on_gpu = device.startswith("cuda")
        self.align_device = device if self.on_gpu else "cpu"
        from omnivoice import OmniVoice

        self.model = OmniVoice.from_pretrained(str(model), device_map=device, dtype=torch.float16 if self.on_gpu else torch.float32)
        # The aligner looks for its weights in the folder of the cache of torch: tools/setup-omnivoice.sh
        # puts them in the folder of the tools.
        torch.hub.set_dir(str(aligner))
        self.bundle = torchaudio.pipelines.MMS_FA
        self.align_model = self.bundle.get_model().to(self.align_device)
        self.tokenizer, self.aligner = self.bundle.get_tokenizer(), self.bundle.get_aligner()
        self.prompts: dict[tuple[str, str], object] = {}
        import soxr

        self.soxr = soxr

    def prompt(self, path: str, text: str):
        """The voice cloned from a sample of a voice, made one time for each sample. The model
        prepares the sample: it removes the long silences, sets its level, and ends the transcript
        with a period."""
        key = (path, text)
        if key not in self.prompts:
            from omnivoice.utils.audio import load_audio

            rate = self.model.sampling_rate
            wave = load_audio(path, rate)          # (1, samples)
            seconds = wave.shape[-1] / rate
            if not SAMPLE_SECONDS[0] <= seconds <= SAMPLE_SECONDS[1]:
                shortest, longest = (f"{limit:.0f}" for limit in SAMPLE_SECONDS)
                raise ValueError(f"The sample of the voice lasts {seconds:.1f} seconds: use a sample of {shortest} to {longest} seconds.")
            transcript = text if text[-1:] in ".!?" else text + "."
            self.prompts[key] = self.model.create_voice_clone_prompt(
                ref_audio=(self.torch.from_numpy(wave), rate), ref_text=transcript,
            )
        return self.prompts[key]

    def synthesize(self, text: str, language: str | None, ref: str | None, ref_text: str | None, speed: float | None,
                   seed: int, stretch: float = 1.0) -> tuple[np.ndarray, list[list[float]]]:
        """The audio at 48000 Hz, and the start and the end of each word of `text`.
        Without `ref`, the model chooses a voice: each seed gives a different one. `stretch` above
        1 makes the clip shorter in time, before the silences are set."""
        self.torch.manual_seed(int(seed))
        options = {"speed": speed} if speed and abs(speed - 1.0) > 1e-6 else {}
        audio = self.model.generate(
            text=text, language=language, voice_clone_prompt=self.prompt(ref, ref_text or "") if ref else None, **options,
        )[0]
        rate = self.model.sampling_rate
        audio = np.asarray(audio, dtype=np.float32)
        if stretch and abs(stretch - 1.0) > 1e-3:
            audio = squeeze(audio, rate, float(stretch))
        audio = clean(audio, rate)
        if len(audio) < rate // 5 or not _voiced(audio, rate)[0].any():
            raise ValueError("The model gave no voice for this text.")
        audio = set_level(audio)
        return self.soxr.resample(audio, rate, RATE_OUT).astype(np.float32), self.times(audio, rate, text.split())

    def times(self, wave: np.ndarray, rate: int, words: list[str]) -> list[list[float]]:
        """The start and the end of each word of `words` in `wave`, in seconds.
        A word without Latin letters has no time: it takes the end of the word before."""
        readable = [(index, letters(word)) for index, word in enumerate(words) if letters(word)]
        spans: list[tuple[float, float] | None] = [None] * len(words)
        try:
            if readable:
                with self.torch.inference_mode():
                    audio = self.soxr.resample(wave, rate, self.bundle.sample_rate)
                    emission, _ = self.align_model(self.torch.from_numpy(np.ascontiguousarray(audio)).unsqueeze(0).to(self.align_device))
                    # The aligner gives the span of each letter; a word goes from its first letter to its last.
                    aligned = self.aligner(emission[0], self.tokenizer([word for _index, word in readable]))
                ratio = audio.shape[0] / emission.size(1)
                for (index, _word), spans_of_letters in zip(readable, aligned):
                    spans[index] = (spans_of_letters[0].start * ratio / self.bundle.sample_rate,
                                    spans_of_letters[-1].end * ratio / self.bundle.sample_rate)
        except Exception as error:      # the clip is good: the time of the words is spread over its length
            print(f"omnivoice_worker: the alignment of the words failed ({error}); their time is spread over the clip", file=sys.stderr)
            total = sum(max(1, len(word)) for word in words)
            cursor = 0.0
            spans = []
            for word in words:
                start = cursor
                cursor += len(wave) / rate * max(1, len(word)) / total
                spans.append((start, cursor))
        length = len(wave) / rate
        result, cursor = [], 0.0
        for span in spans:
            start = cursor if span is None else max(cursor, min(span[0], length))
            end = max(start, min(span[1], length)) if span is not None else start
            result.append([round(start, 3), round(end, 3)])
            cursor = end
        return result


# ------------------------------------------------------------------------------- the protocol


def send(protocol, answer: dict) -> None:
    protocol.write(json.dumps(answer).encode("ascii") + b"\n")
    protocol.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description="The worker of the OmniVoice engine of videogen.")
    parser.add_argument("--model", required=True, help="the folder of the model k2-fsa/OmniVoice")
    parser.add_argument("--aligner", required=True, help="the folder with checkpoints/model.pt, the model of the aligner")
    parser.add_argument("--device", help="cuda:0, mps or cpu (default: the first that operates)")
    parser.add_argument("--check", action="store_true", help="load the model and the aligner, say whether they operate, and stop")
    arguments = parser.parse_args()
    # Without -I, the first entry is the folder of this file. It has omnivoice.py, the engine of
    # videogen: it would hide the package of the model, which has the same name.
    here = str(Path(__file__).resolve().parent)
    sys.path[:] = [entry for entry in sys.path if entry and Path(entry).resolve() != Path(here)]
    warnings.filterwarnings("ignore")                 # the dependencies of the model are noisy
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    # The standard output carries the answers: everything that the libraries print goes to the standard error.
    protocol = os.fdopen(os.dup(1), "wb")
    os.dup2(2, 1)
    sys.stdout = sys.stderr
    try:
        speech = Speech(Path(arguments.model), Path(arguments.aligner), arguments.device)
    except Exception as error:
        traceback.print_exc()
        if arguments.check:
            print(f"OmniVoice does not load: {error}")
            return 1
        send(protocol, {"ok": False, "error": f"the model does not load: {error}"})
        return 1
    hello = {"ok": True, "device": speech.device}
    if arguments.check:
        print(f"OmniVoice is ready on {speech.device}: the model and the aligner load.")
        return 0
    send(protocol, hello)
    for line in sys.stdin.buffer:
        try:
            request = json.loads(line)
        except ValueError:
            send(protocol, {"ok": False, "error": "the request is not a line of JSON"})
            continue
        if request.get("op") == "ping":
            send(protocol, hello)
            continue
        started = time.time()
        try:
            wave, spans = speech.synthesize(
                request["text"], request.get("language"), request.get("ref"), request.get("ref_text"), request.get("speed"),
                request.get("seed", 0), request.get("stretch", 1.0),
            )
        except Exception as error:
            traceback.print_exc()
            send(protocol, {"ok": False, "error": str(error) or type(error).__name__})
            continue
        print(f"omnivoice_worker: {len(wave) / RATE_OUT:.1f} s of audio in {time.time() - started:.1f} s", file=sys.stderr)
        send(protocol, {
            "ok": True, "rate": RATE_OUT, "seconds": round(time.time() - started, 2),
            "samples": base64.b64encode(wave.astype("<f4").tobytes()).decode("ascii"), "spans": spans,
        })
    return 0


if __name__ == "__main__":
    sys.exit(main())
