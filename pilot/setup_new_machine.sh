#!/usr/bin/env bash
# One-time setup of the pilot on a second Mac. Run from the sermon-processor folder:
#   bash pilot/setup_new_machine.sh
set -euo pipefail
cd "$(dirname "$0")"

command -v ffmpeg >/dev/null || { echo "Install ffmpeg first: brew install ffmpeg"; exit 1; }
PY=${PYTHON:-python3}
$PY -c 'import sys; assert sys.version_info >= (3, 10), "need Python 3.10+"'

# GPU environment (mlx-whisper). Large download (PyTorch, about 140 MB).
[ -d .venv-mlx ] || $PY -m venv .venv-mlx
.venv-mlx/bin/pip install --quiet mlx-whisper

# CPU environment (faster-whisper) only if you want to rerun small.en or medium.en.
if [ "${WITH_CPU_ENV:-0}" = "1" ]; then
  [ -d .venv-cpu ] || $PY -m venv .venv-cpu
  .venv-cpu/bin/pip install --quiet faster-whisper numpy
fi

.venv-mlx/bin/python -c "import mlx.core as mx; print('GPU device:', mx.default_device())"
python3 fetch_audio.py --check
echo "Setup done. Next: python3 pilot/fetch_audio.py"
