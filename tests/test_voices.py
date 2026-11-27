"""The voices of the engine omnivoice: `videogen voice-prepare` makes a voice from recordings, and
`videogen voice-compare` makes the file to listen, the measures and the verification of the
recognizer. The engine of the tests is a false one that returns known audio: these tests need
neither the model nor a GPU."""

from __future__ import annotations

import re
import sys
import wave
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from videogen import cli, paths, speech, voices
from videogen.langs import LANGS
from videogen.tts import ENGINES, SAMPLE_RATE, Clip, Status
from videogen.tts import omnivoice_worker as worker

RANDOM = np.random.default_rng(7)


def word(seconds: float = 0.25, loud: float = 0.5) -> np.ndarray:
    """A voice-like sound: a tone in a window of Hann."""
    time = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    return (loud * np.sin(2 * np.pi * 180 * time) * np.hanning(len(time))).astype(np.float32)


def quiet(seconds: float) -> np.ndarray:
    """The silence, with a little noise, as a recorder leaves it."""
    return RANDOM.normal(0, 0.002, int(seconds * SAMPLE_RATE)).astype(np.float32)


def click() -> np.ndarray:
    sound = np.zeros(int(0.04 * SAMPLE_RATE), np.float32)
    sound[240:1200] = 0.3 * np.hanning(960)
    return sound


def wav_file(path: Path, mono: np.ndarray, channels: int = 1, rate: int = SAMPLE_RATE, second: float = 0.5) -> Path:
    """A file WAV, 16-bit PCM. At another rate, the sound lasts the same seconds (a linear
    resampling). With two channels, the second is at the level `second` of the first."""
    if rate != SAMPLE_RATE:
        positions = np.arange(int(len(mono) * rate / SAMPLE_RATE)) * SAMPLE_RATE / rate
        mono = np.interp(positions, np.arange(len(mono)), mono).astype(np.float32)
    sound = np.column_stack([mono, mono * second]) if channels == 2 else np.column_stack([mono])
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes((np.clip(sound, -1, 1) * 32767).astype("<i2").tobytes())
    return path


def read_file(path: Path) -> tuple[np.ndarray, int, int]:
    """The samples (float32, of one channel), the rate and the number of channels of a file WAV."""
    with wave.open(str(path)) as handle:
        sound = np.frombuffer(handle.readframes(handle.getnframes()), dtype="<i2").astype(np.float32) / 32767
        return sound.reshape(-1, handle.getnchannels()).mean(axis=1), handle.getframerate(), handle.getnchannels()


def test_the_pauses_of_an_audio():
    """The silences between the words: a short one does not count, a click does not split one, and
    the silence at the start and at the end of the audio is not a pause."""
    one, two, three = word(), word(), word()
    sound = np.concatenate([quiet(0.5), one, quiet(0.4), two, quiet(0.1), three, quiet(0.8)])
    assert worker.pauses(sound, SAMPLE_RATE) == pytest.approx([0.4], abs=0.1)
    assert worker.pauses(sound, SAMPLE_RATE, shortest=0.05) == pytest.approx([0.4, 0.1], abs=0.1)
    with_click = np.concatenate([quiet(0.5), one, quiet(0.2), click(), quiet(0.2), two])
    assert worker.pauses(with_click, SAMPLE_RATE) == pytest.approx([0.4], abs=0.1)
    assert worker.pauses(quiet(2.0), SAMPLE_RATE) == [] and worker.pauses(word(), SAMPLE_RATE) == []


def template(monkeypatch, tmp_path) -> Path:
    """A template in a temporary folder: its folder `voices` is where `videogen voice-prepare`
    writes. Returns that folder."""
    monkeypatch.setattr(paths, "template_root", lambda: tmp_path / "template")
    return tmp_path / "template" / "voices"


SPOKEN = "Prima parola, seconda parola, terza parola."
# A person reads three words: a long pause after the first one, a short one after the second. 4.75 seconds.
READ_SLOWLY = [quiet(0.8), word(0.6), quiet(1.2), word(0.6), quiet(0.05), word(0.6), quiet(0.9)]


