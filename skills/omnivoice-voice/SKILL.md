---
name: omnivoice-voice
description: "Install the speech engine OmniVoice of the AIVideoGenerator template, and prepare a voice cloned from a sample, for example the voice of the user. Use this skill when the user asks to install or set up OmniVoice, to use their own voice in a video, to clone a voice from a recording, to prepare or improve a sample of a voice, to change the speed of a voice, or when the skill article-to-video selects the engine omnivoice and the voice that the user wants does not exist yet. The skill works with the user: a recording, then two choices by ear."
---

# OmniVoice voice

Install the speech engine OmniVoice and make a voice for it: a voice cloned from a sample, for example the voice of the user. The work has six steps. Each step ends when its condition is true.

You cannot listen. This skill is a dialogue with the user, in three moments: they record the sample, they choose the sample by ear, they choose the speed by ear. Each step that needs the user ends with one clear request, and the work continues when the user answers. On everything else, you decide from the output of the commands.

## How the engine works

Read this before Step 0. It explains the reasons of the rules below.

- **The engine copies a sample.** `omnivoice` is a model on the computer (k2-fsa/OmniVoice): it needs no voice from a service. It reads the text with the voice, the vowels, the pauses and the pace of a sample of 2 to 20 seconds. Nothing leaves the computer. The install is about 11 GB, and a GPU makes the voice fast.
- **A voice is two files, and an optional third.** `voices/<name>.wav` is the sample and `voices/<name>.txt` its words. When the voice has a speed, `voices/<name>.toml` has it (`rate = "+32%"`), and `videogen new` writes that speed in the `video.toml` of a new video.
- **The voices are in two folders.** The folder `voices` of the template has the voices of all the videos. A video project (a folder with a `video.toml`, made by `videogen new`) can have its own folder `voices`: for that project, it comes first. `videogen options` lists only the voices of the template.
- **A video without `voice` uses the first voice of its folders**: those of its project, then those of the template. For the template, `videogen options` lists the voices in that order. It is the order of the file names, and it can surprise: `voce-A` comes before `voce`.
- **The sample decides the voice.** Its vowels (open or closed), its pauses and its pace come back in each clip. `references/sample.md` says what makes a good sample, and what to change when the voice is not good.
- **The candidates stay in a work folder.** `videos/voice-work` receives the candidates and the listening files. The folder `voices` of the template, or that of a project, receives one voice only: the one that the user chose, with its speed.

## Where to start

- A new voice, and the engine can be missing: Step 0.
- The engine is installed: Step 1.
- The user has the recordings and their words: Step 2.
- The user wants another speed for a voice that exists: Step 4, with that voice in place of the candidate. Then write the speed in `voices/<name>.toml` (one line, `rate = "+20%"`), and verify it as Step 4 says.

## Step 0 — The engine

`videogen` operates only if the tools are installed. The tools are in the folder `.tools` of the template (AIVideoGenerator): `tools/setup.sh` puts them there. Thus you need the folder of the template.

Find the command in this order. Stop at the first command that prints a report:

1. `videogen doctor`: the command is on the `PATH`.
2. `tools/videogen doctor`: the current directory is the folder of the template.
3. `$AIVIDEOGEN_HOME/tools/videogen doctor`: the variable `AIVIDEOGEN_HOME` gives the folder of the template.
4. `~/project/AIVideoGenerator/tools/videogen doctor`: the usual folder.

Then use that command in each step below, in place of `videogen`, and keep the folder of the template for the installer.

When no command operates, or `doctor` shows MISSING lines, ask with one menu: "The tools of AIVideoGenerator are not complete. Install them now?" Options: "Install now (Recommended)" and "Stop". For "Install now", start `tools/setup.sh` in the folder of the template (5 to 15 minutes), then `videogen doctor` again.

Then read `videogen options`. In `engines`, find the engine with `id` `omnivoice`:

