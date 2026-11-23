"""
Command-line entry point: profile → dataset → composition → MIDI.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .model import Composition
from .compose import Composer
from .profile import Profile
from .render import ABCWriter, ChartWriter, MidiWriter, PlayerJsonWriter
from .sources import ClimateSource

DEFAULT_PROFILE = Path("profiles/climate.yaml")
DEFAULT_OUT = Path("out/climate")


def parse_voice_ids(value: str) -> set[int]:
    try:
        return {int(part) for part in value.split(",") if part.strip()}
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "--voices expects comma-separated integers, e.g. 0 or 0,1"
        ) from exc


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compose a profile and render it to MIDI."
    )
    parser.add_argument(
        "--profile",
        type=Path,
        default=DEFAULT_PROFILE,
        help="YAML profile path (default: profiles/climate.yaml)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="output basename; .mid will be appended",
    )
    parser.add_argument(
        "--voices",
        type=parse_voice_ids,
        help="comma-separated voice ids to render, e.g. 0 or 0,1",
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="list the profile's voices and exit",
    )
    parser.add_argument(
        "--abc",
        action="store_true",
        help="also write ABC notation",
    )
    parser.add_argument(
        "--player-out",
        "--player_out",
        type=Path,
        default=None,
        help="write the web player payload to PATH",
    )
    parser.add_argument(
        "--chart",
        action="store_true",
        help="also write a chart PNG",
    )
    return parser

def print_info(
    profile: Profile,
    composition: Composition,
    mid_path: str,
    abc_path: str | None = None,
    player_path: str | None = None,
    chart_path: str | None = None,
):
    _, total = composition.bar_times()
    voice_label = ", ".join(f"{voice.label}={len(voice.notes)}" for voice in composition.voices)

    print(f"profile  : {profile.name} — {profile.title}")
    print(f"bars     : {composition.n_bars}")
    print(f"voices   : {voice_label}")
    print(f"tempo    : {composition.tempo_map}")
    print(f"duration : {total:.1f}s")
    print(f"midi     : {mid_path}")

    if abc_path is not None:
        print(f"abc      : {abc_path}")

    if player_path is not None:
        print(f"player   : {player_path}")

    if chart_path is not None:
        print(f"chart    : {chart_path}")

    return

def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    profile = Profile.load(args.profile)

    if args.list_voices:
        for spec in profile.voices:
            print(f"{spec.id}\t{spec.name}\t{spec.generator}\tseries={spec.series}")
        return 0

    datasource = ClimateSource(profile.directory, profile.start_year, profile.end_year)
    dataset = datasource.load()

    composition = Composer(profile).compose(dataset)

    if args.voices is not None:
        composed_voices = {voice.id for voice in composition.voices}

        missing = args.voices - composed_voices
        if missing:
            print(f"warning: voices not in composition: {sorted(missing)}")

        selected = args.voices & composed_voices
        if not selected:
            print("error: none of the requested voices exist in the composition")
            return 2

        composition.voices = [voice for voice in composition.voices if voice.id in selected]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    mid_path = args.out.with_suffix(".mid")

    midi_writer = MidiWriter(ticks_per_beat=profile.timing.ticks_per_quarter, bar_ticks=profile.timing.bar_ticks, config=profile.render)
    midi_writer.write(composition, mid_path)

    abc_path = None
    if args.abc:
        abc_path = args.out.with_suffix(".abc")
        ABCWriter(
            eighth=profile.timing.eighth,
            bar_ticks=profile.timing.bar_ticks,
            section_bars=profile.timing.section_bars,
            config=profile.render,
        ).write(composition, abc_path)

    player_path = None
    if args.player_out is not None:
        player_path = args.player_out
        player_path.parent.mkdir(parents=True, exist_ok=True)
        PlayerJsonWriter(
            bar_ticks=profile.timing.bar_ticks,
            config=profile.render,
        ).write(composition, dataset, player_path)

    chart_path = None
    if args.chart:
        chart_path = args.out.with_suffix(".png")
        ChartWriter(
            composition,
            dataset,
            bar_ticks=profile.timing.bar_ticks,
            config=profile.render,
        ).write(chart_path)

    print_info(profile, composition, mid_path, abc_path, player_path, chart_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
