# The sample of a voice

The engine `omnivoice` reads the text with a voice cloned from a sample. This reference has five parts:

1. What makes a good sample
2. The sentences to read, by language
3. How to record
4. The measures, and how to read them
5. When the voice is not good

The commands are in `docs/5-tts-engines.md` of the template: `videogen voice-prepare` makes a voice from recordings, and `videogen voice-compare` makes the file to listen, the measures and the verification.

## 1. What makes a good sample

The model copies the sample: its timbre, its vowels, its pauses and its pace come back in each clip. So the quality of the voice is the quality of the sample.

- **The sample decides the vowels.** Italian has open vowels and closed vowels (the e of *è* and of *sempre*; the o of *oggi* and of *non*). A sample with closed vowels only gives a voice with vowels that are all closed: the user hears "strette". A good sample has words with open vowels and words with closed vowels. In a test of 2026-11-27, the same voice cloned from a sample with closed vowels only read "È" almost closed; cloned from a sample with open vowels, it read it open, as the real voice does.
- **Two sentences are better than one.** One sentence can close vowels elsewhere. In the tests, the sentence that carried the open o's, used alone, made *fretta* come out closed. Two sentences together gave the best vowels: one for the open e's, one for the open o's.
- **The sample decides the pauses and the pace.** A recording with a pause at each punctuation mark gives a clone that is slow and stops many times in a sentence. `videogen voice-prepare` makes those pauses short (0.2 seconds): the clone then reads as a fluent speaker. With `--pauses keep`, the recording stays as it is.
- **The speed has a limit.** Up to `+20%` the model speaks faster. Above, it stops saying some words clearly (a list of letters, a short phrase). The engine keeps the model at `+20%` and makes each clip shorter in time. A dense list of single letters can lose words at `+20%` too: the third test sentence has one.
- **One clip says little.** The model chooses at random, and the seed moves one clip by about 100 Hz in its vowels. A voice is judged on several clips, and the user judges it by ear.
- **What does not work** (tested on 2026-11-27): an accent in the text to open a vowel; the phonemes in brackets (in Italian, the model reads the letters); the parameters of the generation (`guidance_scale`, the number of steps, `t_shift`, greedy); `instruct` (it knows only gender, age, pitch, whisper, English accents and Chinese dialects); a sample of 11.5 seconds with a pause of one second.
- **The form.** From 2 to 20 seconds (the authors of the model recommend 3 to 10). One or two sentences, in the language of the videos. `videogen voice-prepare` reads any audio format that ffmpeg reads.

## 2. The sentences to read, by language

The sentences have words with open vowels and words with closed vowels, and no name and no number. The user reads them; the clone never reads them in a comparison: the test sentences of the template are other sentences.

**Italian** (used on 2026-11-27; read both, in this order):

- A: "È spesso un effetto di fretta: oggi non c'è un metodo perfetto, e quello che resta è breve."
- B: "Oggi gli uomini non trovano il modo di misurare bene: resta il cuore del problema, e non c'è un metodo."

A alone gives good e's, and no open o. B alone closes the e's elsewhere: use B only together with A.

**English** (written for this skill, and not verified as the Italian ones were):

- A: "It is often a matter of haste: today there is no perfect method, and what remains is brief."
- B: "Today we cannot find a way to measure it well: the heart of the problem remains, and there is no method."

**Another language:** write two sentences with the same properties: common words, 15 to 20 words each, and words with open and with closed vowels when the language has them (as the o and the e of Italian). Say to the user that the sentences are not verified.

## 3. How to record

- A quiet room, and the microphone near the mouth (20 to 30 centimeters). The engine sets the level of the clips, not their quality.
- The natural pace of the person. The pauses can be long: `videogen voice-prepare` makes them short.
- One file for each sentence, or one file for both. The files are in their order.
- Any format that a telephone or a recorder makes: WAV, M4A, MP3, FLAC, OGG; stereo or mono.
- Each sentence from 2 to 10 seconds. All the sentences together stay under 20 seconds: when they do not, the user reads shorter sentences, or you make the voice with one sentence only.
- The user gives the paths of the files. The words are the sentences that you gave, as the user said them.