- **`available` is true:** the engine is ready.
- **`available` is false:** ask with one menu: "Install the speech engine OmniVoice now?" Options: "Install now (Recommended)", and "Stop". The description of "Install now" gives the facts: about 11 GB of download; from ten minutes to one hour; a GPU makes the voice fast, and on the processor only the model is slow; the license CC-BY-NC permits a use that is not commercial; nothing leaves the computer. For "Install now", start `tools/setup-omnivoice.sh` in the folder of the template. The install can last more than the limit of one command of your shell: start it in the background and wait for its end. Then start `videogen doctor` and `videogen options` again.

Condition: `available` is true. When the user selects "Stop", go to Step 5.

When the request was the installation only, ask with one menu: "The engine is ready. Do you want to prepare a voice now?" For "no", go to Step 5.

## Step 1 — The recording

Read `references/sample.md`: part 2 has the sentences to read, and part 3 says how to record.

**When the user gives recordings and their words**, keep their order and their words, and go to Step 2.

Otherwise ask with one menu, in the language of the conversation:

1. **Language of the voice.** The language of the videos. One option for each language of `videogen options` (field `languages`).
2. **Name of the voice.** One or two suggestions that are not names of voices that exist, for example `my-voice`, or its equivalent in the language of the user. The user can write another name. The description names the voices of the template that exist (`videogen options`, in the detail of the engine `omnivoice`), and says which one a video of the template uses today when it has no `voice`: the first of that list.
3. **Labels in the listening files.** "Without labels (Recommended)": "The files stay offline. You follow the voices by their order, which is always the same." "With labels": "In every listening file, before each clip, a voice of edge-tts says the name of the voice and its speed. That text goes to the service of Microsoft. Nothing else leaves the computer."

Then give the user what they need to record:

- the sentences to read, each on a line of its own;
- how to record (`references/sample.md`, part 3): any format, the natural pace, one file for each sentence or one file for both;
- where to put the files: a folder of their choice. They tell you the paths.

End your turn with that request: the user records when they can.

Condition: you have the recordings and their words, in their order.

## Step 2 — The candidates

A **candidate** is a voice with a provisional name, made to be compared with the other candidates.

1. The **work folder** is `videos/voice-work` (in the current directory), or a folder that the user gives. The commands make its folder `voices`.
2. The letters A, B, C, ... name the recordings, in their order. Make the candidates with `videogen voice-prepare`:
   - all the recordings together: `<name>-A-B` (with three recordings, `<name>-A-B-C`; with one, `<name>-A`);
   - with two or more recordings, each recording alone: `<name>-A`, `<name>-B`.

   ```bash
   videogen voice-prepare --root videos/voice-work <name>-A-B <recording A> <recording B> --text "<sentence A> <sentence B>"
   videogen voice-prepare --root videos/voice-work <name>-A <recording A> --text "<sentence A>"
   ```

   The command reads any audio format, makes the long pauses short (a pause over 0.26 seconds becomes 0.2 seconds), and prints the pace of the person: keep that line. When it refuses a candidate (outside 2 to 20 seconds: the message says the seconds), leave that candidate out. When it refuses the candidate with all the recordings, ask the user for shorter sentences: that is the candidate that you recommend.
3. Compare the candidates:

   ```bash
   videogen voice-compare --root videos/voice-work --language <code> [--labels] <the candidates>
   ```

   Each candidate reads four test sentences of the template. The command writes one **listening file** (`voices/confronto/<date and time>-<voices>.wav` in the work folder: its name has the second, so two comparisons never write on the same file), prints the measures of each candidate, and verifies each clip with the offline recognizer. Read its output as `references/sample.md` says (part 4). When a clip is different, that part says what to do: for a list of letters or a name, start the command again with `--model medium`, in one command for the candidates to verify.
4. Tell the user, in the language of the conversation:
   - the path of the listening file, and the order of the candidates in it;
   - the four sentences (the command prints them);
   - one line for each candidate: its words per second, its pauses per sentence, and what the recognizer found;
   - what you see in the measures. For example: "The candidate X reads 15 per cent slower than Y, and stops more times in a sentence."

Condition: the listening file exists, and the user has all of this.

