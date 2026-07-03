#!/usr/bin/env bash
# Linux / macOS entrypoint for unified system and database cleanup
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
uv run python "$SCRIPT_DIR/cleanup.py" "$@"
