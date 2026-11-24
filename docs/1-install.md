# Install the tools

The tools are the Python environment of the template and a portable TeX Live. They are in one folder: the cache. You do not need root access.

## Procedure

1. Clone this repository:

   ```bash
   git clone https://github.com/RisorseArtificiali/AIVideoGenerator.git
   cd AIVideoGenerator
   ```

2. Make sure that `ffmpeg`, `curl`, `perl` and `tar` are installed. On Fedora:

   ```bash
   sudo dnf install ffmpeg curl perl tar
   ```

3. Start the install:

   ```bash
   tools/setup.sh
   ```

   The install downloads approximately 800 MB and needs 5 to 15 minutes. At the end, the command `videogen doctor` verifies the tools.

4. Verify the tools and the voice service:

   ```bash
   videogen doctor --online
   ```

   `--online` sends one short sentence to the speech service for each language.

## The cache folder

- Default folder: `~/.cache/aivideogen`.
- To use a different folder, set `AIVIDEOGEN_CACHE` before you start `tools/setup.sh`. Use the same value when you use `videogen`.

WARNING: Some programs delete the content of `~/.cache`. If this occurs, the tools are gone. Start `tools/setup.sh` again, or set `AIVIDEOGEN_CACHE` to a folder that no program deletes.

## The location of the command

The install puts `videogen` in `~/.cache/aivideogen/venv/bin/`. This folder is usually not on the `PATH`. Three solutions:

- Add the folder to the `PATH` in the file of your shell.
- Use the full path: `~/.cache/aivideogen/venv/bin/videogen`.
- Activate the environment when you work on a video: `source ~/.cache/aivideogen/venv/bin/activate`.

## What `videogen doctor` verifies

| Item | Necessary | How to correct a problem |
|---|---|---|
| Python environment in the cache | yes | `tools/setup.sh` |
| packages `manim` and `edge_tts` | yes | `tools/setup.sh` |
| packages `faster_whisper` and `trafilatura` | no | install the extras `qa` and `extract` |
| `ffmpeg` and `ffprobe` | yes | the package manager of your system |
| `magick` (ImageMagick) | no | necessary for `videogen sheet` |
| TeX Live, and the LaTeX compilation | yes | `tools/setup.sh` |
| speech engine `edge-tts` | yes | the package `edge-tts` |

`videogen doctor --fix` starts `tools/setup.sh` when a necessary item is missing.

## Update

1. Go to the folder of the repository. Get the new version: `git pull`.
2. Start `tools/setup.sh` again. It updates the Python environment and keeps TeX Live.
3. Start `videogen selftest` to make sure that the pipeline operates on your computer.

## Other systems

The install procedure was tested on Linux x86_64 only. On other systems, the necessary changes are in `tools/setup.sh`:

- macOS: the folder of the TeX Live binaries is `universal-darwin`, and the system needs Pango and Cairo.
- ARM: the folder of the TeX Live binaries is `aarch64-linux`.