## Step 3 — The sample

With two or more candidates, ask with one menu: "Which sample do you want for the voice?" One option for each candidate, and its measures in the description. Put first the candidate with all the recordings, with "(Recommended)": two sentences together gave the best vowels in the tests of 2026-11-27, and you cannot hear, so you recommend by that result. The last option is "None: I record again". For "None", Step 1 starts again with the advice of part 5 of `references/sample.md`.

With one candidate only, there is no menu. Say that the file has that one voice, and that Step 4 changes its speed. When the user says that the voice is not good, Step 1 starts again in the same way.

Condition: the user chose a candidate, or accepted the only one.

## Step 4 — The speed

1. Make the second listening file:

   ```bash
   videogen voice-compare --root videos/voice-work --language <code> --rates +0%,+20%,+32% [--labels] <the candidate>
   ```

   Read its output as in Step 2 (`references/sample.md`, part 4).
2. Tell the user the path of the file, the words per second of each speed, and what the recognizer found at each speed. When a speed loses words in a sentence, say it before the user chooses.
3. Ask with one menu: "Which speed do you want?" Options: `+0%`, `+20%`, `+32%`. The user can write another speed: then make the file with that speed too, before the user decides.
4. Make the final voice, in the folder `voices` of the template:

   ```bash
   videogen voice-prepare <name> <the recordings of the candidate> --text "<their words>" --rate "<the speed>"
   ```

   Add `--root <project>` when the user wants the voice for one project only. When a voice with that name is there, the command stops: ask whether to replace it (`--force`) or to change the name.
5. Verify the voice:
   - In the folder of the template: `videogen options` shows the voice in the detail of the engine `omnivoice`, with its speed.
   - In the folder of a project: `videogen options` does not list it. The folder `voices` of the project has `<name>.wav`, `<name>.txt` and `<name>.toml`, and the `.toml` file has the speed.

Up to `+20%` the model speaks faster. Above, the engine keeps the model at `+20%` and makes each clip shorter in time: made to speak faster, the model stops saying some words clearly. The user can change the speed of the voice later, in `voices/<name>.toml`.

Condition: the voice is verified.

## Step 5 — The report

The report ends the work, in the language of the conversation. Tell the user:

1. **The voice.** Its name, its folder, its speed and the seconds of its sample. What the verification of Step 4 says.
2. **What was verified.** The recognizer on the four sentences, for each candidate and each speed; the measures. And that you cannot listen: the user chose by ear.
3. **How to use the voice.**
   - In the folder `voices` of the template: `videogen new <folder> --engine omnivoice --voice <name>` starts at the speed of the voice. With the skill `article-to-video`: the engine `omnivoice` and that voice.
   - In the folder `voices` of a project: write `voice = "<name>"` and `rate = "<the speed>"` in the `video.toml` of that project. To use the voice in another video, copy its three files into the folder `voices` of that video, or of the template.
4. **The default voice.** A video without `voice` uses the first voice of its folders: those of its project, then those of the template. For a video of the template, say which voice `videogen options` lists first, and that the name of the files decides the order.
5. **The work folder.** `videos/voice-work` has the candidates and the listening files. Ask with one menu: "Delete the work folder now?" Delete it only when the user says so, and when the final voice is not in that folder.
6. **The decisions** that you took after the menus. For example a sample that the command refused.

When the engine is not installed (the user stopped Step 0), the report says what is missing, and how to start again.

## Rules

- **A sample of a voice is personal data.** It stays in a folder `voices` or in the work folder, out of git. It goes in no commit, no test, no guide and no message to a service.
- **The consent of the person.** Clone the voice of a person only with their consent. When the user has not the consent of the person, stop and say why.
- **The network.** The only step that uses it is `--labels`, in every listening file. It sends only the name of the voice and its speed to `edge-tts`. The user decides in Step 1.
- **The user decides by ear.** Only the user can hear the timbre and the vowels. You decide on the recognizer and on the measures.
- **A voice that exists stays.** `--force` replaces a voice only when the user asks to replace a voice by its name.
