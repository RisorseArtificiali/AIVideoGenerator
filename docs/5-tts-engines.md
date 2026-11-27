# Speech engines

A speech engine changes one line of text to audio, and gives the time of each word. `videogen tts` uses the engine of `video.toml`.

| Engine | Where the voice is made | Install | The text of the narration |
|---|---|---|---|
| `edge-tts` | an online service of Microsoft | `tools/setup.sh` | goes to the servers of Microsoft |
| `omnivoice` | a model on your computer, with a sample of a voice | `tools/setup-omnivoice.sh` | stays on your computer |
| your own recordings | your microphone | none | stays on your computer |

## The engine in the template: edge-tts

- It uses the Read Aloud service of Microsoft Edge. It is online, free, and needs no key.
- It is not an official API. The service can change or stop without notice.
- The text of the narration goes to the servers of Microsoft.
- The voices of a language are in `videogen/langs.py`. For the full list: `videogen options --online`.

## OmniVoice: a local model with a sample of a voice

`omnivoice` is a model of speech that operates on your computer (k2-fsa/OmniVoice: 0.6 billion parameters, 646 languages). It does not need a list of voices: it copies the voice of a sample. Thus a video can have your voice.

Nothing leaves the computer. The engine reads the text, the model and the sample on the disk, and does not use the network.

### Install

```bash
tools/setup.sh               # first: the tools of the template
tools/setup-omnivoice.sh     # then: the engine omnivoice
```

The install downloads approximately 11 GB, and puts them in the folder of the tools:

```
AIVideoGenerator/
└── .tools/
    ├── venv-omnivoice/     the Python environment of the model, with PyTorch (about 7 GB)
    ├── models/omnivoice/   the model of speech (about 3 GB)
    └── models/mms-fa/      the model that gives the time of each word (about 1.2 GB)
```

It also installs the package `num2words` in the environment of the tools (the extra `omnivoice` of `pyproject.toml`).

- The engine is optional. `videogen doctor` shows it on a line `OPTIONAL`: when it is not installed, it is not a problem, and the other videos do not need it.
- Start `tools/setup-omnivoice.sh` again to repair an incomplete install. The options `--environment` and `--models` install only one part.
- The model needs a GPU for a fast voice. With an NVIDIA GPU, `videogen tts` makes a clip of 10 seconds in approximately 3 seconds, and uses 6 GB of memory on the GPU. On the processor only, the model is slow: it takes approximately 7 times the length of the audio on a computer with 32 threads. An hour of narration then takes more than 7 hours.

### A voice: a sample and its transcript

A voice is two files with the same name, in a folder `voices`, and an optional third file with its speed:

| File | Content |
|---|---|
| `voices/<name>.wav` | a sample of the voice, from 2 to 20 seconds. WAV, FLAC, OGG or MP3, at any sample rate |
| `voices/<name>.txt` | the words of the sample, exactly as the voice says them |
| `voices/<name>.toml` | optional: the speed of the voice, for example `rate = "+32%"` |

```text
AIVideoGenerator/
├── voices/
│   ├── elsa.wav
│   ├── elsa.txt
│   └── elsa.toml      (optional)
└── videos/my-video/
    └── voices/
        ├── narrator.flac
        └── narrator.txt
```

- The folder `voices` of the template has the voices of all the videos. A video project can have its own folder `voices`: it comes first.
- `videogen options` shows the voices of the engine in `languages[].voices.omnivoice` and in the detail of the engine, with their speed.
- To make a voice from your recordings: `videogen voice-prepare` (next section), or the skill `omnivoice-voice` with an agent.
- To use a voice: `engine = "omnivoice"` and `voice = "<name>"` in `video.toml`, or `videogen new <folder> --engine omnivoice --voice <name>`. Without a voice, videogen uses the first voice of the folders.
- `voice` can also be the path of an audio file, relative to the folder of the video. The transcript is in the text file that has the same name.
- **The speed of a voice.** When the voice has its `.toml` file, `videogen new` writes that speed as `rate` in the `video.toml` of the new video. Change `rate` in `video.toml` for one video; change the `.toml` file for the next videos. The speed of the voice stays out of git, as its sample.

To record a good sample:

