#!/usr/bin/env sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_ROOT"

command -v python3 >/dev/null 2>&1 || {
  echo "Python 3 tidak ditemukan. Instal Python 3.12 terlebih dahulu." >&2
  exit 1
}

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [ "$PYTHON_VERSION" != "3.12" ]; then
  echo "Ditemukan Python $PYTHON_VERSION. Proyek ini direkomendasikan menggunakan Python 3.12." >&2
  exit 1
fi

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q

echo "Setup selesai. Jalankan aplikasi dengan: ./scripts/run.sh"
