#!/usr/bin/env bash
# Root wrapper forwarding to scripts/cleanup/cleanup.py
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
uv run python "$SCRIPT_DIR/cleanup/cleanup.py" "$@"
