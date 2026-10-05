#!/bin/bash
# Set up the backend's Python environment inside WSL (Ubuntu), for Windows PCs where Smart App Control blocks
# the machine-learning libraries. Linux files aren't checked by Smart App Control.
# Run from Windows:   wsl bash backend/setup_wsl.sh      (run.py then uses it automatically)
set -e
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
HERE="$(cd "$(dirname "$0")" && pwd)"
VENV="$HOME/venvs/hr-simple"

command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
[ -x "$VENV/bin/python" ] || uv venv --python 3.11 "$VENV"
tr -d '\r' < "$HERE/requirements.txt" > /tmp/hr-simple-requirements.txt
uv pip install --python "$VENV/bin/python" -r /tmp/hr-simple-requirements.txt
"$VENV/bin/python" -c "import pandas, sklearn, xgboost, lime, fastapi; print('Backend environment ready in WSL.')"