def test_prepare_cuts_the_pauses_of_a_recording(tmp_path, monkeypatch):
    """A pause longer than 0.26 seconds becomes 0.2 seconds; a shorter one stays. The sample starts
    with 0.15 seconds of silence, and ends with 0.2 seconds."""
    template(monkeypatch, tmp_path)
    recording = wav_file(tmp_path / "a.wav", np.concatenate(READ_SLOWLY))
    sample, rate, channels = read_file(voices.prepare(None, "mia", [recording], SPOKEN))
    assert (rate, channels) == (48000, 1)
    assert worker.pauses(sample, rate, shortest=0.05) == pytest.approx([0.2, 0.12], abs=0.04)
    loud = np.flatnonzero(np.abs(sample) > 0.02)
    assert loud[0] / rate == pytest.approx(0.15, abs=0.04)                      # the silence before the first word
    assert (len(sample) - loud[-1]) / rate == pytest.approx(0.2, abs=0.04)      # the silence after the last one
    assert len(sample) / rate < 4.75 - 2                                        # the long pause is gone
    assert np.abs(sample[: int(0.12 * rate)]).max() == 0.0 and sample[-1] == 0.0


def test_prepare_can_keep_the_pauses(tmp_path, monkeypatch):
    """Without the cut, the recording stays as it is: the model copies its pauses."""
    template(monkeypatch, tmp_path)
    recording = wav_file(tmp_path / "a.wav", np.concatenate(READ_SLOWLY))
    sample, rate, _channels = read_file(voices.prepare(None, "mia", [recording], SPOKEN, cut=False))
    assert len(sample) / rate == pytest.approx(4.75, abs=0.02)
    assert worker.pauses(sample, rate, shortest=0.05) == pytest.approx([1.27, 0.12], abs=0.04)


def test_prepare_joins_the_recordings_with_a_short_silence(tmp_path, monkeypatch):
    """Two recordings make one sample: 0.4 seconds of silence between them, and the words of the
    two in one transcript, on one line."""
    folder = template(monkeypatch, tmp_path)
    first = wav_file(tmp_path / "uno.wav", np.concatenate([word(0.6), quiet(0.2), word(0.6), quiet(0.2), word(0.6)]))
    second = wav_file(tmp_path / "due.wav", np.concatenate([word(0.6), quiet(0.2), word(0.6), quiet(0.2), word(0.6)]))
    alone = read_file(voices.prepare(None, "una", [first], "Prima frase, seconda frase, terza frase."))[0]
    sample = voices.prepare(None, "mia", [first, second], "  Prima frase.\nSeconda   frase.  ")
    assert sample == folder / "mia.wav"
    sound, rate, _channels = read_file(sample)
    assert len(sound) == pytest.approx(2 * len(alone) + 0.4 * rate, abs=2 * 480)      # the two samples, and 0.4 seconds
    assert worker.pauses(sound, rate, shortest=0.05) == pytest.approx([0.2, 0.2, 0.2 + 0.4 + 0.15, 0.2, 0.2], abs=0.04)   # the tail, the silence, the lead
    assert (folder / "mia.txt").read_text(encoding="utf-8") == "Prima frase. Seconda frase.\n"
    assert not (folder / "mia.toml").exists()                                            # a voice without a speed has no third file


