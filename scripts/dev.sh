#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

PYTHON_BIN="python3"
if [[ -x "$HOME/Code/uCore/backend/.venv/bin/python" ]]; then
  PYTHON_BIN="$HOME/Code/uCore/backend/.venv/bin/python"
fi

if [[ ! -d .venv ]]; then
  "$PYTHON_BIN" -m venv .venv
fi

source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .

smx doctor
smx capabilities
