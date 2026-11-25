# Speech engines, voices and languages

Read this when the user selects an engine that is not edge-tts, wants a voice that is not in the menu, wants to record the voice-over, or wants a language that is not in the list. The technical details are in `docs/5-tts-engines.md` and `docs/6-languages.md` of the template.

## The engines

`videogen options` lists the engines. Each engine has a `status`: `available` is true when the engine is ready on this computer.

- **edge-tts** is the only engine that the template installs. It is an online service, free, with no key. It is not an official API: it can stop without notice. It sends the text of the narration to the service of Microsoft. The menu of Step 1 in the skill says so to the user when the source is not public.
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

## Languages

The template has English and Italian. A language needs more than a voice: the format of the numbers, the words for the line breaks of the subtitles, and the interface strings of `script.md`. To add a language, add one entry in `LANGS` in `videogen/langs.py`: the procedure is in `docs/6-languages.md`. Then start `videogen doctor` and continue.
