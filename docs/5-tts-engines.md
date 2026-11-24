# Speech engines

A speech engine changes one line of text to audio, and gives the time of each word. `videogen tts` uses the engine of `video.toml`.

## The engine in the template: edge-tts

- It uses the Read Aloud service of Microsoft Edge. It is online, free, and needs no key.
- It is not an official API. The service can change or stop without notice.
- The text of the narration goes to the servers of Microsoft.
- The voices of a language are in `videogen/langs.py`. For the full list: `videogen options --online`.

## Your own recordings

1. Write the narration and make the voice clips: `videogen tts`. Then make the script: `videogen script`. `script.md` has the text of each beat and its ID.
2. Record one audio file for each beat. Use the format `<scene>_<beat>.wav`, for example `ch02_c8.wav`. WAV, MP3, FLAC and OGG operate.
3. Adopt the recordings:

   ```bash
   videogen voice-adopt ~/recordings
   ```

   The command removes the silence at the start and at the end of each file, and records the new length of the beat.

4. Write or render the scenes again. The scenes follow the new length of the clips.

A recorded beat has no time for each word. On that beat, `hold_until` uses the middle of the clip. Use `self.dur("key")` to divide the beat in parts.

## Keys in the .env file

An engine with an API key reads the key from the environment. Put the key in a `.env` file, in the folder of the template or in the folder of the video project. `videogen` reads these files when it starts. The file `.gitignore` keeps `.env` out of git. The file `.env.example` shows the form.

```
MY_SERVICE_KEY=1234567890
```

A variable that is already in the environment keeps its value.

## How to add an engine

Write a class that inherits from `Engine` in a new file in `videogen/tts/`. This example shows the three parts of an engine with an API key:

```python
import os

from videogen.tts import Clip, Engine, Status, decode_audio

class MyServiceEngine(Engine):
    id = "my-service"
    name = "Speech service with an API key"
    needs_env = ("MY_SERVICE_KEY",)       # videogen reads it from .env

    def status(self) -> Status:
        status = super().status()         # it verifies the variables of .env
        return status

    def voices(self, language):
        return language.voices.get(self.id, ())

    def synthesize(self, text, voice, rate) -> Clip:
        key = os.environ["MY_SERVICE_KEY"]
        # 1. Send the text to the service and get the audio in a file.
        # 2. Change the audio: samples = decode_audio(path_to_the_audio_file)
        # 3. Get the time of the words, if the service gives it: [(start, duration, word), ...]
        return Clip(samples, words)
```

Then:

1. Add an instance of the class to `ENGINES` in `videogen/tts.py`.
2. Add the voices of the engine for each language in `videogen/langs.py`: `voices={"edge-tts": (...), "my-service": (...)}`.
3. Add the key to `.env`.

`videogen options` shows the new engine with its status. The skill shows it in the menu.

### An engine with a local model on the GPU

The class is the same. These are the differences:

- `needs_env` is empty.
- `status()` verifies that the model is on the disk, and that the GPU operates.
- Load the model one time, before the first call of `synthesize`. Keep the model in an attribute of the engine.
- `videogen tts` calls `synthesize` from some threads at the same time. If the model operates on one thread only, protect it with a lock (`threading.Lock`).

`decode_audio(path)` changes any audio file to the form that `Clip` needs: mono, float32, at 48000 Hz.

## The quality of the voice

You cannot know the quality from the code. Use these tests:

- `videogen doctor --online` makes one short audio for each language.
- `videogen transcript` compares the voice with the script. It finds the names that the voice reads badly.
- Listen to the clips in `build/audio/` before you render the full video.