def test_prepare_reads_any_recording_format(tmp_path, monkeypatch):
    """A recording of a telephone can be stereo at another rate. It gives the same sample as its
    copy in mono at 48000 Hz, at the mean of its two channels. (The downmix of ffmpeg to mono is
    not the mean: a loud stereo recording would clip.)"""
    template(monkeypatch, tmp_path)
    sound = np.concatenate([quiet(0.3), word(0.6), quiet(0.2), word(0.6), quiet(0.2), word(0.6), quiet(0.3)])
    mono = wav_file(tmp_path / "mono.wav", sound)
    reference = read_file(voices.prepare(None, "mono", [mono], "Una parola, due parole, tre parole."))[0]
    telephone = wav_file(tmp_path / "telefono.wav", sound, channels=2, rate=44100)
    sample, rate, channels = read_file(voices.prepare(None, "mia", [telephone], "Una parola, due parole, tre parole."))
    assert (rate, channels) == (48000, 1)
    assert len(sample) == pytest.approx(len(reference), abs=2 * 480)                  # the same seconds
    common = min(len(sample), len(reference))
    assert np.allclose(sample[:common], 0.75 * reference[:common], atol=0.01)          # the mean of (the sound, half the sound)


def test_prepare_writes_the_speed_of_the_voice(tmp_path, monkeypatch):
    """With a speed, the third file of the voice is there, and the engine finds it."""
    template(monkeypatch, tmp_path)
    recording = wav_file(tmp_path / "a.wav", np.concatenate(READ_SLOWLY))
    voices.prepare(None, "mia", [recording], SPOKEN, rate="+20%")
    assert ENGINES["omnivoice"].default_rate("mia") == "+20%"
    with pytest.raises(ValueError, match="The rate 'fast' is not valid"):
        voices.prepare(None, "altra", [recording], SPOKEN, rate="fast")
    assert not (tmp_path / "template" / "voices" / "altra.wav").exists()


def test_prepare_refuses_a_sample_outside_its_limits(tmp_path, monkeypatch):
    """A sample is from 2 to 20 seconds, as the model accepts it. The voice is not written."""
    folder = template(monkeypatch, tmp_path)
    short = wav_file(tmp_path / "short.wav", np.concatenate([quiet(0.3), word(0.4), quiet(0.3)]))
    with pytest.raises(ValueError, match=r"sample lasts 0\.\d seconds: use a sample of 2 to 20 seconds"):
        voices.prepare(None, "mia", [short], "Una parola.")
    long = wav_file(tmp_path / "long.wav", np.concatenate([word(0.5), quiet(0.2)] * 40 + [word(0.5)]))
    with pytest.raises(ValueError, match=r"sample lasts \d+\.\d seconds: use a sample of 2 to 20 seconds"):
        voices.prepare(None, "mia", [long], "Tante parole.")
    assert not list(folder.glob("mia.*"))


def test_prepare_does_not_replace_a_voice(tmp_path, monkeypatch):
    """A voice that has that name stays, unless the command says to replace it."""
    folder = template(monkeypatch, tmp_path)
    folder.mkdir(parents=True)
    (folder / "mia.txt").write_text("Le parole del campione di prima.\n", encoding="utf-8")
    (folder / "mia.wav").write_bytes(b"RIFF" + bytes(100))
    recording = wav_file(tmp_path / "a.wav", np.concatenate(READ_SLOWLY))
    with pytest.raises(RuntimeError, match=r"The voice 'mia' is in .*--force"):
        voices.prepare(None, "mia", [recording], "Altre parole.")
    assert (folder / "mia.txt").read_text(encoding="utf-8") == "Le parole del campione di prima.\n"
    assert (folder / "mia.wav").read_bytes() == b"RIFF" + bytes(100)
    voices.prepare(None, "mia", [recording], "Altre parole.", force=True)
    assert (folder / "mia.txt").read_text(encoding="utf-8") == "Altre parole.\n"
    assert (folder / "mia.wav").read_bytes() != b"RIFF" + bytes(100)


