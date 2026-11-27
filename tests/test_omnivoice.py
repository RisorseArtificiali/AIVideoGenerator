"""The speech engine omnivoice: its voices, the numbers in words, the time of the words, and the
dialogue with its worker. The worker of the tests is a small script that answers like the real
one: these tests need neither the model nor a GPU. `test_the_model_reads_a_clip` starts the real
worker: it needs the install of tools/setup-omnivoice.sh, and AIVIDEOGEN_SELFTEST=1."""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest

from videogen import cli, paths, speech, subtitles
from videogen import config as video_config
from videogen.langs import LANGS
from videogen.narration import load_script
from videogen.tts import ENGINES, SAMPLE_RATE
from videogen.tts import omnivoice as engine_module
from videogen.tts.omnivoice import OmniVoiceEngine, Sample, Worker, find_sample, folders_of, sample_names, speed_of, times_of

# A worker that speaks the protocol of the real one. Its mode says how it fails:
# "die" stops at the first clip of its first run, "sleep" never answers, "garbage" answers out
# of the protocol, "error" refuses every clip, "now" stops before it says that it is ready.
FAKE_WORKER = '''
import base64, json, os, sys, time

mode, log = sys.argv[1], sys.argv[2]


def send(answer):
    sys.stdout.write(json.dumps(answer) + "\\n")
    sys.stdout.flush()


if mode == "now":
    sys.exit(3)
hello = {"ok": True, "device": "cpu"}
send(hello)
if mode == "sleep":
    time.sleep(60)
for line in sys.stdin.buffer:
    with open(log, "ab") as handle:
        handle.write(line)
    if mode == "garbage":
        sys.stdout.write("not an answer in JSON\\n")
        sys.stdout.flush()
        continue
    request = json.loads(line)
    if request.get("op") == "ping":
        send(hello)
        continue
    if mode == "die" and not os.path.exists(log + ".died"):
        open(log + ".died", "w").close()          # the first run stops at its first clip
        sys.exit(3)
    if mode == "error":
        send({"ok": False, "error": "The model gave no audio for this text."})
        continue
    words = request["text"].split()
    step = 0.3
    spans = [[round(0.2 + index * step, 3), round(0.44 + index * step, 3)] for index in range(len(words))]
    samples = bytes(4 * int((0.2 + len(words) * step + 0.2) * 48000))
    send({"ok": True, "rate": 48000, "seconds": 0.0, "samples": base64.b64encode(samples).decode("ascii"), "spans": spans})
'''

TRANSCRIPT = "Questa è una frase di prova: il campione di una voce, con il suo testo."
LEAD = engine_module.LEAD


