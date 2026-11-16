#!/bin/bash
#
# Wrapper for `python -m sonify`.
#
# Usage:
#   bin/sonify.sh --out out/climate
#   bin/sonify.sh --out out/melody --voices 0
#   bin/sonify.sh --out out/bass --voices 1
#   bin/sonify.sh --out out/full --voices 0,1
#   bin/sonify.sh --list-voices
#
# Use a specific interpreter with:
#   PYTHON=/path/to/python bin/sonify.sh ...
#
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT_DIR"

if [ "$1" = "--help" ]; then
    echo "Usage:"
    echo "  bin/sonify.sh --out OUTPUT_DIR [--voices 0|0,1] [--profile PROFILE]"
    echo "  bin/sonify.sh --list-voices"
    exit 0
fi


resolve_python() {
    if [[ -n "${PYTHON:-}" ]]; then
        printf '%s\n' "$PYTHON"
        return 0
    fi

    candidate="python"
    if command -v "$candidate" >/dev/null 2>&1 \
        && "$candidate" -c 'import mido, yaml' >/dev/null 2>&1; then
        printf '%s\n' "$candidate"
        return 0
    fi

    return 1
}

if ! PYTHON_BIN="$(resolve_python)"; then
    echo "No Python with mido and PyYAML found, set PYTHON to a suitable interpreter" >&2
    exit 127
fi

exec "$PYTHON_BIN" -m sonify "$@"
