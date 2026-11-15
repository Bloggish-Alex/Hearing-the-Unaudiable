"""
Syncopated root/fifth/octave accompaniment.
"""

from __future__ import annotations

from ..model import Note
from .base import VoiceContext, VoiceGenerator


class BasslineVoice(VoiceGenerator):

    def generate(self, ctx: VoiceContext) -> list[Note]:
        series = ctx.dataset.series[self.series_id]
        roots = self.options["roots"]
        velocity = self.options["velocity"]
        octave_threshold = self.options["octave_threshold"]
        section_bars = ctx.timing.section_bars
        eighth = ctx.timing.eighth
        bar_ticks = ctx.timing.bar_ticks
        first_year = int(ctx.dataset.periods[0].start)

        notes: list[Note] = []

        for bar, value in enumerate(series.values): # mean of temp monthly data
            if value is None:
                continue

            year = int(ctx.dataset.periods[bar].start)
            section = (year - first_year) // section_bars # n years as a section (10 by default)

            root = roots[section % len(roots)] # Set root every n years (a section)
            fifth, octave = root + 7, root + 12 # Chord: root, root + 7, root + 12

            # dynamic velocity according to the mean value, using floor and ceiling to limit the range.
            vel = int(
                max(
                    velocity["floor"],
                    min(velocity["ceiling"], velocity["base"] + value * velocity["per_mean"])
                )
            )

            """
            We need some minor tuning over pitches, to void just repeating pitch list every 10 years.
            Three patterns:
                1. last bar/end (last year) of a section: 'root' pitch for 12 slots
                2. even year of a section: 3 root, 3 fifth, 2 root, 4 octave|fifth
                3. odd year of a section: 3 root, 2 fifth, 3 root, 3 octave|fifth
            If value is over speficied threshold, give a high pitch (octave) in last 4/3 slots
            """
            if bar % section_bars == section_bars - 1:
                pattern = [(0, 12, root)]
            elif section % 2 == 0:
                pattern = [
                    (0, 3, root),
                    (3, 3, fifth),
                    (6, 2, root),
                    (8, 4, octave if value > octave_threshold else fifth)
                ]
            else:
                pattern = [
                    (0, 3, root),
                    (4, 2, fifth),
                    (6, 3, root),
                    (9, 3, octave if value > octave_threshold else fifth)
                ]

            for slot, duration_slots, pitch in pattern:
                notes.append(
                    Note(
                        bar * bar_ticks + slot * eighth,
                        duration_slots * eighth,
                        pitch,
                        vel,
                        self.voice_id,
                    )
                )

        return notes
