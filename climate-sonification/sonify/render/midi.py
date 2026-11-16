"""
Render a Composition as a type-1 MIDI file.
"""

from __future__ import annotations

from pathlib import Path

import mido

from ..model import Composition

# General MIDI programs used by the climate profile's voice ids.
# Unknown ids fall back to acoustic grand piano.
PROGRAMS = {
    0: 73,  # flute
    1: 42,  # cello
}


class MidiWriter:
    def __init__(
        self,
        ticks_per_beat: int = 480,
        bar_ticks: int = 2880,
        time_signature: tuple[int, int] = (12, 8),
        tempo_scale: float = 1.5,
        config: dict | None = None
    ):
        self.ticks_per_beat = ticks_per_beat
        self.bar_ticks = bar_ticks
        self.time_signature = time_signature
        self.tempo_scale = tempo_scale
        self.program = config["midi_program"] if config and config["midi_program"] else PROGRAMS

    def write(self, composition: Composition, path: Path) -> None:
        if not composition.tempo_map:
            raise ValueError("composition has no tempo map")

        mid = mido.MidiFile(type=1, ticks_per_beat=self.ticks_per_beat)
        mid.tracks.append(self._meta_track(composition))

        for voice in composition.voices:
            mid.tracks.append(self._voice_track(voice))

        mid.save(path)

    def _meta_track(self, composition: Composition) -> mido.MidiTrack:
        track = mido.MidiTrack()
        track.append(
            mido.MetaMessage(
                "track_name",
                name=str(composition.meta.get("title", "composition")),
                time=0,
            )
        )

        numerator, denominator = self.time_signature
        track.append(
            mido.MetaMessage(
                "time_signature",
                numerator=numerator,
                denominator=denominator,
                time=0,
            )
        )

        first_bar, first_bpm = composition.tempo_map[0]
        track.append(
            mido.MetaMessage(
                "set_tempo",
                tempo=mido.bpm2tempo(self.tempo_scale * first_bpm),
                time=0,
            )
        )

        previous_bar = first_bar
        for bar, bpm in composition.tempo_map[1:]:
            track.append(
                mido.MetaMessage(
                    "set_tempo",
                    tempo=mido.bpm2tempo(self.tempo_scale * bpm),
                    time=(bar - previous_bar) * self.bar_ticks,
                )
            )
            previous_bar = bar

        track.append(mido.MetaMessage("end_of_track", time=0))

        return track

    def _voice_track(self, voice) -> mido.MidiTrack:
        track = mido.MidiTrack()
        channel = voice.id % 16
        track.append(mido.MetaMessage("track_name", name=voice.label, time=0))
        track.append(
            mido.Message(
                "program_change",
                channel=channel,
                program=self.program.get(voice.id, 0),
                time=0,
            )
        )

        events = []
        for note in voice.notes:
            events.append(
                (
                    note.tick,
                    0,
                    mido.Message(
                        "note_off",
                        channel=channel,
                        note=note.midi,
                        velocity=0,
                    ),
                )
            ) # make sure it is off for now
            events.append(
                (
                    note.tick,
                    1,
                    mido.Message(
                        "note_on",
                        channel=channel,
                        note=note.midi,
                        velocity=note.vel,
                    ),
                )
            )
            events.append(
                (
                    note.tick + note.dur,
                    0,
                    mido.Message(
                        "note_off",
                        channel=channel,
                        note=note.midi,
                        velocity=0,
                    ),
                )
            )

        events.sort(key=lambda event: (event[0], event[1]))

        last_tick = 0
        for tick, _, message in events:
            track.append(message.copy(time=tick - last_tick))
            last_tick = tick

        track.append(mido.MetaMessage("end_of_track", time=0))

        return track
