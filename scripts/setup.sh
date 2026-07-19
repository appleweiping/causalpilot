#!/usr/bin/env sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python_bin=${PYTHON:-python3}

if [ ! -f "$repo_root/frontend/package-lock.json" ]; then
  echo "Missing frontend/package-lock.json. A reproducible setup requires the checked-in lockfile." >&2
  exit 1
fi

if [ ! -x "$repo_root/.venv/bin/python" ]; then
  "$python_bin" -m venv "$repo_root/.venv"
fi

"$repo_root/.venv/bin/python" -m pip install -e "$repo_root/backend[test]"
npm --prefix "$repo_root/frontend" ci

echo "Setup complete. Run ./scripts/run_demo.sh"