def test_prepare_refuses_what_it_cannot_use(tmp_path, monkeypatch):
    """The errors say what to change. A refused voice writes nothing."""
    folder = template(monkeypatch, tmp_path)
    recording = wav_file(tmp_path / "a.wav", np.concatenate(READ_SLOWLY))
    for name in ("la mia voce", "voce.wav", "una/voce"):
        with pytest.raises(ValueError, match="name of a voice"):
            voices.prepare(None, name, [recording], SPOKEN)
    with pytest.raises(ValueError, match="text"):
        voices.prepare(None, "mia", [recording], "   ")
    with pytest.raises(FileNotFoundError, match="missing.wav"):
        voices.prepare(None, "mia", [tmp_path / "missing.wav"], SPOKEN)
    (tmp_path / "false.wav").write_text("this is not audio", encoding="utf-8")
    with pytest.raises(RuntimeError, match="ffmpeg does not read"):
        voices.prepare(None, "mia", [tmp_path / "false.wav"], SPOKEN)
    silent = wav_file(tmp_path / "silent.wav", np.zeros(int(3 * SAMPLE_RATE), np.float32))
    with pytest.raises(ValueError, match="no sound"):
        voices.prepare(None, "mia", [silent], SPOKEN)
    assert not folder.exists()


def test_prepare_reports_the_pace_of_the_sample(tmp_path, monkeypatch, capsys):
    """The command says how fast the person reads, and which voice videogen uses when a video has
    no `voice`: a new voice can become the first one."""
    folder = template(monkeypatch, tmp_path)
    folder.mkdir(parents=True)
    (folder / "anna.txt").write_text("Una voce di prima.\n", encoding="utf-8")
    (folder / "anna.wav").write_bytes(b"RIFF" + bytes(100))
    recording = wav_file(tmp_path / "a.wav", np.concatenate(READ_SLOWLY))
    voices.prepare(None, "mia", [recording], SPOKEN)
    out = capsys.readouterr().out
    seconds, pace = (float(value) for value in re.search(r"Voice mia: ([\d.]+) s, ([\d.]+) words per second", out).groups())
    assert seconds < 4.75 - 2 and pace == pytest.approx(6 / seconds, abs=0.1)       # 6 words in the seconds of the sample
    assert "1.0 pauses per sentence" in out
    assert "the longest pause 1.3 s -> 0.2 s" in out
    assert "videogen uses the first one: anna." in out                      # anna is still the first voice
    voices.prepare(None, "alba", [recording], SPOKEN)
    assert "videogen uses the first one: alba." in capsys.readouterr().out


# ------------------------------------------------------------------------- videogen voice-compare

SENTENCES = ["Una due tre quattro.", "Cinque e sei."]
SPEEDS = ["+0%", "+20%"]


def tone(seconds: float, frequency: float, loud: float = 0.3) -> np.ndarray:
    time = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    return (loud * np.sin(2 * np.pi * frequency * time)).astype(np.float32)


def frequency(sound: np.ndarray, start: float, seconds: float = 0.9) -> float:
    """The frequency of the tone of `sound` from `start` seconds, for `seconds`."""
    first = int(start * SAMPLE_RATE)
    window = sound[first:first + int(seconds * SAMPLE_RATE)].astype(np.float64) * np.hanning(int(seconds * SAMPLE_RATE))
    spectrum = np.abs(np.fft.rfft(window, n=1 << 18))
    return float(np.fft.rfftfreq(1 << 18, 1 / SAMPLE_RATE)[np.argmax(spectrum)])


