#!/usr/bin/env bash
# Install the optional speech engine OmniVoice: a local model, with a sample of a voice.
# Start tools/setup.sh first: this script needs the environment of the tools.
#
#   tools/setup-omnivoice.sh                install, or repair an incomplete install
#   tools/setup-omnivoice.sh --environment  only the Python environment of the model
#   tools/setup-omnivoice.sh --models       only the models
#
# The install puts, in the folder of the tools (.tools of this repository):
#   venv-omnivoice/       the Python environment of the model, with PyTorch (about 7 GB)
#   models/omnivoice/     the model k2-fsa/OmniVoice (about 3 GB)
#   models/mms-fa/        the model that gives the time of each word (about 1.2 GB)
# and it installs the package num2words in the environment of the tools.
# Download size: approximately 11 GB. Needs a GPU for a fast voice: NVIDIA (tested), or Apple
# Silicon (the model accepts it; not tested here). Without a GPU, the model runs on the processor
# and it is slow.
# The model does not use the network: it reads the text, the model and the sample of the voice on
# this computer. Its license is CC-BY-NC: for a use that is not commercial.
#
# Optional environment variables:
#   AIVIDEOGEN_TOOLS   folder for the tools (default: .tools in this repository)
#   AIVIDEOGEN_PYTHON  Python version for the environment (default 3.12)
#   HF_ENDPOINT        a mirror of Hugging Face, where the site is slow or not reachable
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS="${AIVIDEOGEN_TOOLS:-$ROOT/.tools}"
PYTHON_VERSION="${AIVIDEOGEN_PYTHON:-3.12}"
ONLY="${1:-}"
case "$ONLY" in
  ""|--environment|--models) ;;
  *) echo "ERROR: unknown option '$ONLY'. The options are --environment and --models." >&2; exit 1 ;;
esac

if [ ! -x "$TOOLS/venv/bin/python" ]; then
  echo "ERROR: the tools of AIVideoGenerator are not installed. Start tools/setup.sh first." >&2
  exit 1
fi
TOOLS="$(cd "$TOOLS" && pwd)"   # an absolute path, also when AIVIDEOGEN_TOOLS is relative
ENVIRONMENT="$TOOLS/venv-omnivoice"
MODEL="$TOOLS/models/omnivoice"
ALIGNER="$TOOLS/models/mms-fa"
# The aligner needs the interface of torchaudio 2.8: the version 2.9 removes it.
TORCH_VERSION="2.8.0"

install() {   # install() <python environment> <packages...>
  local target="$1"
  shift
  if command -v uv >/dev/null 2>&1; then
    uv pip install --python "$target/bin/python" "$@"
  else
    "$target/bin/python" -m pip install --upgrade pip
    "$target/bin/python" -m pip install "$@"
  fi
}

if [ "$ONLY" != "--models" ]; then
  echo "== 1/2  Python environment of the model: $ENVIRONMENT"
  if [ ! -x "$ENVIRONMENT/bin/python" ]; then
    if command -v uv >/dev/null 2>&1; then
      uv venv --python "$PYTHON_VERSION" "$ENVIRONMENT"
    else
      "python$PYTHON_VERSION" -m venv "$ENVIRONMENT"
    fi
  fi
  # The wheels with CUDA 12.8 are not on PyPI: they are on the index of PyTorch.
  CUDA=()
  if command -v nvidia-smi >/dev/null 2>&1; then
    CUDA=(--extra-index-url "https://download.pytorch.org/whl/cu128")
  fi
  install "$ENVIRONMENT" "torch==$TORCH_VERSION" "torchaudio==$TORCH_VERSION" ${CUDA[@]+"${CUDA[@]}"} omnivoice
  echo "== 2/2  Package for the numbers in words, in the environment of the tools"
  install "$TOOLS/venv" -e "$ROOT[omnivoice]"
fi

if [ "$ONLY" != "--environment" ]; then
  echo "== Models: $MODEL and $ALIGNER"
  mkdir -p "$MODEL" "$ALIGNER/checkpoints"
  if [ ! -f "$MODEL/model.safetensors" ] || [ ! -f "$MODEL/audio_tokenizer/model.safetensors" ]; then
    "$ENVIRONMENT/bin/python" - "$MODEL" <<'PY'
import sys
from huggingface_hub import snapshot_download

snapshot_download("k2-fsa/OmniVoice", local_dir=sys.argv[1])
PY
  else
    echo "The model of speech is here."
  fi
  WEIGHTS="https://dl.fbaipublicfiles.com/mms/torchaudio/ctc_alignment_mling_uroman/model.pt"
  if [ ! -s "$ALIGNER/checkpoints/model.pt" ]; then
    curl -fsSL -C - --retry 5 -o "$ALIGNER/checkpoints/model.pt.part" "$WEIGHTS"
    mv "$ALIGNER/checkpoints/model.pt.part" "$ALIGNER/checkpoints/model.pt"
  else
    echo "The model of the aligner is here."
  fi
fi

echo "== Verification"
if [ -f "$MODEL/model.safetensors" ] && [ -f "$ALIGNER/checkpoints/model.pt" ]; then
  "$ENVIRONMENT/bin/python" -I -W ignore "$ROOT/videogen/tts/omnivoice_worker.py" \
    --model "$MODEL" --aligner "$ALIGNER" --check
else
  echo "The models are not here. Start tools/setup-omnivoice.sh --models to download them."
fi
"$TOOLS/venv/bin/python" -m videogen.cli doctor
