"""The voices of the engine omnivoice. `videogen voice-prepare` makes a voice from the recordings
of a person. `videogen voice-compare` makes the file to listen, the measures of the pace, and the
verification of the recognizer. See docs/5-tts-engines.md."""

from __future__ import annotations

import re
import subprocess
import time
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from videogen import paths, speech
from videogen.langs import LANGS, Language
from videogen.tts import SAMPLE_RATE, decode_audio
from videogen.tts import omnivoice_worker as worker
from videogen.tts.omnivoice import AUDIO, RATE, find_sample, folders_of, sample_names

SAMPLE_LEAD = 0.15         # the seconds of silence before the first word of a sample
SAMPLE_TAIL = 0.20         # the seconds of silence after the last word
SAMPLE_LONGEST = 0.26      # a pause of a recording longer than this...
SAMPLE_SHORTEST = 0.20     # ...becomes this: the model copies the pauses of its sample
BETWEEN_RECORDINGS = 0.4   # the seconds of silence between two recordings of one sample
SOUND = 1e-4               # the peak under which an audio has no sound
NAME = re.compile(r"[^\s/\\]+")   # the name of a voice: no spaces, no path
SENTENCE_END = re.compile(r"[.!?]+")
SPEED_FILE = "# The speed of this voice: `videogen new` writes it as `rate` in the video.toml of a new video.\nrate = \"{}\"\n"


def folder_of(root: Path | None) -> Path:
    """The folder `voices` where a command writes: that of the project `root`, or that of the template."""
    return (root if root is not None else paths.template_root()) / "voices"


def _silence(seconds: float) -> np.ndarray:
    return np.zeros(int(seconds * SAMPLE_RATE), np.float32)


def _longest(sound: np.ndarray) -> float:
    return max(worker.pauses(sound, SAMPLE_RATE), default=0.0)


def prepare(root: Path | None, name: str, recordings: list[Path], text: str, rate: str = "", cut: bool = True,
            force: bool = False, log=print) -> Path:
    """A voice from one or more recordings, in the order of `text`: the words that the voice says.

    With `cut`, the silences of each recording change: a pause longer than `SAMPLE_LONGEST` seconds
    becomes `SAMPLE_SHORTEST` seconds, with `SAMPLE_LEAD` seconds of silence before the first word
    and `SAMPLE_TAIL` after the last one (also when the recording starts or ends with a word). A
    recording with a pause at each punctuation mark gives a clone that is slow and stops at each
    comma: the model copies the pauses of its sample.

    The voice is `voices/<name>.wav` (mono, 16-bit PCM, at SAMPLE_RATE) with `voices/<name>.txt`,
    and `voices/<name>.toml` when `rate` is not empty. The folder is that of the project `root`,
    or that of the template. The recordings do not change. Returns the path of the sample.
    """
    if not NAME.fullmatch(name) or name.lower().endswith(AUDIO):
        raise ValueError(f"'{name}' is not a name of a voice: no spaces, no path, and no audio extension "
                         "(videogen reads that as the path of a file).")
    words = " ".join(text.split())
    if not words:
        raise ValueError("The text of the sample is empty: --text has the words that the voice says.")
    speed = rate.strip()
    if speed and not RATE.fullmatch(speed):
        raise ValueError(f"The rate '{rate}' is not valid. Use a value such as '+5%' or '-10%'.")
    for recording in recordings:
        if not recording.is_file():
            raise FileNotFoundError(f"The recording '{recording}' does not exist.")
    folder = folder_of(root)
    old = find_sample(name, [folder])
    if old is not None and not force:
        raise RuntimeError(f"The voice '{name}' is in {old.path.parent} ({old.path.name}). Use --force to replace it.")
    margin = _silence(max(SAMPLE_LEAD, SAMPLE_TAIL))
    parts = []
    for recording in recordings:
        audio = decode_audio(recording)
        if float(np.abs(audio).max()) < SOUND:
            raise ValueError(f"The recording '{recording}' has no sound.")
        before = len(audio) / SAMPLE_RATE
        longest = _longest(audio)
        if cut:
            audio = worker.clean(np.concatenate([margin, audio, margin]), SAMPLE_RATE, lead=SAMPLE_LEAD, tail=SAMPLE_TAIL,
                                 longest=SAMPLE_LONGEST, shortest=SAMPLE_SHORTEST)
            log(f"{recording.name}: {before:.1f} s -> {len(audio) / SAMPLE_RATE:.1f} s, "
                f"the longest pause {longest:.1f} s -> {_longest(audio):.1f} s")
        else:
            log(f"{recording.name}: {before:.1f} s (the pauses stay), the longest pause {longest:.1f} s")
        parts.append(audio)
    sample = np.concatenate([piece for part in parts for piece in (part, _silence(BETWEEN_RECORDINGS))][:-1])
    seconds = len(sample) / SAMPLE_RATE
    shortest, longest = (f"{limit:.0f}" for limit in worker.SAMPLE_SECONDS)
    if not worker.SAMPLE_SECONDS[0] <= seconds <= worker.SAMPLE_SECONDS[1]:
        raise ValueError(f"The sample lasts {seconds:.1f} seconds: use a sample of {shortest} to {longest} seconds. "
                         "Give one recording only, or read shorter sentences.")
    path = folder / f"{name}.wav"
    speech.write_wav(path, sample)
    transcript = path.with_suffix(".txt")
    transcript.write_text(words + "\n", encoding="utf-8")
    written = [path, transcript]
    if speed:
        path.with_suffix(".toml").write_text(SPEED_FILE.format(speed), encoding="utf-8")
        written.append(path.with_suffix(".toml"))
    sentences = max(1, len(SENTENCE_END.findall(words)))
    count = len(words.split())
    log(f"Voice {name}: {seconds:.1f} s, {count / seconds:.2f} words per second, "
        f"{len(worker.pauses(sample, SAMPLE_RATE)) / sentences:.1f} pauses per sentence.")
    log("Wrote " + ", ".join(str(file) for file in written))
    names = sample_names(folders_of(root))
    log(f"Voices: {', '.join(names)}. Without `voice`, videogen uses the first one: {names[0]}.")
    return path


