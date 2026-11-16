#!/bin/bash
#
# Render a MIDI file to WAV with fluidsynth.
#
# Usage:
#   bin/render_audio.sh [options] MIDI [fluidsynth args...]
#
# Options:
#   --soundfont PATH       General MIDI SoundFont
#                          (default: /usr/share/sounds/sf2/FluidR3_GM.sf2)
#   --sample-rate N        sample rate (default: 22050)
#   --gain G               fluidsynth gain (default: 0.9)
#   --reverb-room-size R   reverb room size (default: 0.6)
#   --reverb-level L       reverb level (default: 0.5)
#   --no-reverb            disable reverb
#
# The WAV is written next to the MIDI, with the same stem.
# Unrecognized arguments are passed to fluidsynth before the SoundFont/MIDI.
#
set -euo pipefail

DEFAULT_SOUNDFONT="/usr/share/sounds/sf2/FluidR3_GM.sf2"

usage() {
    cat <<'EOF'
Usage: bin/render_audio.sh [options] MIDI [fluidsynth args...]

Options:
  --soundfont PATH       General MIDI SoundFont
                         (default: /usr/share/sounds/sf2/FluidR3_GM.sf2)
  --sample-rate N        sample rate (default: 22050)
  --gain G               fluidsynth gain (default: 0.9)
  --reverb-room-size R   reverb room size (default: 0.6)
  --reverb-level L       reverb level (default: 0.5)
  --no-reverb            disable reverb
  -h, --help             show this help

The WAV is written next to the MIDI, with the same stem.
Unrecognized arguments are passed to fluidsynth.
EOF
}

soundfont="$DEFAULT_SOUNDFONT"
sample_rate=22050
gain=0.9
reverb=1
reverb_room=0.6
reverb_level=0.5
mid=""
extra=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --soundfont)
            soundfont="${2:?--soundfont needs a path}"
            shift 2
            ;;
        --soundfont=*)
            soundfont="${1#*=}"
            shift
            ;;
        --sample-rate)
            sample_rate="${2:?--sample-rate needs a value}"
            shift 2
            ;;
        --sample-rate=*)
            sample_rate="${1#*=}"
            shift
            ;;
        --gain)
            gain="${2:?--gain needs a value}"
            shift 2
            ;;
        --gain=*)
            gain="${1#*=}"
            shift
            ;;
        --reverb-room-size)
            reverb_room="${2:?--reverb-room-size needs a value}"
            shift 2
            ;;
        --reverb-room-size=*)
            reverb_room="${1#*=}"
            shift
            ;;
        --reverb-level)
            reverb_level="${2:?--reverb-level needs a value}"
            shift 2
            ;;
        --reverb-level=*)
            reverb_level="${1#*=}"
            shift
            ;;
        --no-reverb)
            reverb=0
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --)
            shift
            extra+=("$@")
            break
            ;;
        -*)
            extra+=("$1")
            shift
            ;;
        *)
            if [[ -z "$mid" ]]; then
                mid="$1"
            else
                extra+=("$1")
            fi
            shift
            ;;
    esac
done

if [[ -z "$mid" ]]; then
    echo "error: missing MIDI path" >&2
    usage >&2
    exit 2
fi

if [[ ! -f "$mid" ]]; then
    echo "error: MIDI file not found: $mid" >&2
    exit 2
fi

if ! command -v fluidsynth >/dev/null 2>&1; then
    cat >&2 <<'EOF'
error: fluidsynth is not installed.

Install it first, for example:
  Debian/Ubuntu: sudo apt install fluidsynth fluid-soundfont-gm
  macOS:         brew install fluid-synth
  https://www.fluidsynth.org/
EOF
    exit 127
fi

if [[ ! -f "$soundfont" ]]; then
    cat >&2 <<EOF
error: SoundFont not found: $soundfont

Install a General MIDI SoundFont, for example:
  Debian/Ubuntu: sudo apt install fluid-soundfont-gm

Or pass one explicitly:
  bin/render_audio.sh --soundfont /path/to/soundfont.sf2 "$mid"
EOF
    exit 2
fi

mid_dir="$(dirname -- "$mid")"
mid_base="$(basename -- "$mid")"
stem="${mid_base%.*}"
wav="$mid_dir/$stem.wav"

cmd=(fluidsynth -ni -F "$wav" -r "$sample_rate" -g "$gain")

if [[ "$reverb" -eq 1 ]]; then
    cmd+=(
        -o synth.reverb.active=1
        -o "synth.reverb.room-size=$reverb_room"
        -o "synth.reverb.level=$reverb_level"
    )
else
    cmd+=(-o synth.reverb.active=0)
fi

cmd+=(${extra[@]+"${extra[@]}"} "$soundfont" "$mid")

if [[ "${VERBOSE:-0}" == "1" ]]; then
    "${cmd[@]}"
else
    "${cmd[@]}" >/dev/null 2>&1
fi

echo "wav      : $wav"