1. Read one or two sentences, in the language of the video. The model copies the speed and the pauses: a long pause in the sample gives long pauses in each clip. `videogen voice-prepare` makes the long pauses of a recording short.
2. Read words with open vowels and words with closed vowels. The model copies the vowels of the sample: a sample with closed vowels only gives a voice with vowels that are too closed. In Italian, *è*, *fretta*, *effetto*, *oggi*, *cuore* are open, and *sempre*, *perché*, *non*, *dopo* are closed. For example: "È spesso un effetto di fretta: oggi non c'è un metodo perfetto, e quello che resta è breve." When you have two sentences, read both: one sentence alone can close vowels elsewhere.
3. Use a quiet room and a good microphone. The engine changes the level of the audio, not its quality.
4. Write the transcript with the normal punctuation.

### Prepare a voice and compare the candidates

With an agent, the skill `omnivoice-voice` does all of this with you: it installs the engine, gives you the sentences to read, and asks you to choose the sample and the speed by ear. Without an agent, these are the two commands.

**`videogen voice-prepare` makes a voice from your recordings.** It reads any audio format (M4A too), and makes the long pauses of the recordings short: a pause over 0.26 seconds becomes 0.2 seconds. It writes the files of the voice:

```bash
videogen voice-prepare my-voice recording-a.wav recording-b.wav --text "<the words of the two recordings>" --rate "+20%"
```

- Without `--root`, the voice goes to the folder `voices` of the template. With `--root <project>`, to the folder `voices` of that video project.
- `--rate` is optional: it writes `voices/<name>.toml`. `--pauses keep` leaves the recordings as they are.
- The sample must be from 2 to 20 seconds. A voice that has that name is replaced only with `--force`.
- The command prints the seconds of each recording before and after, the pace of the person (the words per second), and the voice that videogen uses when a video has no `voice`.

**`videogen voice-compare` makes the voices read test sentences.** You obtain one file to listen, the measures of the pace of each voice, and the verification of the recognizer on each clip:

```bash
videogen voice-compare my-voice-A my-voice-B --language it
videogen voice-compare my-voice-A --language it --rates +0%,+20%,+32%
```

- The file to listen has, for each test sentence, one clip for each voice. It is in `voices/confronto/`, or in the file of `--out`. With `--root <project>`, the voices of that project come before those of the template.
- The test sentences are in `videogen/templates/voice-test/<language>.txt`: four sentences with what was weak with the model (in Italian: a sentence that starts with "È", numbers, a list of letters, a name). `--text <file>` gives other sentences, one per line.
- Without `--rates`, each voice reads at its own speed.
- The command prints, for each voice and each speed: the words per second, the pauses per sentence and the longest pause. Then the recognizer: how many clips say their sentence, and what it heard in the others. The exit code is 1 when a clip is different.
- `--model medium` is slower and better: use it when the small recognizer does not understand a list of letters or a name.
- `--labels` puts the name of the voice and its speed before each clip, read by `edge-tts`. It is the only step that uses the network, and it sends only that text.

### What the engine does

- **Numbers.** The model does not read digits correctly: `0,042` becomes "zero zero quarantadue". The engine writes the numbers in words before it sends the text: cardinals, ordinals, decimals, thousands, percentages and currency, in Italian and in English. The subtitles show the text as it is written (`0,042`, `96°`, `5.000`), and the scenes find these tokens with `hold_until`.
- **Pauses and level.** The model copies the pauses and the level of the sample. The engine sets each clip at the level of the clips of `edge-tts`, keeps 0.15 seconds of silence before the first word and after the last one, and makes a pause longer than 0.7 seconds 0.5 seconds long. A breath in a pause stays.
- **The same clip again.** The model chooses at random. The engine gives it a seed that comes from the text, the voice and the rate. Thus a clip made again is the same clip.
- **The time of the words.** The model gives the audio only. A second model, MMS_FA, finds the time of each word on the audio. The time of the words of the subtitles and of the cues comes 0.06 seconds before their sound.
- **The speed.** `rate` in `video.toml` is the speed of the voice: `+10%` reads 1.1 times faster. Up to `+20%` the model speaks faster. Above `+20%`, the model stays at `+20%` and the engine makes each clip shorter in time, with the same pitch: made to speak faster than that, the model stops saying some words clearly (a list of letters, a short phrase). A voice can have its own speed (`voices/<name>.toml`), and a new video starts with it.
- **A process of its own.** The model needs PyTorch, and the tools of the template do not need it. Thus the model operates in the environment `venv-omnivoice`, in a process that `videogen tts` starts at the first clip and stops at the end. `videogen/tts/omnivoice_worker.py` is that process.

### Rules

