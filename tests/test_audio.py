"""The audio of a file with more than one channel. `decode_audio` makes the mean of the channels,
and `videogen voice-adopt` keeps the level of a recording of the user."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
import pytest

from videogen import speech
from videogen import config as video_config
from videogen.narration import load_script
from videogen.tts import SAMPLE_RATE, decode_audio

PEAK = 0.9


def sound() -> np.ndarray:
    """A voice-like sound that peaks at PEAK, with a little silence around it."""
    time = np.arange(int(0.5 * SAMPLE_RATE)) / SAMPLE_RATE
    word = (PEAK * np.sin(2 * np.pi * 180 * time) * np.hanning(len(time))).astype(np.float32)
    return np.concatenate([np.zeros(int(0.1 * SAMPLE_RATE), np.float32), word, np.zeros(int(0.1 * SAMPLE_RATE), np.float32)])


def wav_file(path: Path, mono: np.ndarray, channels: int = 1) -> Path:
    """A file WAV, 16-bit PCM. With two channels, the sound is the same on both."""
    path.parent.mkdir(parents=True, exist_ok=True)
    block = np.column_stack([mono] * channels)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes((np.clip(block, -1, 1) * 32767).astype("<i2").tobytes())
    return path


def test_decode_audio_is_the_mean_of_the_channels(tmp_path):
    """The change to mono of ffmpeg (`-ac 1`) is not the mean of the channels: it multiplies each
    channel by 0.707. A stereo file gained 3 decibels (a sound at 0.9 came out at 1.27), and a loud
    recording clips in a file of 16 bits."""
    voice = sound()
    both = decode_audio(wav_file(tmp_path / "stereo.wav", voice, channels=2))
    assert len(both) == len(voice) and np.abs(both).max() == pytest.approx(PEAK, abs=0.01)
    alone = decode_audio(wav_file(tmp_path / "mono.wav", voice))
    assert len(alone) == len(voice) and np.abs(alone).max() == pytest.approx(PEAK, abs=0.01)


def test_a_file_that_is_not_audio(tmp_path):
    (tmp_path / "false.wav").write_text("this is not audio", encoding="utf-8")
    with pytest.raises(RuntimeError, match="ffmpeg does not read"):
        decode_audio(tmp_path / "false.wav")


def test_a_recording_of_the_user_keeps_its_level(tmp_path):
    """`videogen voice-adopt` makes the clip of a stereo recording at the mean of its channels: a
    recording that peaks at 0.9 gives a clip at 0.9."""
    (tmp_path / "video.toml").write_text('title = "T"\nlanguage = "it"\nengine = "edge-tts"\n', encoding="utf-8")
    (tmp_path / "narration.py").write_text(
        "from collections import namedtuple\nBeat = namedtuple('Beat', 'key text visual')\nSCENE_ORDER = ['ch00']\n"
        "CHAPTERS = {'ch00': ('', '')}\nNARRATION = {'ch00': [Beat('a1', 'Una frase detta da me.', 'a line')]}\n", encoding="utf-8",
    )
    recordings = tmp_path / "registrazioni"
    wav_file(recordings / "ch00_a1.wav", sound(), channels=2)
    adopted, skipped = speech.adopt_recordings(load_script(tmp_path), video_config.load(tmp_path), recordings)
    assert (adopted, skipped) == (1, 0)
    clip = speech.read_wav(speech.clip_path(tmp_path, "ch00", "a1"))
    assert np.abs(clip).max() == pytest.approx(PEAK, abs=0.01)
    assert speech.load_timing(tmp_path, "ch00")["beats"]["a1"]["hash"] == "manual"
