#!/usr/bin/env bash
# Install the tools that AIVideoGenerator needs. You do not need root access.
#
#   tools/setup.sh            install, or repair an incomplete install
#   tools/setup.sh --fresh    delete the folder .tools of this repository, then install
#
# The install puts all the tools in the folder .tools of this repository:
#   .tools/venv/              the Python environment, with the videogen package
#   .tools/texlive/           a portable TeX Live
#   .tools/models/whisper/    the model of the offline speech recognizer
# The tools stay with the project: a sandbox that keeps the folder of the project also
# keeps the tools. The folder .tools is not in git. Download size: approximately 1.3 GB.
#
# To put the tools in a different folder, set AIVIDEOGEN_TOOLS here, and each time you
# use videogen.
#
# Optional environment variables:
#   AIVIDEOGEN_TOOLS   folder for the tools (default: .tools in this repository)
#   AIVIDEOGEN_PYTHON  Python version for the environment (default 3.12)
#   AIVIDEOGEN_EXTRAS  optional packages (default qa,extract,dev)
#   AIVIDEOGEN_CTAN    TeX Live repository (default: the CTAN mirror service)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS="${AIVIDEOGEN_TOOLS:-$ROOT/.tools}"
PYTHON_VERSION="${AIVIDEOGEN_PYTHON:-3.12}"
EXTRAS="${AIVIDEOGEN_EXTRAS:-qa,extract,dev}"
CTAN="${AIVIDEOGEN_CTAN:-https://mirror.ctan.org/systems/texlive/tlnet}"
ARCH="$(uname -m)-$(uname -s | tr '[:upper:]' '[:lower:]')"   # for example: x86_64-linux

for tool in curl perl tar ffmpeg; do
  command -v "$tool" >/dev/null 2>&1 || { echo "ERROR: $tool is not installed. Install it, then start again." >&2; exit 1; }
done

# --fresh deletes only the default folder. A different folder (AIVIDEOGEN_TOOLS) is the
# decision of the user: the script does not delete it.
if [ "${1:-}" = "--fresh" ]; then
  if [ "$TOOLS" = "$ROOT/.tools" ]; then
    echo "Delete $TOOLS"
    rm -rf "$ROOT/.tools"
  else
    echo "NOTE: --fresh deletes only the folder .tools of this repository. AIVIDEOGEN_TOOLS is set: empty $TOOLS yourself, if necessary."
  fi
fi
mkdir -p "$TOOLS"
TOOLS="$(cd "$TOOLS" && pwd)"   # an absolute path, also when AIVIDEOGEN_TOOLS is relative
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

if [ "$TOOLS" != "$HOME/.cache/aivideogen" ] && [ -d "$HOME/.cache/aivideogen" ]; then
  echo "NOTE: a previous version put the tools in $HOME/.cache/aivideogen. This version does not use that folder. You can delete it."
fi

echo "== 1/4  Python environment: $TOOLS/venv"
if [ ! -x "$TOOLS/venv/bin/python" ]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv --python "$PYTHON_VERSION" "$TOOLS/venv"
  else
    "python$PYTHON_VERSION" -m venv "$TOOLS/venv"
  fi
fi
if command -v uv >/dev/null 2>&1; then
  uv pip install --python "$TOOLS/venv/bin/python" -e "$ROOT[$EXTRAS]"
else
  "$TOOLS/venv/bin/python" -m pip install --upgrade pip
  "$TOOLS/venv/bin/python" -m pip install -e "$ROOT[$EXTRAS]"
fi

echo "== 2/4  TeX Live (portable): $TOOLS/texlive"
if [ ! -x "$TOOLS/texlive/bin/$ARCH/dvisvgm" ]; then
  curl -fsSL -o "$WORK/install-tl-unx.tar.gz" "$CTAN/install-tl-unx.tar.gz"
  tar xzf "$WORK/install-tl-unx.tar.gz" -C "$WORK"
  cat > "$WORK/profile.txt" <<PROFILE
selected_scheme scheme-basic
TEXDIR $TOOLS/texlive
TEXMFLOCAL $TOOLS/texlive/texmf-local
TEXMFSYSCONFIG $TOOLS/texlive/texmf-config
TEXMFSYSVAR $TOOLS/texlive/texmf-var
TEXMFCONFIG $TOOLS/texmf-user/config
TEXMFVAR $TOOLS/texmf-user/var
TEXMFHOME $TOOLS/texmf-user/home
instopt_adjustpath 0
instopt_adjustrepo 1
instopt_letter 0
instopt_portable 1
instopt_write18_restricted 1
tlpdbopt_autobackup 0
tlpdbopt_install_docfiles 0
tlpdbopt_install_srcfiles 0
tlpdbopt_post_code 1
PROFILE
  perl "$WORK"/install-tl-*/install-tl -profile "$WORK/profile.txt"
  "$TOOLS/texlive/bin/$ARCH/tlmgr" install dvisvgm standalone preview lm babel-english
else
  echo "Already installed."
fi

echo "== 3/4  Model of the offline speech recognizer: $TOOLS/models/whisper"
# videogen transcript uses this model. The download is not necessary for the install:
# without the model, videogen transcript downloads it when it starts the first time.
"$TOOLS/venv/bin/python" -W ignore - <<'PY' || echo "NOTE: the model is not downloaded. videogen transcript downloads it when it starts the first time."
import sys

from videogen import paths

try:
    from faster_whisper import WhisperModel
    WhisperModel("small", device="cpu", compute_type="int8", download_root=str(paths.models_root() / "whisper"))
except Exception as error:
    print(f"Not downloaded: {error}")
    sys.exit(1)
PY

echo "== 4/4  Verification"
"$TOOLS/venv/bin/python" -m videogen.cli doctor