# ------------------------------------------------------------------------ the comparison

PAUSE = 0.15               # a silence of this many seconds or more is a pause, in the measures
BEFORE_SENTENCE = 1.5      # the seconds of silence before each sentence in the file to listen
AFTER_CLIP = 0.9           # the seconds of silence after a clip in the file to listen
AFTER_LABEL = 0.25         # the seconds of silence after a label
THRESHOLD = 0.9            # a clip with a lower similarity is different from its sentence


@dataclass
class Take:
    """A clip of the comparison: a voice reads a sentence at one speed."""
    voice: str             # the name shown: that of the voice, or the name of the file of a sample
    rate: str
    sentence: str
    samples: np.ndarray


def rates_of(text: str) -> list[str]:
    """The speeds of the option `--rates` of `videogen voice-compare`: "+0%,+20%" gives two speeds."""
    speeds = [speed.strip() for speed in text.split(",") if speed.strip()]
    for speed in speeds:
        if not RATE.fullmatch(speed):
            raise ValueError(f"The rate '{speed}' is not valid. Use values such as '+0%,+20%,+32%'.")
    return speeds


def sentences_of(text: Path | None, language: Language) -> list[str]:
    """The sentences that the voices read in a comparison: those of the file `text` (one sentence
    per line; empty lines and lines that start with # do not count), or those of the template for
    the language (`videogen/templates/voice-test/<language>.txt`)."""
    if text is not None and not text.is_file():
        raise FileNotFoundError(f"The file of the test sentences '{text}' does not exist.")
    if text is None:
        text = paths.template_root() / "videogen" / "templates" / "voice-test" / f"{language.code}.txt"
        if not text.is_file():
            raise FileNotFoundError(f"No test sentences for the language '{language.code}' in {text}: give them with --text "
                                    "(a file with one sentence per line).")
    sentences = [line.strip() for line in text.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
    if not sentences:
        raise ValueError(f"The file of the test sentences has no sentence: {text}. Write one sentence per line.")
    return sentences


def _heard(recognizer, samples: np.ndarray, language: str) -> str:
    """What the recognizer hears in a clip. Each clip goes to the recognizer alone: in one stream
    for all the clips, the recognizer can lose the first word of a clip."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "f32le", "-ac", "1", "-ar", str(SAMPLE_RATE), "-i", "pipe:0",
         "-f", "f32le", "-ac", "1", "-ar", "16000", "pipe:1"],
        input=np.ascontiguousarray(samples, dtype="<f4").tobytes(), check=True, capture_output=True,
    ).stdout
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")      # the dependencies of the recognizer are noisy
        segments, _info = recognizer.transcribe(np.frombuffer(raw, dtype=np.float32), language=language, beam_size=5)
    return " ".join(segment.text.strip() for segment in segments)


def compare(engine, names: list[str], sentences: list[str], rates: list[str] | None = None, root: Path | None = None,
            language: Language = LANGS["en"], out: Path | None = None, labels=None, recognizer=None, similarity=None,
            threshold: float = THRESHOLD, log=print) -> int:
    """The voices `names` read the test `sentences`, at the speeds `rates`, or at their own speed:
    one file to listen, the measures of the pace, and the verification of the recognizer.

    The file to listen has, for each sentence (`BEFORE_SENTENCE` seconds of silence before it), for
    each speed and each voice: the label, the clip, and `AFTER_CLIP` seconds of silence. The clips
    have the form of the clips of a video. The file is `out`, or in the folder `confronto` of the
    first folder of voices. `labels` is an engine that reads the label: the name of the voice and
    its speed.

    The measures of a voice at a speed: its words per second, its pauses per sentence, and its
    longest pause. A clone reads at the pace of its sample: these measures say whether a voice is
    slow, or stops many times in a sentence.

    `recognizer` is the offline recognizer (an object with a method `transcribe`, as faster-whisper),
    or a function that gives it: the comparison calls it when the voices are verified. None to
    not verify the clips. `similarity(heard, language, *texts)` says how much a
    transcription agrees with a text: it is the one of `videogen transcript`.

    Returns 1 when the recognizer finds clips that are different from their sentence, else 0.
    """
    folders = folders_of(root)
    found = []
    for name in names:
        sample = find_sample(name, folders, root)
        if sample is None:
            known = ", ".join(sample_names(folders)) or "none"
            raise RuntimeError(f"OmniVoice has no voice '{name}' (the voices of the folders voices/ are: {known}).")
        found.append((name, sample.name))
    recognizer = recognizer() if callable(recognizer) else recognizer
    engine.configure(root, language)
    if rates:
        plan = [(name, shown, rate) for rate in rates for name, shown in found]
    else:
        plan = [(name, shown, engine.default_rate(name, root) or "+0%") for name, shown in found]
    log(f"{len(sentences) * len(plan)} clips with omnivoice: {len(sentences)} sentences, {len(plan)} voices and speeds, in {language.name}.")
    rows: list[list[Take]] = []
    for sentence in sentences:
        said = speech.spoken(sentence, language.spoken_rules)
        rows.append([Take(shown, rate, sentence, speech.trim_tail(engine.synthesize(said, name, rate).samples)) for name, shown, rate in plan])
    spoken: dict[tuple[str, str], np.ndarray] = {}
    if labels is not None:
        voice = language.voices.get("edge-tts", ())[:1]
        if not voice:
            raise RuntimeError(f"edge-tts has no voice for the language '{language.code}': start the command without --labels.")
        try:
            for _name, shown, rate in plan:
                if (shown, rate) not in spoken:
                    words = f"{shown.replace('-', ' ').replace('_', ' ')}, {rate}."
                    spoken[shown, rate] = speech.trim_tail(labels.synthesize(words, voice[0], "+0%").samples)
        except Exception as error:      # the labels are a help to listen: without a connection, the file has none
            log(f"NOTE: edge-tts gave no label ({str(error)[:160]}): the file has no labels.")
            spoken = {}
    if out is None:
        # The second is in the name: two comparisons of the same voices in a minute give two files.
        out = folders[0] / "confronto" / f"{time.strftime('%Y%m%d-%H%M%S')}-{'-'.join(dict.fromkeys(shown for _n, shown, _r in plan))}.wav"
    parts = []
    for row in rows:
        parts.append(_silence(BEFORE_SENTENCE))
        for take in row:
            if spoken:
                parts += [spoken[take.voice, take.rate], _silence(AFTER_LABEL)]
            parts += [take.samples, _silence(AFTER_CLIP)]
    sound = np.concatenate(parts)
    speech.write_wav(out, sound)
    total = len(sound) / SAMPLE_RATE
    log(f"File to listen: {out} ({int(total // 60)} min {int(total % 60):02d} s)")
    log(f"{'voice':<18} {'speed':<7} {'words/s':<8} {'pauses/sentence':<16} longest pause")
    for _name, shown, rate in plan:
        mine = [take for row in rows for take in row if (take.voice, take.rate) == (shown, rate)]
        words = sum(len(take.sentence.split()) for take in mine)
        seconds = sum(len(take.samples) for take in mine) / SAMPLE_RATE
        silences = [pause for take in mine for pause in worker.pauses(take.samples, SAMPLE_RATE, PAUSE)]
        log(f"{shown:<18} {rate:<7} {words / seconds:<8.2f} {len(silences) / len(mine):<16.1f} {max(silences, default=0.0):.1f} s")
    log("For each sentence, the clips come in this order: " + ", ".join(f"{shown} ({rate})" for _n, shown, rate in plan) + ".")
    for index, sentence in enumerate(sentences, 1):
        log(f"{index}. {sentence}")
    if recognizer is None:
        return 0
    different = []
    for index, row in enumerate(rows, 1):
        for take in row:
            said = speech.spoken(take.sentence, language.spoken_rules)
            heard = _heard(recognizer, take.samples, language.code)
            ratio = similarity(heard, language.code, said, take.sentence)
            if ratio < threshold:
                different.append((ratio, index, take, heard))
    count = sum(len(row) for row in rows)
    log(f"The recognizer: {count - len(different)} of {count} clips say their sentence.")
    for ratio, index, take, heard in different:
        log(f"  [{ratio:.2f}] {take.voice} ({take.rate}), sentence {index}: {heard}")
        log(f"         script: {take.sentence}")
    return 1 if different else 0
