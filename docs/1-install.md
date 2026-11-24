# Install the tools

The tools are the Python environment of the template, a portable TeX Live, and the model of the offline speech recognizer. The script `tools/setup.sh` puts all of them in one folder: `.tools`, in the folder of this repository. You do not need root access.

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

   The install downloads approximately 1.3 GB and needs 5 to 15 minutes. At the end, `videogen doctor` verifies the tools.

4. Verify the tools and the voice service:

   ```bash
   tools/videogen doctor --online
   ```

   `--online` sends one short sentence to the speech service for each language.

## The tools folder

```
AIVideoGenerator/
└── .tools/
    ├── venv/              the Python environment, with the videogen package
    ├── texlive/           a portable TeX Live
    └── models/whisper/    the model of the offline speech recognizer
```

- The folder `.tools` is in the `.gitignore` file of the repository. It stays out of git.
- The tools stay with the project. A sandbox that keeps the folder of the project also keeps the tools.
- A new clone of the repository has no tools. Start `tools/setup.sh` in the new clone.
- The Python environment has the path of the repository in its files. If you move the repository to a different folder, start `tools/setup.sh` again in the new location.
- To remove the tools, delete the folder `.tools`. `tools/setup.sh --fresh` does this, then installs again.

The previous version put the tools in `~/.cache/aivideogen`. That folder is not necessary. You can delete it.

### A different folder for the tools

To put the tools in a different folder, set `AIVIDEOGEN_TOOLS` before you start `tools/setup.sh`. The program `videogen` reads the same variable. Thus set it each time you use `videogen`.

CAUTION: A sandbox can delete a folder outside the project between two sessions. The default folder `.tools` does not have this problem.

## The location of the command

The install puts `videogen` in `.tools/venv/bin/`. This folder is usually not on the `PATH`. Three solutions:

- In the folder of the repository, use `tools/videogen`. This script starts `videogen` with the tools of the repository, and it operates from any folder.
- Use the full path: `.tools/venv/bin/videogen`.
- Activate the environment when you work on a video: `source .tools/venv/bin/activate`.

## What `videogen doctor` verifies

| Item | Necessary | How to correct a problem |
|---|---|---|
| Python environment of the tools | yes | `tools/setup.sh` |
| packages `manim` and `edge_tts` | yes | `tools/setup.sh` |
| packages `faster_whisper` and `trafilatura` | no | install the extras `qa` and `extract` |
| `ffmpeg` and `ffprobe` | yes | the package manager of your system |
| `magick` (ImageMagick) | no | necessary for `videogen sheet` |
| TeX Live, and the LaTeX compilation | yes | `tools/setup.sh` |
| speech engine `edge-tts` | yes | the package `edge-tts` |

`videogen doctor --fix` starts `tools/setup.sh` when a necessary item is missing.

If the tools are not in the folder of the repository, `doctor` prints a NOTE: a sandbox can delete the other folder between two sessions.

## Update

1. Go to the folder of the repository. Get the new version: `git pull`.
2. Start `tools/setup.sh` again. It updates the Python environment, and keeps TeX Live and the model.
3. Start `videogen selftest` to make sure that the pipeline operates on your computer.

## Other systems

The install procedure was tested on Linux x86_64 only. On other systems, the necessary changes are in `tools/setup.sh`:

- macOS: the folder of the TeX Live binaries is `universal-darwin`, and the system needs Pango and Cairo.
- ARM: the folder of the TeX Live binaries is `aarch64-linux`.