def voice_in(folder: Path, name: str) -> None:
    """A voice in a folder: a sample (a file that is not read) and its transcript."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.txt").write_text("Le parole di questo campione.\n", encoding="utf-8")
    (folder / f"{name}.wav").write_bytes(b"RIFF" + bytes(100))


def project_of(monkeypatch, tmp_path, *names) -> Path:
    """A video project with voices, and a template without voices. Returns the folder of the project."""
    monkeypatch.setattr(paths, "template_root", lambda: tmp_path / "template")
    for name in names:
        voice_in(tmp_path / "project" / "voices", name)
    return tmp_path / "project"


def text_file(tmp_path) -> Path:
    """The test sentences in a file, with a comment and an empty line."""
    path = tmp_path / "frasi.txt"
    path.write_text("# a comment\n\n" + "\n".join(SENTENCES) + "\n", encoding="utf-8")
    return path


def no_recognizer(monkeypatch) -> None:
    """The recognizer of the command line fails the test when it starts."""
    def start(model, threads):
        raise AssertionError("the recognizer started before the voices were verified")
    monkeypatch.setattr(cli, "_recognizer", start)


def false_engine(monkeypatch, clip_of) -> list[tuple[str, str, str]]:
    """The engine omnivoice of the command line without its model: `synthesize` gives
    `clip_of(text, voice, speed)`. Returns the calls, in their order."""
    calls = []

    def synthesize(text, voice, rate):
        calls.append((text, voice, rate))
        return Clip(clip_of(text, voice, rate))

    monkeypatch.setattr(ENGINES["omnivoice"], "synthesize", synthesize)
    monkeypatch.setattr(ENGINES["omnivoice"], "status", lambda: Status(True))
    return calls


def words_clip(text: str, _voice: str, _rate: str) -> np.ndarray:
    """A clip of the words of `text`: a tone of 0.3 seconds for each word, and a pause of 0.4 seconds between
    two words. A tone that starts and ends abruptly: the pause measures what it is."""
    return np.concatenate(sum(([tone(0.3, 180), quiet(0.4)] for _ in text.split()[:-1]), []) + [tone(0.3, 180)])


def false_recognizer(monkeypatch, *answers: str) -> None:
    """The recognizer of the command line says `answers`, in the order of the clips."""
    heard = iter(answers)
    recognizer = SimpleNamespace(transcribe=lambda audio, language, beam_size: ([SimpleNamespace(text=next(heard))], None))
    monkeypatch.setattr(cli, "_recognizer", lambda model, threads: recognizer)


def compare(monkeypatch, *arguments) -> int:
    """`videogen voice-compare <arguments>`: the exit code."""
    monkeypatch.setattr(sys, "argv", ["videogen", "voice-compare", *arguments])
    return cli.main()


def test_compare_puts_the_clips_in_one_file_sentence_by_sentence(tmp_path, monkeypatch):
    """For each sentence (1.5 seconds of silence before it), each speed, then each voice: the
    clip, and 0.9 seconds of silence. The sentences come from a file: a comment and an empty
    line do not count. The engine receives the folder of the project and the language. A clip
    keeps 0.14 seconds of the silence after its last sound, as a clip of a video."""
    project = project_of(monkeypatch, tmp_path, "anna", "elena")
    calls = false_engine(monkeypatch, lambda text, voice, rate: np.concatenate([tone(1.0, 200 + 40 * ("anna", "elena").index(voice)
                                                                                + 2 * SENTENCES.index(text)), np.zeros(SAMPLE_RATE, np.float32)]))
    out = tmp_path / "ascolto.wav"
    code = compare(monkeypatch, "anna", "elena", "--language", "it", "--text", str(text_file(tmp_path)), "--root", str(project),
                   "--out", str(out), "--no-check")
    assert code == 0 and ENGINES["omnivoice"].language is LANGS["it"] and ENGINES["omnivoice"].project == project
    sound, rate, channels = read_file(out)
    assert (rate, channels) == (48000, 1)
    assert len(sound) / rate == pytest.approx(2 * (1.5 + 2 * (1.0 + 0.14 + 0.9)), abs=0.02)
    for start, wanted in ((1.5, 200), (1.5 + 2.04, 240), (1.5 + 2 * 2.04 + 1.5, 202), (1.5 + 3 * 2.04 + 1.5, 242)):
        assert frequency(sound, start) == pytest.approx(wanted, abs=1)
    assert [(voice, rate) for _text, voice, rate in calls] == [("anna", "+0%"), ("elena", "+0%")] * 2


def test_compare_reads_at_the_speeds_given_or_at_that_of_the_voice(tmp_path, monkeypatch):
    """`--rates` gives the speeds of every voice. Without it, a voice reads at its own speed
    (`voices/<name>.toml`), or at +0%."""
    project = project_of(monkeypatch, tmp_path, "anna", "elena")
    (project / "voices" / "elena.toml").write_text('rate = "+20%"\n', encoding="utf-8")
    false_engine(monkeypatch, lambda text, voice, rate: tone(1.0, 200 + 8 * SPEEDS.index(rate)))
    out = tmp_path / "ascolto.wav"
    common = ("--language", "it", "--text", str(text_file(tmp_path)), "--root", str(project), "--out", str(out), "--no-check")

    def run(*voices, speeds=()):
        return compare(monkeypatch, *voices, *(("--rates", ",".join(speeds)) if speeds else ()), *common)

    assert run("anna", "elena") == 0
    assert frequency(read_file(out)[0], 1.5) == pytest.approx(200, abs=1) and frequency(read_file(out)[0], 3.4) == pytest.approx(208, abs=1)
    assert run("anna", speeds=SPEEDS) == 0
    sound = read_file(out)[0]
    assert len(sound) / SAMPLE_RATE == pytest.approx(2 * (1.5 + 2 * 1.9), abs=0.01)
    assert [frequency(sound, start) for start in (1.5, 3.4, 1.5 + 2 * 1.9 + 1.5, 3.4 + 2 * 1.9 + 1.5)] == pytest.approx([200, 208, 200, 208], abs=1)


def test_compare_measures_the_pace(tmp_path, monkeypatch, capsys):
    """For each voice and each speed, the command prints the words per second, the pauses per
    sentence and the longest pause, from its clips. A clip of 4 words lasts 2.4 seconds and has
    3 pauses; one of 3 words lasts 1.7 seconds and has 2."""
    project = project_of(monkeypatch, tmp_path, "elena")
    false_engine(monkeypatch, words_clip)
    compare(monkeypatch, "elena", "--language", "it", "--text", str(text_file(tmp_path)), "--root", str(project),
            "--out", str(tmp_path / "ascolto.wav"), "--no-check")
    out = capsys.readouterr().out
    row = re.search(r"^elena\s+\+0%\s+([\d.]+)\s+([\d.]+)\s+([\d.]+) s$", out, re.MULTILINE)
    assert row and float(row.group(1)) == pytest.approx(7 / (2.4 + 1.7), abs=0.01)      # 7 words in 4.1 seconds
    assert float(row.group(2)) == pytest.approx(2.5, abs=0.01) and float(row.group(3)) == pytest.approx(0.4, abs=0.05)
    assert f"File to listen: {tmp_path / 'ascolto.wav'}" in out


def test_the_recognizer_hears_each_clip_alone(tmp_path, monkeypatch, capsys):
    """The recognizer verifies each clip against its sentence. A clip that is different makes the
    command say it, and exit with 1."""
    project = project_of(monkeypatch, tmp_path, "elena")
    false_engine(monkeypatch, words_clip)
    common = ("elena", "--language", "it", "--text", str(text_file(tmp_path)), "--root", str(project), "--out", str(tmp_path / "a.wav"))
    false_recognizer(monkeypatch, *SENTENCES)
    assert compare(monkeypatch, *common) == 0
    assert "2 of 2 clips say their sentence" in capsys.readouterr().out
    false_recognizer(monkeypatch, SENTENCES[0], "Qualcos'altro, del tutto.")
    assert compare(monkeypatch, *common) == 1
    out = capsys.readouterr().out
    assert "1 of 2 clips say their sentence" in out and "[0." in out and "elena (+0%), sentence 2: Qualcos'altro, del tutto." in out
    assert "script: Cinque e sei." in out


def test_compare_without_the_recognizer(tmp_path, monkeypatch, capsys):
    """Without the package of the recognizer, the file is made and the command says that the clips
    are not verified. With --no-check, the recognizer does not start."""
    project = project_of(monkeypatch, tmp_path, "elena")
    false_engine(monkeypatch, words_clip)

    def missing(model, threads):
        raise RuntimeError("The package faster-whisper is not installed. Install the extra 'qa' of the template.")

    monkeypatch.setattr(cli, "_recognizer", missing)
    common = ("elena", "--language", "it", "--text", str(text_file(tmp_path)), "--root", str(project), "--out", str(tmp_path / "a.wav"))
    assert compare(monkeypatch, *common) == 0
    assert "The clips are not verified" in capsys.readouterr().out and (tmp_path / "a.wav").is_file()
    assert compare(monkeypatch, *common, "--no-check") == 0
    assert "not verified" not in capsys.readouterr().out


def test_compare_can_name_each_voice_before_its_clip(tmp_path, monkeypatch, capsys):
    """With --labels, the first voice of edge-tts for the language reads the name of the voice and
    its speed before each clip. When edge-tts fails, the file has no labels and the command says it."""
    project = project_of(monkeypatch, tmp_path, "voce_di-prova")
    false_engine(monkeypatch, lambda text, voice, rate: tone(1.0, 200))
    labels = []

    def synthesize(text, voice, rate):
        labels.append((text, voice, rate))
        return Clip(tone(0.3, 1000))

    monkeypatch.setattr(ENGINES["edge-tts"], "synthesize", synthesize)
    common = ("voce_di-prova", "--language", "it", "--text", str(text_file(tmp_path)), "--root", str(project), "--out", str(tmp_path / "a.wav"),
              "--no-check")
    assert compare(monkeypatch, *common, "--labels", "--rates", "+0%,+20%") == 0
    assert labels == [("voce di prova, +0%.", "it-IT-IsabellaNeural", "+0%"), ("voce di prova, +20%.", "it-IT-IsabellaNeural", "+0%")]
    sound = read_file(tmp_path / "a.wav")[0]
    assert len(sound) / SAMPLE_RATE == pytest.approx(2 * (1.5 + 2 * (0.3 + 0.25 + 1.0 + 0.9)), abs=0.01)
    assert frequency(sound, 1.5, seconds=0.3) == pytest.approx(1000, abs=1)   # the name of the voice and its speed...
    assert frequency(sound, 1.5 + 0.55) == pytest.approx(200, abs=1)       # ...then the clip

    def offline(text, voice, rate):
        raise RuntimeError("the service returned no audio")

    monkeypatch.setattr(ENGINES["edge-tts"], "synthesize", offline)
    assert compare(monkeypatch, *common, "--labels") == 0
    assert "no labels" in capsys.readouterr().out
    assert len(read_file(tmp_path / "a.wav")[0]) / SAMPLE_RATE == pytest.approx(2 * (1.5 + 1.9), abs=0.01)


def test_compare_reads_the_test_sentences_of_the_template(tmp_path, monkeypatch, capsys):
    """Without --text, the voices read the test sentences of the template for the language: four,
    and never the sentences that a person reads for the sample. A language without a file gives an error."""
    for name in ("elena",):
        voice_in(tmp_path / "project" / "voices", name)
    calls = false_engine(monkeypatch, words_clip)
    common = ("--root", str(tmp_path / "project"), "--out", str(tmp_path / "a.wav"), "--no-check")
    assert compare(monkeypatch, "elena", "--language", "it", *common) == 0
    capsys.readouterr()
    written = (Path(paths.__file__).parent / "templates" / "voice-test" / "it.txt").read_text(encoding="utf-8")
    sentences = [line.strip() for line in written.splitlines() if line.strip() and not line.startswith("#")]
    assert len(sentences) == 4 and [text for text, _voice, _rate in calls] == [speech.spoken(s, LANGS["it"].spoken_rules) for s in sentences]
    assert all(len(sentence.split()) >= 8 for sentence in sentences)
    monkeypatch.setitem(LANGS, "de", LANGS["it"].__class__(code="de", name="Deutsch", voices={"edge-tts": ("de-DE-KatjaNeural",)},
                                                    function_words=frozenset(), decimal_separator=","))
    assert compare(monkeypatch, "elena", "--language", "de", *common) == 2
    assert "No test sentences for the language 'de'" in capsys.readouterr().err
    # A file with comments only has no sentence: the command stops before it starts the model.
    (tmp_path / "a.wav").unlink()
    empty = tmp_path / "empty.txt"
    empty.write_text("# only a comment\n\n", encoding="utf-8")
    assert compare(monkeypatch, "elena", "--language", "it", "--text", str(empty), *common) == 2
    assert "has no sentence" in capsys.readouterr().err and not (tmp_path / "a.wav").exists()


def test_compare_says_what_is_missing(tmp_path, monkeypatch, capsys):
    """A voice that does not exist, and an engine that is not installed: the command stops before it
    starts a model or the recognizer."""
    project = project_of(monkeypatch, tmp_path, "elena")
    false_engine(monkeypatch, words_clip)
    common = ("--language", "it", "--text", str(text_file(tmp_path)), "--root", str(project), "--out", str(tmp_path / "a.wav"))
    no_recognizer(monkeypatch)
    assert compare(monkeypatch, "nobody", *common) == 2
    assert "has no voice 'nobody'" in capsys.readouterr().err and not (tmp_path / "a.wav").exists()
    assert compare(monkeypatch, "elena", "--text", str(tmp_path / "missing.txt"), "--language", "it", "--root", str(project),
                   "--out", str(tmp_path / "a.wav")) == 2
    assert "The file of the test sentences" in capsys.readouterr().err
    monkeypatch.setattr(ENGINES["omnivoice"], "status", lambda: Status(False, "not installed (the environment venv-omnivoice)"))
    assert compare(monkeypatch, "elena", *common) == 2
    assert "not installed" in capsys.readouterr().err and not (tmp_path / "a.wav").exists()
    # A speed that is not valid stops the command in the same way.
    monkeypatch.setattr(ENGINES["omnivoice"], "status", lambda: Status(True))
    assert compare(monkeypatch, "elena", "--rates", "fast", *common) == 2
    assert "The rate 'fast' is not valid" in capsys.readouterr().err


def test_compare_writes_its_file_next_to_the_voices(tmp_path, monkeypatch):
    """Without --out, the file goes to the folder `confronto` of the first folder of voices: that
    of the project. Its name has the date, the hour, the minute, the second and the names of the
    voices: two comparisons of the same voices do not write on the same file."""
    project = project_of(monkeypatch, tmp_path, "anna", "elena")
    false_engine(monkeypatch, lambda text, voice, rate: tone(1.0, 200))
    assert compare(monkeypatch, "anna", "elena", "--language", "it", "--text", str(text_file(tmp_path)), "--root", str(project), "--no-check") == 0
    files = list((project / "voices" / "confronto").glob("*.wav"))
    assert len(files) == 1 and re.fullmatch(r"\d{8}-\d{6}-anna-elena\.wav", files[0].name)


# ------------------------------------------------------------------------- the command of the parser


def test_the_command_voice_prepare(tmp_path, monkeypatch, capsys):
    """`videogen voice-prepare` writes the voice in the folder `voices` of the template, or in that
    of the project with --root. The speed is optional."""
    monkeypatch.setattr(paths, "template_root", lambda: tmp_path / "template")
    monkeypatch.setattr(sys, "argv", ["videogen", "voice-prepare", str(tmp_path / "p.wav"), "--help"])
    with pytest.raises(SystemExit) as stop:
        cli.main()
    assert stop.value.code == 0 and "--pauses" in capsys.readouterr().out
    recording = wav_file(tmp_path / "a.wav", np.concatenate(READ_SLOWLY))
    for arguments, folder in (((), tmp_path / "template"), (("--root", str(tmp_path / "video")), tmp_path / "video")):
        monkeypatch.setattr(sys, "argv", ["videogen", "voice-prepare", "mia", str(recording), "--text", SPOKEN, "--rate", "+32%", *arguments])
        assert cli.main() == 0
        assert (folder / "voices" / "mia.wav").is_file() and (folder / "voices" / "mia.toml").is_file()