## 4. The measures, and how to read them

You cannot listen. The commands give you three things.

**The line of `videogen voice-prepare`** gives the pace of the person:

```
frase-A.wav: 9.7 s -> 8.4 s, the longest pause 0.5 s -> 0.2 s
Voice prova-A-B: 16.6 s, 2.29 words per second, 6.0 pauses per sentence.
```

**The table of `videogen voice-compare`** gives the pace of each voice at each speed, from its clips:

| voice | speed | words/s | pauses/sentence | longest pause |
|---|---|---|---|---|
| prova-A-B-letto | +0% | 2.08 | 3.2 | 0.6 s |
| prova-A-B | +0% | 2.42 | 2.0 | 0.5 s |
| prova-A-B | +20% | 2.77 | 1.2 | 0.3 s |
| prova-A-B | +32% | 3.11 | 1.0 | 0.2 s |

**The recognizer** says how many clips say their sentence, and what it heard in the others.

How to read them:

- **The clone reads at the pace of its sample.** The table above is one speaker of 2026-11-27: the sample as the person read it (`prova-A-B-letto`, with pauses up to 1.1 seconds) gave a clone at 2.08 words per second that stopped 3.2 times in a sentence. The same sample with the pauses cut gave 2.42 and 2.0. The numbers change from one person to another: compare the candidates with each other, never with these numbers.
- **More words per second and fewer pauses** mean a voice more fluent. A candidate that reads slower than the person (the line of `videogen voice-prepare`), and that stops more times, copies long pauses.
- **The user decides the speed by ear.** The words per second of each speed help the user: say them, with what the recognizer found at each speed.
- **The recognizer gives a first sign, not a verdict.** The third test sentence has a dense list of single letters, and the fourth has a name: the small recognizer hears those badly. When only those clips are different, and they are at `+0%`, start the command again on the candidates to verify, all in one command, with `--model medium` (it is slower, and it is better). The command makes the clips again, and they are the same clips (their seed comes from the text). It writes a second listening file: give it a name that says what it verifies with `--out`, for example `videos/voice-work/controllo-campioni.wav`, and tell the user that it has the same clips, so they do not need to listen to it. At `+20%` and above, do not start it again: it is the limit of the model (the next point).
- **What a clip that is still different means.** At `+0%`, it says that the sample is weak. One clip can be the seed of that clip (the engine gives a clip its seed from the text, so the same clip comes again): the user listens to it in the file. Several clips say that the sample is weak: part 5. At `+20%` and above, the model itself can lose words in a dense list of letters: it is a limit of the model at that speed, not of the sample. Say it to the user, who decides whether their videos have such lists.
- **The exit code.** `videogen voice-compare` exits with 1 when a clip is different. The listening file and the measures are good all the same. The exit code 2 is an error: its message says what to change.

## 5. When the voice is not good

The user listens to the file and says what is wrong. In each case, start again from the step named.

| What the user hears | What to do |
|---|---|
| The vowels are closed ("le e sono strette") | The sample has too few open vowels. Ask for both sentences (two), or for other sentences with more open vowels. In Italian, *è*, *fretta*, *effetto*, *oggi*, *cuore* are open. Step 1. |
| The voice is slow, or it stops at each comma | The pauses of the recordings are short already. Step 4 changes the speed. When the voice is still chopped, ask for a recording read as the person speaks. Step 1. |
| The voice is not the person's voice | The recording: a quiet room, the microphone near, a good microphone. Step 1. |
| The voice does not say some words | At `+0%`: one clip can be the seed, several clips say that the sample is weak. Part 4 says how to know (`--model medium`). At `+20%` and above, a dense list of letters is a limit of the model: the user decides the speed with that in mind. |
| The voice says a word of the sample in a strange way | The transcript must have the words exactly as the person said them. Verify the words of the recordings. |
| The speed is not the one that the user wants | `voices/<name>.toml` has one line, `rate = "+20%"`. Change it, then `videogen options` shows the new speed. Step 4. |

When the user records again, the new candidates replace the old ones: start Step 2 with the same work folder, and add `--force` to `videogen voice-prepare` only for the candidates that have the same name.
