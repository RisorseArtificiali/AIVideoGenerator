# Review: the corrections and the final tests

Read this at Step 5 and Step 6 of the skill.

## What `videogen check` reports

| Report | Meaning | Correction |
|---|---|---|
| `[layout] ... out of frame` | A line of text is outside the frame, or touches the border | Move the object, or make the text smaller |
| `[layout] ... overlap` | Two lines of text are one on the other | Move one of them, or delete one |
| `[cue]` | The phrase of `hold_until` is not in the clip | Copy the phrase from the text of the beat. If a rule in `spoken_rules.py` changes the words, write the changed words |
| `[pace]` | The visuals of the beat are longer than the voice clip | Make the animations shorter, or divide the visuals between two beats. The video stays correct: the voice of the next beat starts later |

A false positive is possible: two lines of text with large letters can touch. Verify on the contact sheet, then change the position a little.

## What to look for on the contact sheets

Open every sheet with the Read tool. For each frame, compare the frame with the narration of the beat:

- Is each object completely in the frame, far from the border?
- Is a line, an arrow or a box on text?
- Does the frame agree with what the voice says at that moment?
- Are the small labels readable? At 480p the small text is difficult: verify the size in the 1080p film when in doubt.
- Is the title of the chapter free (top left)?

Correct, then start `check`, `render --quality l` and `sheet` again.

## The tests of the voice

- `videogen transcript`: the offline recognizer transcribes the clips. A clip with a similarity below 0.9 is different from the script: usually a name that the voice reads badly. Read the transcription to know what the voice says.
- `videogen sync`: after the assembly, it verifies that each clip starts when its scene put it on the time line.

## The report to the user

The user must know what is approximate and what was not verified:

- The pronunciation is verified with a recognizer, not with ears. The user must hear the voice and the rhythm.
- The numbers read from figures are approximate. The video must show a note on the charts.
- If the source contradicts itself, say it in the report, and say which version the video uses.
