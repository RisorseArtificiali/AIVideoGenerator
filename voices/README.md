# Voices for OmniVoice

This folder has the voices of the speech engine `omnivoice`: a local model that reads the text with a voice cloned from a sample. The installer of the engine is `tools/setup-omnivoice.sh`. The details are in [`docs/5-tts-engines.md`](docs/5-tts-engines.md).

A voice is two files with the same name, and an optional third file with its speed:

| File | Content |
|---|---|
| `voices/<name>.wav` | a sample of the voice, from 2 to 20 seconds. WAV, FLAC, OGG or MP3 |
| `voices/<name>.txt` | the words of the sample, exactly as the voice says them |
| `voices/<name>.toml` | optional: the speed of the voice, for example `rate = "+32%"` |

```text
voices/elsa.wav
voices/elsa.txt
voices/elsa.toml     (optional)
```

To record a good sample:

1. Read one or two sentences, in the language of the video. The model copies the speed and the pauses: a long pause in the sample gives long pauses in every clip. `videogen voice-prepare` makes the long pauses of a recording short.
2. Read words with open vowels and words with closed vowels. The model copies the vowels of the sample: a sample with closed vowels only gives a voice with vowels that are too closed. In Italian, *è*, *fretta*, *effetto*, *oggi*, *cuore* are open, and *sempre*, *perché*, *non*, *dopo* are closed. For example: "È spesso un effetto di fretta: oggi non c'è un metodo perfetto, e quello che resta è breve." When you have two sentences, read both: one sentence alone can close vowels elsewhere.
3. Use a quiet room and a good microphone. The engine changes the level of the audio, not its quality.
4. Write the transcript with the normal punctuation. The engine adds the final period, if it is not there.

## From your recordings to a voice

With an agent, ask the skill `omnivoice-voice`: it installs the engine, gives you the sentences to read, and asks you to choose the sample and the speed by ear. These are its two commands, for a use without an agent:

```bash
videogen voice-prepare my-voice frase-a.wav frase-b.wav --text "<the words of the two recordings>" --rate "+20%"
videogen voice-compare my-voice --language it --rates +0%,+20%,+32%
```

The first command makes the voice from your recordings, in any audio format, with the long pauses short. The second command makes one file to listen, with the measures of the pace of each speed. To change the speed of the voice later, change the line of `voices/my-voice.toml`.

Then use the name of the voice in `video.toml`:

```toml
engine = "omnivoice"
voice = "elsa"
```

**The speed.** When the voice has its `.toml` file, `videogen new` writes that speed as `rate` in the `video.toml` of the new video. To change the speed of one video, change `rate` in its `video.toml`. To change it for the next videos, change the `.toml` file of the voice. `videogen doctor` shows the speed of each voice.

Up to `+20%` the model speaks faster. Above `+20%`, the engine keeps the model at `+20%` and makes the clips shorter in time, with the same pitch: made to speak faster than that, the model stops saying some words clearly.

## Rules of this folder

- **A sample of a voice is personal data.** Git ignores this folder, except this README. Do not put a sample in git, and do not give a sample to others without the consent of the person whose voice it is.
- **The samples are only on your computer.** A clone of the repository has no voice: keep a copy of your samples with your backups, to use them again on another computer.
- `videogen new` does not copy this folder. A video project can have its own folder `voices/`: it comes before this one.
- The sample must be in the language of the video.
- When you change a sample, `videogen tts` makes the clips of that voice again.
