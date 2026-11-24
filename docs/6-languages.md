# Languages

The language of the video is a decision of the user. It is independent of the language of the source. The narration, the text on the screen, the subtitles and the voice use the language of the video.

The template has English (`en`) and Italian (`it`).

## What a language changes

| Element | Source |
|---|---|
| The voices of the engines | `Language.voices` |
| The format of the numbers: `38.3` or `38,3` | `Language.decimal_separator`, used by `self.lang.number()` and `self.lang.percent()` |
| The line breaks of the subtitles | `Language.function_words` |
| How the voice reads some names | `Language.spoken_rules` |
| The interface strings of `script.md` and of the chapters | `Language.text` |
| The language that the offline recognizer hears | `Language.code` |

## How to add a language

1. Open `videogen/langs.py`. Add an entry in `LANGS`:

   ```python
   "de": Language(
       code="de",
       name="Deutsch",
       voices={"edge-tts": ("de-DE-KatjaNeural", "de-DE-ConradNeural")},
       function_words=frozenset("der die das und oder ...".split()),
       decimal_separator=",",
       text={**ENGLISH_TEXT, "opening": "Einführung", ...},
   ),
   ```

2. For the voices, read the list of the service: `videogen options --online`.

3. For `text`, translate the strings of `ENGLISH_TEXT`. The strings are for `script.md` and for the first beats of a new project.

4. Add the language to the choices of `videogen new --language` in the documentation.

5. Verify: `videogen doctor --online` makes one audio with the new language. `videogen selftest` verifies that the engine operates.

## The text of the narration

The agent (or you) writes the narration in the language of the video. The translation of a source in a different language is also an explanation: use short sentences for the ear. Keep the technical names in the language of the viewer when the viewer knows them. For the other names, say the meaning and show the name on the screen.
