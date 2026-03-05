#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-./.venv/bin/python}"

echo "[quality] checklist"
echo "[quality] 1/4 format  -> ruff format --check"
"$PYTHON_BIN" -m ruff format --check src tests

echo "[quality] 2/4 lint    -> ruff check"
"$PYTHON_BIN" -m ruff check src tests

echo "[quality] 3/4 unit    -> pytest tests/test_pipeline.py"
"$PYTHON_BIN" -m pytest tests/test_pipeline.py

echo "[quality] 4/4 smoke   -> pytest -k persist_load"
"$PYTHON_BIN" -m pytest tests/test_pipeline.py -k persist_load

echo "[quality] ok ✅"