- **A sample of a voice is personal data.** The file `.gitignore` keeps the folder `voices` out of git, except its README. Do not put a sample in git. Do not use the voice of a person without their consent.
- **The license of the model is CC-BY-NC**: it permits a use that is not commercial. The code is Apache-2.0. Read the license of the model before a commercial use.
- **The same language.** The sample must be in the language of the video. The numbers in words operate in Italian and in English only: in the other languages, the digits stay in the text.
- **Another device.** The model operates on the first NVIDIA GPU, or on the GPU of an Apple system, or on the processor. To select a device, set `OMNIVOICE_DEVICE` before `videogen tts`, for example `cuda:1`, `mps` or `cpu`.

### The problems

- "OmniVoice has no voice '…'": there is no sample with that name. The error lists the voices of the folders `voices`. A voice of `edge-tts` (as `it-IT-ElsaNeural`) is not a voice of `omnivoice`.
- "The sample of the voice lasts … seconds": use a sample from 2 to 20 seconds.
- "the worker of OmniVoice stopped" or "is not ready": the model does not load. Start the worker by hand to read the error: `.tools/venv-omnivoice/bin/python -I videogen/tts/omnivoice_worker.py --model .tools/models/omnivoice --aligner .tools/models/mms-fa --check`. If the memory of the GPU is in use by other programs, stop them.
- "The model gave no voice for this text": the model returned silence. Change the text a little, or change the sample.

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

    def voices(self, language, root=None):
        return language.voices.get(self.id, ())

    def synthesize(self, text, voice, rate) -> Clip:
        key = os.environ["MY_SERVICE_KEY"]
        # 1. Send the text to the service and get the audio in a file.
        # 2. Change the audio: samples = decode_audio(path_to_the_audio_file)
        # 3. Get the time of the words, if the service gives it: [(start, duration, word), ...]
        return Clip(samples, words)
```

Then:

1. Add an instance of the class to `ENGINES`, at the end of `videogen/tts/__init__.py`.
2. Add the voices of the engine for each language in `videogen/langs.py`: `voices={"edge-tts": (...), "my-service": (...)}`.
3. Add the key to `.env`.

`videogen options` shows the new engine with its status. The skill shows it in the menu.

### The parts of an engine that change for some engines

`Engine` has more attributes and methods. Their default is correct for most engines:

| Attribute or method | When to change it |
|---|---|
| `optional = True` | `tools/setup.sh` does not install the engine. Then `videogen doctor` shows the engine on a line `OPTIONAL`, and does not count it as a problem. |
| `voices_help` | a sentence that says how to give the engine a voice, when its voices are not in `videogen/langs.py`. `videogen options` shows it in `voices_help`. |
| `voices(language, root)` | the voices are not in `videogen/langs.py`, or they can be in the folder `root` of the video project. |
| `configure(root, language)` | the engine needs the folder of the video project or its language when it reads a text. `videogen tts` calls this method one time, before the first clip. |
| `signature(voice, rate)` | the voice depends on a file that can change, as a sample. The method returns a short text that identifies the file: `videogen tts` adds it to the fingerprint of each clip, and makes the clips again when the file changes. |
| `default_rate(voice, root)` | a voice of the engine has its own speed. The method returns it in the form of `rate` (`"+32%"`), or an empty string: `videogen new` writes it in the `video.toml` of the new video. |

### An engine with a local model on the GPU

The class is the same. These are the differences:

- `needs_env` is empty.
- `status()` verifies that the model is on the disk, and that the GPU operates.
- Load the model one time, before the first call of `synthesize`. Keep the model in an attribute of the engine.
- `videogen tts` calls `synthesize` from some threads at the same time. If the model operates on one thread only, protect it with a lock (`threading.Lock`).
- Do not import the libraries of the model at the start of the file: the commands of videogen that do not need the model must operate when the libraries are not installed. Import them in `status()` and in `synthesize()`.
- Give one entry in `words` for each token of `text` (the text cut on the spaces). Then the subtitles show the text as it is written. `omnivoice.py` is the example.

`decode_audio(path)` changes any audio file to the form that `Clip` needs: mono (the mean of its channels), float32, at 48000 Hz. `videogen voice-adopt` uses it on your recordings.

## The quality of the voice

You cannot know the quality from the code. Use these tests:

- `videogen doctor --online` makes one short audio for each language with `edge-tts`.
- `videogen transcript` compares the voice with the script. It finds the names that the voice reads badly. The recognizer writes a number as digits or as words: `transcript` accepts the two forms.
- Listen to the clips in `build/audio/` before you render the full video.
