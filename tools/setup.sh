#!/usr/bin/env bash
# Install the tools that AIVideoGenerator needs. You do not need root access.
#
#   tools/setup.sh            install, or repair an incomplete install
#   tools/setup.sh --fresh    delete the cache, then install again
#
# The install puts a Python environment and a portable TeX Live in $AIVIDEOGEN_CACHE.
# Default cache: ~/.cache/aivideogen. Download size: approximately 800 MB.
#
# Optional environment variables:
#   AIVIDEOGEN_CACHE   folder for the tools (default ~/.cache/aivideogen)
#   AIVIDEOGEN_PYTHON  Python version for the environment (default 3.12)
#   AIVIDEOGEN_EXTRAS  optional packages (default qa,extract,dev)
#   AIVIDEOGEN_CTAN    TeX Live repository (default: the CTAN mirror service)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CACHE="${AIVIDEOGEN_CACHE:-$HOME/.cache/aivideogen}"
PYTHON_VERSION="${AIVIDEOGEN_PYTHON:-3.12}"
EXTRAS="${AIVIDEOGEN_EXTRAS:-qa,extract,dev}"
CTAN="${AIVIDEOGEN_CTAN:-https://mirror.ctan.org/systems/texlive/tlnet}"
ARCH="$(uname -m)-$(uname -s | tr '[:upper:]' '[:lower:]')"   # for example: x86_64-linux

if [ "${1:-}" = "--fresh" ]; then
  echo "Delete $CACHE"
  rm -rf "$CACHE"
fi
mkdir -p "$CACHE"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

for tool in curl perl tar ffmpeg; do
  command -v "$tool" >/dev/null 2>&1 || { echo "ERROR: $tool is not installed. Install it, then start again." >&2; exit 1; }
done

echo "== 1/3  Python environment: $CACHE/venv"
if [ ! -x "$CACHE/venv/bin/python" ]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv --python "$PYTHON_VERSION" "$CACHE/venv"
  else
    "python$PYTHON_VERSION" -m venv "$CACHE/venv"
  fi
fi
if command -v uv >/dev/null 2>&1; then
  uv pip install --python "$CACHE/venv/bin/python" -e "$ROOT[$EXTRAS]"
else
  "$CACHE/venv/bin/python" -m pip install --upgrade pip
  "$CACHE/venv/bin/python" -m pip install -e "$ROOT[$EXTRAS]"
fi

echo "== 2/3  TeX Live (portable): $CACHE/texlive"
if [ ! -x "$CACHE/texlive/bin/$ARCH/dvisvgm" ]; then
  curl -fsSL -o "$WORK/install-tl-unx.tar.gz" "$CTAN/install-tl-unx.tar.gz"
  tar xzf "$WORK/install-tl-unx.tar.gz" -C "$WORK"
  cat > "$WORK/profile.txt" <<PROFILE
selected_scheme scheme-basic
TEXDIR $CACHE/texlive
TEXMFLOCAL $CACHE/texlive/texmf-local
TEXMFSYSCONFIG $CACHE/texlive/texmf-config
TEXMFSYSVAR $CACHE/texlive/texmf-var
TEXMFCONFIG $CACHE/texmf-user/config
TEXMFVAR $CACHE/texmf-user/var
TEXMFHOME $CACHE/texmf-user/home
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
  "$CACHE/texlive/bin/$ARCH/tlmgr" install dvisvgm standalone preview lm babel-english
else
  echo "Already installed."
fi

echo "== 3/3  Verification"
"$CACHE/venv/bin/videogen" doctor
