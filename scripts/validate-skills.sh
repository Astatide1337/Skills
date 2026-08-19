#!/usr/bin/env bash

set -euo pipefail

repo_root=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

if command -v uv >/dev/null 2>&1; then
  exec uv run python scripts/validate_catalog.py
fi

exec python3 scripts/validate_catalog.py
