#!/usr/bin/env sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_ROOT"

if [ ! -x .venv/bin/python ]; then
  echo "Virtual environment belum tersedia. Jalankan ./scripts/setup.sh terlebih dahulu." >&2
  exit 1
fi

exec .venv/bin/python run.py
