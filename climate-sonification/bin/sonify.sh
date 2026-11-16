#!/bin/bash
#
# Wrapper for `python -m sonify`, optionally rendering WAV.
#
# Usage:
#   bin/sonify.sh --out out/climate
#   bin/sonify.sh --out out/climate --audio
#   bin/sonify.sh --out out/climate --audio --soundfont /path/to.sf2
#   bin/sonify.sh --out out/melody --voices 0 --audio
#   bin/sonify.sh --list-voices
#
# Uses default settings to call render_audio.sh. For custom audio parameters,
# use bin/render_audio.sh directly.
#
# Use a specific interpreter with:
#   PYTHON=/path/to/python bin/sonify.sh ...
#
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT_DIR"

usage() {
    cat <<'EOF'
Usage:
  bin/sonify.sh --out OUTPUT_BASENAME [--voices 0|0,1] [--profile PROFILE]
  bin/sonify.sh --out OUTPUT_BASENAME [--voices ...] --audio [--soundfont PATH]
  bin/sonify.sh --list-voices

  --audio uses render_audio.sh default settings.
  For custom audio parameters, call bin/render_audio.sh directly.
EOF
}

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

generate_midi() {
    "$PYTHON_BIN" -m sonify "$@"
}

generate_wav() {
    local mid_path="$1"
    local soundfont="${2:-}"

    if [[ -n "$soundfont" ]]; then
        "$SCRIPT_DIR/render_audio.sh" --soundfont "$soundfont" "$mid_path"
    else
        "$SCRIPT_DIR/render_audio.sh" "$mid_path"
    fi
}

audio=0
soundfont=""
list_voices=0
out="out/climate"
midi_args=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --audio)
            audio=1
            shift
            ;;
        --soundfont)
            soundfont="${2:?--soundfont needs a path}"
            shift 2
            ;;
        --soundfont=*)
            soundfont="${1#*=}"
            shift
            ;;
        --out)
            out="${2:?--out needs a value}"
            midi_args+=("--out" "$2")
            shift 2
            ;;
        --out=*)
            out="${1#*=}"
            midi_args+=("$1")
            shift
            ;;
        --list-voices)
            list_voices=1
            midi_args+=("$1")
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            midi_args+=("$1")
            shift
            ;;
    esac
done

if ! PYTHON_BIN="$(resolve_python)"; then
    echo "No Python with mido and PyYAML found, set PYTHON to a suitable interpreter" >&2
    exit 127
fi

generate_midi ${midi_args[@]+"${midi_args[@]}"}

if [[ "$audio" -eq 0 ]]; then
    exit 0
fi

if [[ "$list_voices" -eq 1 ]]; then
    echo "warning: --audio is ignored with --list-voices" >&2
    exit 0
fi

if [[ "$out" == *.mid || "$out" == *.MID ]]; then
    mid_path="$out"
else
    mid_path="${out}.mid"
fi

generate_wav "$mid_path" "$soundfont"
