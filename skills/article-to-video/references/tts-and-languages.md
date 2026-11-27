# Speech engines, voices and languages

Read this when the user selects an engine that is not edge-tts, wants a voice that is not in the menu, wants to record the voice-over, or wants a language that is not in the list. The technical details are in `docs/5-tts-engines.md` and `docs/6-languages.md` of the template.

## The engines

`videogen options` lists the engines. Each engine has a `status`: `available` is true when the engine is ready on this computer.

- **edge-tts** is the engine that `tools/setup.sh` installs. It is an online service, free, with no key. It is not an official API: it can stop without notice. It sends the text of the narration to the service of Microsoft. The menu of Step 1 in the skill says so to the user when the source is not public.
- **omnivoice** is an optional engine: a model on the computer, with a sample of a voice. Nothing leaves the computer: the text, the model and the sample stay on the disk. When `available` is false, the user can install it with `tools/setup-omnivoice.sh` (about 11 GB, and a GPU for a fast voice). Its voices are samples of voices, not names of a service:
  - `videogen options` shows them in `voices` of the engine, for each language, and at the end of `detail`.
  - A voice is `voices/<name>.wav` with its transcript in `voices/<name>.txt`, in the folder of the template or in the folder of the video. A voice can have its speed (`voices/<name>.toml`): `videogen new` writes it as `rate` in `video.toml`. The detail of the engine shows the speed of each voice.
  - When the user selects this engine, use one of its voices for the video: the first one, unless the user asks for another. A voice of edge-tts is not valid for omnivoice.
  - When the user wants their own voice and there is no sample: the user must record one or two sentences (2 to 20 seconds) and give you the words that they say. Give the user a sentence to read: it must have open vowels and closed vowels, as "È spesso un effetto di fretta: oggi non c'è un metodo perfetto, e quello che resta è breve." in Italian. Put the two files in the folder `voices`. That needs the user, so ask before the end of Step 1.
  - The model copies the pauses, the speed and the vowels of the sample: a sample with closed vowels only gives a voice with vowels that are too closed. The license of the model is CC-BY-NC: it permits a use that is not commercial.
- **An engine with an API key** is not in the template. To add one, the template needs code: the procedure is in `docs/5-tts-engines.md`. If the user wants one, stop after the menu and explain what is necessary.
- **My own recordings**: the user records one audio file for each beat. Continue in this way:
  1. Make the video with `videogen tts` and `videogen script --root <folder>`. The user reads the script from `script.md`: it has the text of each beat and its ID.
  2. The user puts the files in one folder, with the name `<scene>_<beat>.wav` (for example `ch02_c8.wav`).
  3. Start `videogen voice-adopt <folder> --root <folder of the video>`.
  4. Start Step 5 again: the scenes follow the new length of the clips. The word cues (`hold_until`) work only on the beats with the synthesized voice: for a recorded beat, `hold_until` falls back to the middle of the clip. Use the time of the clip (`self.dur`) in that case.

## Voices

- `videogen options --online` gives the full list of the voices of edge-tts for each language.
- The first voice of a language in `videogen/langs.py` is the default.
- To change the voice after the project started: change `voice` in `video.toml`, then start `videogen tts --force`: the clips change, and the scenes follow the new length.
- With omnivoice, a token of the text keeps its written form in the subtitles (`3,61`, `96°`), and a cue phrase (`hold_until`) finds it as it is written. With edge-tts, a number can make the service return its words in a different form: then the subtitles of that beat show the words of the service, without punctuation. When this happens, write the numbers of that beat in words.

## Languages

The template has English and Italian. A language needs more than a voice: the format of the numbers, the words for the line breaks of the subtitles, and the interface strings of `script.md`. To add a language, add one entry in `LANGS` in `videogen/langs.py`: the procedure is in `docs/6-languages.md`. Then start `videogen doctor` and continue. OmniVoice reads 646 languages, but its numbers in words operate in Italian and in English only.