def make_voice(folder: Path, name: str = "elsa", extension: str = "wav") -> Path:
    """A voice in a folder: a sample (a file that is not read: the worker of the tests does not
    open it) and its transcript."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.txt").write_text(TRANSCRIPT + "\n", encoding="utf-8")
    sample = folder / f"{name}.{extension}"
    sample.write_bytes(b"RIFF" + bytes(100))
    return sample


@pytest.fixture
def fake_worker(tmp_path) -> Path:
    path = tmp_path / "fake_worker.py"
    path.write_text(FAKE_WORKER, encoding="utf-8")
    return path


def fake_engine(worker: Path, voices: Path, mode: str = "good", **options) -> OmniVoiceEngine:
    engine = OmniVoiceEngine(command=[sys.executable, "-I", str(worker), mode, str(worker.with_suffix(".log"))], folders=[voices])
    engine.worker.timeout = options.get("timeout", engine.worker.timeout)
    engine.worker.start = options.get("start", engine.worker.start)
    return engine


def requests_of(worker: Path) -> list[dict]:
    return [json.loads(line) for line in worker.with_suffix(".log").read_text(encoding="utf-8").splitlines()]


def test_speed_of_the_rate():
    assert speed_of("+10%") == 1.1
    assert speed_of("-5%") == 0.95
    assert speed_of("+0%") == 1.0
    assert speed_of("fast") == 1.0


def test_a_voice_is_a_sample_with_its_transcript(tmp_path):
    template, project = tmp_path / "template", tmp_path / "video"
    elsa = make_voice(template / "voices", "elsa")
    make_voice(project / "voices", "mia", "mp3")
    (project / "voices" / "silent.txt").write_text("A transcript without its audio file.\n", encoding="utf-8")
    folders = [project / "voices", template / "voices"]
    sample = find_sample("mia", folders, project)
    assert isinstance(sample, Sample) and sample.path == (project / "voices" / "mia.mp3").resolve()
    assert sample.text == TRANSCRIPT and sample.name == "mia"
    assert find_sample("elsa", folders, project).path == elsa.resolve()
    assert find_sample("nobody", folders, project) is None
    assert find_sample("silent", folders, project) is None            # no audio, no voice
    # The path of an audio file: absolute, or relative to the folder of the video.
    assert find_sample("voices/mia", [template / "voices"], project).path == sample.path
    assert find_sample("voices/mia.mp3", [], project).path == sample.path
    assert find_sample(str(elsa), [], None).path == elsa.resolve()
    assert find_sample(str(tmp_path / "elsa.mp3"), [], project) is None      # the transcript is not there
    assert sample_names(folders) == ["mia", "elsa"]
    make_voice(project / "voices", "elsa")                                   # a voice of the video comes before that of the template
    assert sample_names(folders) == ["elsa", "mia"] and find_sample("elsa", folders, project).path.parent == project / "voices"
    assert sample_names([tmp_path / "elsewhere"]) == []


def test_the_voices_of_a_project_come_before_those_of_the_template(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "template_root", lambda: tmp_path / "template")
    make_voice(tmp_path / "template" / "voices", "of-the-template")
    engine = OmniVoiceEngine()
    assert folders_of(None) == [tmp_path / "template" / "voices"]
    assert engine.voices(LANGS["it"]) == ["of-the-template"]           # before there is a video: the voices of the template
    make_voice(tmp_path / "video" / "voices", "of-the-video")
    assert folders_of(tmp_path / "video") == [tmp_path / "video" / "voices", tmp_path / "template" / "voices"]
    assert engine.voices(LANGS["it"], tmp_path / "video") == ["of-the-video", "of-the-template"]
    make_voice(tmp_path / "video" / "voices", "of-the-template")      # the same name: the voice of the video wins
    assert find_sample("of-the-template", folders_of(tmp_path / "video"), tmp_path / "video").path.parent == tmp_path / "video" / "voices"


def test_the_numbers_in_words():
    pytest.importorskip("num2words")
    from videogen.tts.numbers import spoken_tokens, spoken_text

    text = "Lo 0,042% costa 3,61 volte, tra 200–350 e 5.000 dollari: il 96° del 2026."
    tokens = spoken_tokens(text, "it")
    assert [token for token, _words in tokens] == text.split()         # the tokens keep the punctuation and the digits
    words = [word for _token, group in tokens for word in group]
    assert " ".join(words) == ("Lo zero virgola zero quattro due per cento costa tre virgola sessantuno volte, "
                               "tra duecento, trecentocinquanta e cinquemila dollari: il novantaseiesimo del duemilaventisei.")
    assert spoken_text("Ecco 3.61 e 5.5, 2,500 dollars, the 3rd of May.", "en") == \
        "Ecco three point six one e five point five, two thousand, five hundred dollars, the third of May."
    assert spoken_text("Cresce del -5% e costa $3.", "it") == "Cresce del meno cinque per cento e costa tre dollari."
    assert spoken_text("Nel 2026 — davvero.", "de") == "Nel 2026 — davvero."        # a language without numbers in words
    # A token that is only a pause says nothing; an article with an apostrophe stays with its number.
    assert spoken_tokens("l'1 — e", "it") == [("l'1", ["l'uno"]), ("—", []), ("e", ["e"])]


def test_the_time_of_each_token():
    tokens = [("Nel", ["Nel"]), ("2026,", ["duemilaventisei,"]), ("—", []), ("cresce.", ["cresce", "di", "poco."])]
    spans = [[0.26, 0.44], [0.56, 1.50], [1.60, 1.64], [1.70, 1.98], [2.00, 2.30]]
    timed = times_of(tokens, spans, length=2.5)
    assert [word for _start, _duration, word in timed] == ["Nel", "2026,", "—", "cresce."]
    # The times come a little before the sound of the words (LEAD).
    assert timed[0] == (pytest.approx(0.26 - LEAD), pytest.approx(0.18), "Nel")
    assert timed[1] == (pytest.approx(0.56 - LEAD), pytest.approx(0.94), "2026,")
    assert timed[2] == (pytest.approx(1.50 - LEAD), 0.0, "—")          # the pause is shown, but it has no time of its own
    assert timed[3] == (pytest.approx(1.60 - LEAD), pytest.approx(0.70), "cresce.")   # from its first word to its last one
    long = times_of([("parola", ["pa", "ro", "la"])], [[0.2, 1.0], [1.0, 2.0], [2.0, 3.0]], length=1.4)
    assert long == [(pytest.approx(0.14), pytest.approx(1.26), "parola")]    # a word after the end of the clip stops at the end
    with pytest.raises(RuntimeError, match="the time of 2 words; the text has 4"):
        times_of(tokens[:1] + tokens[3:], spans[:2], length=3.0)


def test_the_engine_reads_the_numbers_in_words_and_keeps_them_in_the_subtitles(tmp_path, fake_worker):
    voices = tmp_path / "voices"
    make_voice(voices, "elsa")
    engine = fake_engine(fake_worker, voices)
    engine.configure(tmp_path, LANGS["it"])
    text = "Nel 2026 la misura è 3,61 volte — per il 96° rapporto."
    clip = engine.synthesize(text, "elsa", "+10%")
    request, = requests_of(fake_worker)
    assert request["text"] == "Nel duemilaventisei la misura è tre virgola sessantuno volte per il novantaseiesimo rapporto."
    assert request["language"] == "it" and request["speed"] == 1.1
    assert request["ref"] == str((voices / "elsa.wav").resolve()) and request["ref_text"] == TRANSCRIPT
    assert isinstance(request["seed"], int) and 0 <= request["seed"] < 2 ** 32
    # One entry for each token of the text: the subtitles show the numbers as they are written.
    assert [word for _start, _duration, word in clip.words] == text.split()
    assert clip.words[1] == (pytest.approx(0.5 - LEAD), 0.24, "2026")
    assert clip.words[5] == (pytest.approx(1.7 - LEAD), pytest.approx(0.84), "3,61")   # three words, one token
    assert clip.words[7] == (pytest.approx(2.84 - LEAD), 0.0, "—")
    assert clip.words[8] == (pytest.approx(2.90 - LEAD), 0.24, "per")     # the next word keeps its own time
    assert len(clip.samples) == int((0.2 + 13 * 0.3 + 0.2) * SAMPLE_RATE)
    cues = subtitles.group_cues(clip.words, LANGS["it"].function_words)
    assert " ".join(text for _start, _end, text in cues) == text
    # A voice by its path, relative to the folder of the video.
    make_voice(tmp_path / "other", "gia", "flac")
    clip = engine.synthesize("Una frase.", "other/gia", "+0%")
    assert [word for _start, _duration, word in clip.words] == ["Una", "frase."]
    assert requests_of(fake_worker)[1]["ref"] == str((tmp_path / "other" / "gia.flac").resolve())


def test_an_unknown_voice_says_which_ones_exist(tmp_path, fake_worker):
    engine = fake_engine(fake_worker, tmp_path / "voices")
    make_voice(tmp_path / "voices", "elsa")
    engine.configure(tmp_path, LANGS["it"])
    with pytest.raises(RuntimeError, match=r"OmniVoice has no voice 'it-IT-ElsaNeural' \(the voices of the folders voices/ are: elsa\)"):
        engine.synthesize("Una frase.", "it-IT-ElsaNeural", "+0%")
    (tmp_path / "voices" / "elsa.txt").write_text("  \n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="The transcript of the voice 'elsa' is empty"):
        engine.synthesize("Una frase.", "elsa", "+0%")
    assert not fake_worker.with_suffix(".log").exists()               # no worker starts for a wrong voice


def test_the_errors_of_the_model_and_the_seed_of_a_clip(tmp_path, fake_worker):
    voices = tmp_path / "voices"
    make_voice(voices, "elsa")
    engine = fake_engine(fake_worker, voices, "error")
    engine.configure(tmp_path, LANGS["it"])
    with pytest.raises(RuntimeError, match="OmniVoice: The model gave no audio for this text."):
        engine.synthesize("Una frase.", "elsa", "+0%")
    engine.worker.close()
    # The model chooses at random. The seed comes from the text, the voice and the rate: the same
    # clip made again is the same.
    engine = fake_engine(fake_worker, voices)
    engine.configure(tmp_path, LANGS["it"])
    engine.synthesize("Una frase.", "elsa", "+0%")
    engine.synthesize("Una frase.", "elsa", "+0%")
    engine.synthesize("Una frase.", "elsa", "+5%")
    engine.synthesize("Un'altra frase.", "elsa", "+0%")
    seeds = [request["seed"] for request in requests_of(fake_worker)[1:]]   # the first request is that of the worker in error
    assert seeds[0] == seeds[1] and seeds[2] != seeds[0] and seeds[3] != seeds[0]


def test_a_worker_that_stops_or_never_answers(tmp_path, fake_worker):
    log = fake_worker.with_suffix(".log")
    worker = Worker([sys.executable, "-I", str(fake_worker), "die", str(log)])
    assert worker.request({"op": "ping"}) == {"ok": True, "device": "cpu"}
    answer = worker.request({"op": "synthesize", "text": "Una frase."})   # the first worker stops at its first clip
    assert answer["ok"] is False and "the worker of OmniVoice stopped" in answer["error"]
    assert worker.process is None and log.with_suffix(".log.died").exists()
    assert worker.request({"op": "ping"}) == {"ok": True, "device": "cpu"}   # a new worker starts
    assert worker.request({"op": "synthesize", "text": "Una frase."})["ok"] is True
    pid = worker.process.pid
    worker.close()
    worker.close()                                                    # nothing left to close: no error
    assert worker.process is None
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)                                               # the worker is gone

    worker = Worker([sys.executable, "-I", str(fake_worker), "sleep", str(log)], timeout=1.0, grace=0.5)
    answer = worker.request({"op": "ping"})                           # no answer: the worker is stopped, then killed
    assert answer["ok"] is False and "gave no answer in 1 seconds" in answer["error"] and worker.process is None

    worker = Worker([sys.executable, "-I", str(fake_worker), "garbage", str(log)])
    answer = worker.request({"op": "ping"})
    assert answer["ok"] is False and "not JSON" in answer["error"]

    worker = Worker([sys.executable, "-I", str(fake_worker), "now", str(log)])
    with pytest.raises(RuntimeError, match="OmniVoice does not start: the worker of OmniVoice stopped"):
        worker.request({"op": "ping"})

    worker = Worker([str(tmp_path / "no-python"), str(fake_worker), "good", str(log)])
    with pytest.raises(RuntimeError, match="OmniVoice does not start: .* Start tools/setup-omnivoice.sh"):
        worker.request({"op": "ping"})

    engine = OmniVoiceEngine(command=[str(tmp_path / "no-python")], folders=[tmp_path / "voices"])
    with pytest.raises(RuntimeError, match="no voice 'elsa'"):         # a wrong voice: the error comes before the worker
        engine.synthesize("Una frase.", "elsa", "+0%")


def test_the_command_of_the_worker(monkeypatch, tmp_path):
    monkeypatch.setenv("AIVIDEOGEN_TOOLS", str(tmp_path / "tools"))
    monkeypatch.delenv("OMNIVOICE_DEVICE", raising=False)
    command = OmniVoiceEngine.command()
    assert command[:2] == [str(tmp_path / "tools" / "venv-omnivoice" / "bin" / "python"), "-I"]
    assert command[-4:] == ["--model", str(tmp_path / "tools" / "models" / "omnivoice"),
                            "--aligner", str(tmp_path / "tools" / "models" / "mms-fa")]
    monkeypatch.setenv("OMNIVOICE_DEVICE", "cpu")
    assert OmniVoiceEngine.command()[-2:] == ["--device", "cpu"]


def test_the_status_of_an_optional_engine(monkeypatch, tmp_path):
    engine = OmniVoiceEngine(folders=[tmp_path / "voices"])
    assert engine.optional is True and ENGINES["edge-tts"].optional is False
    monkeypatch.delenv("OMNIVOICE_DEVICE", raising=False)
    monkeypatch.setenv("AIVIDEOGEN_TOOLS", str(tmp_path / "tools"))     # nothing is installed there
    monkeypatch.delenv("OMNIVOICE_DEVICE", raising=False)
    status = engine.status()
    assert status.available is False and "Start tools/setup-omnivoice.sh" in status.detail
    assert "the environment venv-omnivoice" in status.detail
    for file in ("venv-omnivoice/bin/python", "models/omnivoice/model.safetensors", "models/mms-fa/checkpoints/model.pt"):
        path = tmp_path / "tools" / file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    if not engine.status().available:                                  # num2words is not in the environment of these tests
        return
    assert "no voice yet" in engine.status().detail
    make_voice(tmp_path / "voices")
    detail = engine.status().detail
    assert detail.endswith("voices: elsa") and "with a sample of a voice" in detail
    monkeypatch.setenv("OMNIVOICE_DEVICE", "cpu")
    assert "the device cpu of OMNIVOICE_DEVICE" in engine.status().detail

def test_doctor_and_options_show_an_optional_engine(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("AIVIDEOGEN_TOOLS", str(tmp_path / "tools"))     # nothing is installed there
    monkeypatch.delenv("OMNIVOICE_DEVICE", raising=False)
    assert cli.cmd_doctor(cli.build_parser().parse_args(["doctor"])) == 1
    output = capsys.readouterr().out
    assert "OPTIONAL speech engine omnivoice: not installed (" in output and "MISSING speech engine edge-tts" not in output
    cli.cmd_options(cli.build_parser().parse_args(["options"]))
    data = json.loads(capsys.readouterr().out)
    engine = [entry for entry in data["engines"] if entry["id"] == "omnivoice"][0]
    assert engine["optional"] is True and engine["available"] is False and "voices/<name>.wav" in engine["voices_help"]
    assert [entry["optional"] for entry in data["engines"] if entry["id"] == "edge-tts"] == [False]


def test_the_default_voice_of_the_engine(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "template_root", lambda: tmp_path / "template")   # no voice in the template
    (tmp_path / "video.toml").write_text('title = "T"\nlanguage = "it"\nengine = "omnivoice"\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r"has no voice for the language 'it'.*voices/<name>.wav"):
        video_config.load(tmp_path).resolved_voice
    make_voice(tmp_path / "voices", "mia")
    make_voice(tmp_path / "voices", "altri")
    assert video_config.load(tmp_path).resolved_voice == "altri"        # the voices are in the order of their names
    make_voice(tmp_path / "template" / "voices", "del-template")
    assert ENGINES["omnivoice"].voices(LANGS["it"], tmp_path) == ["altri", "mia", "del-template"]
    (tmp_path / "video.toml").write_text('title = "T"\nlanguage = "it"\nengine = "omnivoice"\nvoice = "mia"\n', encoding="utf-8")
    assert video_config.load(tmp_path).resolved_voice == "mia"


def test_a_voice_can_have_its_speed(tmp_path, monkeypatch):
    """A third file of a voice, `voices/<name>.toml`, gives its speed. A voice without the file has none."""
    monkeypatch.setattr(paths, "template_root", lambda: tmp_path / "template")
    voices = tmp_path / "template" / "voices"
    make_voice(voices, "elsa")
    make_voice(voices, "mia")
    engine = ENGINES["omnivoice"]
    assert engine.default_rate("mia") == "" and engine.default_rate(None) == ""      # no voice has a speed
    (voices / "mia.toml").write_text('rate = "+32%"\n', encoding="utf-8")
    assert engine.default_rate("mia") == "+32%" and engine.default_rate("elsa") == ""
    assert engine.default_rate(None) == ""                                            # the first voice (elsa) has no speed
    (voices / "elsa.toml").write_text('rate = "-5%"\n', encoding="utf-8")
    assert engine.default_rate(None) == "-5%"                                         # the default voice is the first one
    (voices / "elsa.toml").write_text('rate = "fast"\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r"The rate 'fast' in .*elsa\.toml is not valid"):
        engine.default_rate("elsa")
    assert ENGINES["edge-tts"].default_rate("en-US-AndrewNeural") == ""               # the other engines have no speed of a voice


def test_a_new_project_takes_the_speed_of_its_voice(tmp_path, monkeypatch, capsys):
    """`videogen new` writes the speed of the voice in video.toml: each video can then change its `rate`."""
    monkeypatch.setattr(paths, "template_root", lambda: tmp_path / "template")
    voices = tmp_path / "template" / "voices"
    make_voice(voices, "elsa")
    make_voice(voices, "mia")
    (voices / "mia.toml").write_text('rate = "+32%"\n', encoding="utf-8")

    def new(name, *options):
        folder = tmp_path / name
        folder.mkdir()                                    # the templates of the template make it, when they are there
        cli.cmd_new(cli.build_parser().parse_args(["new", str(folder), "--language", "it", "--engine", "omnivoice", *options]))
        return folder, capsys.readouterr().out

    folder, output = new("mine", "--voice", "mia")
    assert video_config.load(folder).rate == "+32%" and video_config.load(folder).resolved_voice == "mia"
    assert '+32%' in output and "mia.toml" in output                                  # the project says where the speed comes from
    folder, _output = new("yours", "--voice", "elsa")
    assert video_config.load(folder).rate == "+0%"                                     # a voice without a speed
    folder, _output = new("default")
    assert video_config.load(folder).rate == "+0%" and video_config.load(folder).resolved_voice == "elsa"
    assert video_config.load(tmp_path / "mine").rate == "+32%"


def test_a_changed_sample_makes_the_clips_again(tmp_path, fake_worker):
    voices = tmp_path / "voices"
    sample = make_voice(voices, "elsa")
    engine = fake_engine(fake_worker, voices)
    (tmp_path / "video.toml").write_text('title = "T"\nlanguage = "it"\nengine = "omnivoice"\nvoice = "elsa"\n', encoding="utf-8")
    (tmp_path / "narration.py").write_text(
        "from collections import namedtuple\nBeat = namedtuple('Beat', 'key text visual')\nSCENE_ORDER = ['ch00']\n"
        "CHAPTERS = {'ch00': ('', '')}\nNARRATION = {'ch00': [Beat('a1', 'Nel 2026.', 'a line')]}\n", encoding="utf-8",
    )
    config, script = video_config.load(tmp_path), load_script(tmp_path)
    lines = []
    speech.synthesize(script, config, engine, log=lines.append)
    timing = speech.load_timing(tmp_path, "ch00")
    assert timing["engine"] == "omnivoice" and timing["voice"] == "elsa" and timing["rate"] == "+0%"
    assert [word for _start, _duration, word in timing["beats"]["a1"]["words"]] == ["Nel", "2026."]
    assert timing["beats"]["a1"]["spoken"] == "Nel 2026."              # the subtitles show the script, not the words of the model
    assert lines == ["1 clips to synthesize with omnivoice (elsa, +0%)", "  ch00/a1: 1.00 s"]
    speech.synthesize(script, config, engine, log=lines.append)
    assert len(lines) == 2                                              # the clip is there: nothing to make
    sample.write_bytes(sample.read_bytes() + bytes(4))
    speech.synthesize(script, config, engine, log=lines.append)
    assert len(lines) == 4 and "1 clips to synthesize" in lines[2]      # the sample changed: the clip is old
    assert speech.load_timing(tmp_path, "ch00")["beats"]["a1"]["hash"] != timing["beats"]["a1"]["hash"]


def test_the_silences_of_a_clip():
    """The worker receives the audio of the model: it keeps a short lead and tail, and shortens
    the long pauses. A click is not a word, and nothing that sounds is cut."""
    from videogen.tts import omnivoice_worker as worker

    rate = worker.RATE_OUT
    random = np.random.default_rng(7)
    time = np.arange(int(0.25 * rate)) / rate

    def word():                                           # 250 milliseconds of a voice-like sound
        return (0.5 * np.sin(2 * np.pi * 180 * time) * np.hanning(len(time))).astype(np.float32)

    def silence(seconds):                                 # the model leaves a little noise in the pauses
        return random.normal(0, 0.002, int(seconds * rate)).astype(np.float32)

    def click():
        sound = np.zeros(int(0.04 * rate), np.float32)
        sound[240:1200] = 0.3 * np.hanning(960)
        return sound

    def pauses_of(wave, minimum=0.2):                     # the silences of the clip, for the worker
        voiced, hop = worker._voiced(wave, rate)
        runs, start = [], None
        for index, flag in enumerate(list(voiced) + [True]):
            if not flag and start is None:
                start = index
            elif flag and start is not None:
                if (index - start) * hop / rate >= minimum:
                    runs.append(round((index - start) * hop / rate, 1))
                start = None
        return runs

    one, two = word(), word()
    out = worker.clean(np.concatenate([silence(2.0), one, silence(1.6), two, silence(1.0)]), rate)
    assert len(out) / rate == pytest.approx(0.15 + 0.25 + 0.5 + 0.25 + 0.15, abs=0.05)
    assert pauses_of(out) == [0.5]                                     # the pause of 1.6 seconds became 0.5
    assert np.abs(out[: int(0.13 * rate)]).max() == 0.0                # the clip starts in silence...
    assert np.abs(out[-100:]).max() < 1e-3 and out[-1] == 0.0          # ...and ends in silence
    assert pauses_of(worker.clean(np.concatenate([one, silence(0.3), two]), rate)) == [0.3]
    assert pauses_of(worker.clean(np.concatenate([one, silence(0.6), two]), rate)) == [0.6]    # a pause under 0.7 seconds stays
    # A click does not split a pause, and it is not cut.
    out = worker.clean(np.concatenate([silence(0.5), one, silence(0.4), click(), silence(0.3), two]), rate)
    assert len(out) / rate == pytest.approx(0.15 + 0.25 + 0.5 + 0.25, abs=0.05) and pauses_of(out) == [0.2, 0.2]
    middle = out[int(0.4 * rate):int(0.65 * rate)]
    assert np.abs(middle).max() == pytest.approx(0.3, abs=0.01)
    # A click before the first word does not move the start of the clip.
    out = worker.clean(np.concatenate([silence(0.5), click(), silence(0.76), one, silence(0.3)]), rate)
    assert len(out) / rate == pytest.approx(0.15 + 0.25 + 0.15, abs=0.05) and pauses_of(out) == []
    # A sound of 40 milliseconds inside a long pause stays, when the pause becomes shorter around it.
    burst = word()[: int(0.04 * rate)]
    out = worker.clean(np.concatenate([silence(0.5), one, silence(0.45), burst, silence(0.45), two, silence(0.3)]), rate)
    assert len(out) / rate == pytest.approx(0.15 + 0.25 + 0.54 + 0.25 + 0.15, abs=0.1)    # the pause: 0.25, the sound, 0.25
    assert np.abs(out[int(0.5 * rate):int(0.9 * rate)]).max() == pytest.approx(np.abs(burst).max(), abs=0.01)
    # A word between two pauses of 0.45 seconds: each pause stays, because each one is under 0.7 seconds
    # (the pauses measure 0.5 with the quiet ends of the synthetic words).
    out = worker.clean(np.concatenate([one, silence(0.45), two, silence(0.45), one]), rate)
    assert pauses_of(out) == [0.5, 0.5]
    for wave in (silence(1.0), click(), one[:100], np.zeros(0, np.float32)):
        assert len(worker.clean(wave, rate)) == len(wave)              # nothing to clean: the audio stays
    assert worker.set_level(out).shape == out.shape
    loud = worker.set_level(np.concatenate([silence(0.5), one, silence(0.5)]))
    assert np.sqrt(np.mean(loud.astype(np.float64) ** 2)) == pytest.approx(worker.LEVEL)   # the RMS of the whole clip
    assert worker.set_level(np.zeros(rate, np.float32)).tolist() == [0.0] * rate   # silence stays silent
    assert np.sqrt(np.mean(worker.set_level(silence(1.0)).astype(np.float64) ** 2)) == pytest.approx(worker.LEVEL)   # noise alone becomes loud...


def test_the_recognizer_can_write_a_number_as_digits_or_as_words():
    pytest.importorskip("num2words")
    script = "Lo 0,042% dei modelli costa 5.000 dollari."
    assert cli._similarity("Lo 0 ,042 % dei modelli costa 5 .000 dollari.", "it", script) == 1.0
    assert cli._similarity("Lo zero virgola zero quattro due per cento dei modelli costa cinquemila dollari.", "it", script) == 1.0
    assert cli._similarity("Lo 0,042% dei modelli costa cinquemila dollari.", "it", script) == 1.0          # digits and words together
    assert cli._similarity("GPT cinque punto sei", "it", "GPT 5 punto 6") == 1.0
    assert cli._similarity("The third of May", "en", "The 3rd of May") == 1.0
    assert cli._similarity("Una frase diversa.", "it", "Una frase.") < 1.0
    # The rules of spoken_rules.py change the text that the voice reads. The recognizer writes
    # what it hears in its own way: the written text of the beat is accepted too.
    written, spoken = "OpenAI ha rilasciato GPT-5.6 a novembre del 2025, e cresce del 96°.", "Open AI ha rilasciato GPT 5 punto 6 a novembre del 2025, e cresce del 96°."
    heard = "OpenAI ha rilasciato GPT 5.6 a novembre del 2025 e cresce del 96esimo."
    assert cli._similarity(heard, "it", spoken, written) > cli._similarity(heard, "it", spoken) > 0.9
    assert cli._similarity(heard.replace("OpenAI ", ""), "it", spoken, written) > 0.9         # the recognizer lost the first name
    assert cli._similarity("NanoGPT è piccolo.", "it", "Nano GPT è piccolo.", "NanoGPT è piccolo.") > cli._similarity("NanoGPT è piccolo.", "it", "Nano GPT è piccolo.")
    too_long = "Nel " + "9" * 70 + "."
    assert cli._numbers_in_words(too_long, "it") == too_long          # a number too long for num2words stays as it is
    assert cli._numbers_in_words("Nel 2026.", "de") == "Nel 2026."


@pytest.mark.pipeline
@pytest.mark.skipif(not os.environ.get("AIVIDEOGEN_SELFTEST"), reason="Set AIVIDEOGEN_SELFTEST=1 to start the model.")
def test_the_model_reads_a_clip():
    """The real worker: it loads the model, reads a clip with a voice of its own, and gives the
    time of the words."""
    worker = Worker(OmniVoiceEngine.command())
    text = "Una frase di prova, con i numeri in parole: tre virgola sessantuno."
    answer = worker.request({"op": "synthesize", "text": text, "language": "it", "speed": 1.0, "seed": 1})
    pid = worker.process.pid
    worker.close()
    assert answer.get("ok"), answer
    samples = np.frombuffer(base64.b64decode(answer["samples"]), dtype="<f4")
    seconds = len(samples) / SAMPLE_RATE
    assert answer["rate"] == SAMPLE_RATE and 2.0 < seconds < 15.0
    assert len(answer["spans"]) == len(text.split())
    starts = [start for start, _end in answer["spans"]]
    assert starts == sorted(starts) and 0.1 < starts[0] < 1.0 and answer["spans"][-1][1] < seconds
    assert np.sqrt(np.mean(samples.astype(np.float64) ** 2)) == pytest.approx(0.10, abs=0.02)   # the level of the clips of edge-tts
    assert np.abs(samples[: int(0.12 * SAMPLE_RATE)]).max() < 1e-6                      # the clip starts in silence
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)                                                                       # the worker stops with videogen
