#!/usr/bin/env bash
# SPEC_ID: venv-always-on (ensure_venv)
# Generated on 2025-08-31

set -vexu

# move to repo root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

VENV_DIR="$REPO_ROOT/.venv"

# require python3.11 explicitly
if ! command -v python3.11 >/dev/null 2>&1; then
  echo "python3.11 が見つかりません。python3.11 をインストールしてください。" >&2
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  python3.11 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$REPO_ROOT/requirements.txt"

echo "VENV_READY: $VENV_DIR"

