"""
Section form: breath rests, cadence notes, and tempo.
"""

from __future__ import annotations

from ..model import Composition, Dataset, Note, Timing
from ..scales import Scale


class SectionForm:
    def __init__(self, config: dict, timing: Timing):
        self.config = config
        self.timing = timing

    @staticmethod
    def carve_rest(notes: list[Note], start: int, end: int) -> list[Note]:
        """
        Remove the tick range [start, end), splitting notes that cross it.
        In general, the duration between [start, end] will be replaced with REST, A note crossing the range will be splitted into two notes.
        """
        out = []

        for note in notes:
            note_start = note.tick
            note_end = note_start + note.dur

            if note_end <= start or note_start >= end: # out of range (start, end)
                out.append(note)
                continue

            # cut overlapped period, keep it out of range (start, end)
            if note_start < start:
                out.append(
                    Note(
                        note_start,
                        start - note_start,
                        note.midi,
                        note.vel,
                        note.voice,
                        note.art,
                    )
                )

            if note_end > end:
                out.append(
                    Note(
                        end,
                        note_end - end,
                        note.midi,
                        note.vel,
                        note.voice,
                        note.art,
                    )
                )

            # skip it if in the range of (start, end)

        return out

    def apply(
        self,
        composition: Composition,
        dataset: Dataset,
        scale: Scale,
    ) -> Composition:
        config = self.config
        timing = self.timing
        section_bars = timing.section_bars
        bar_ticks = timing.bar_ticks
        eighth = timing.eighth
        series = dataset.series[config["series"]]
        
        if series.slots is None:
            raise ValueError(
                f"series {config['series']!r} has no intra-bar slots"
            )

        rest = config["rest"]
        cadence = config["cadence"]

        target_id = cadence["voice"]
        target = next((voice for voice in composition.voices if voice.id == target_id), None)

        if target is None:
            raise ValueError(f"form target voice {target_id} not found")

        notes = list(target.notes)

        """
        Post-processing stage:
            1. Carve rest: replace notes in specified range with REST
            2. Cadence: last bar in a section as cadence bar
            3. Tempo build: 
        """
        for start_bar in range(0, composition.n_bars, section_bars):
            for offset in rest["bar_offsets"]:
                """
                Carve reset every 'section_bars', e.g. 10 bars per section.
                All slots/bars have been flatten into list (target.notes), carve rest can be done directly on bars, slots with ticks.
                """
                bar = start_bar + offset
                if bar < composition.n_bars:
                    # replace notes with REST in range [rest["slots"][0], rest["slots"][1]]
                    start_pos = bar * bar_ticks + rest["slots"][0] * eighth
                    end_pos = bar * bar_ticks + rest["slots"][1] * eighth
                    notes = self.carve_rest(notes, start_pos, end_pos)

            """
            The last bar in a section is handled as cadence
            Clear all notes in the bar, and fill specified number of notes with mean value.
            """
            cadence_bar = start_bar + section_bars - 1 # last bar in the section
            if cadence_bar >= composition.n_bars:
                continue

            values = [
                value for value in series.values[start_bar : start_bar + section_bars] if value is not None
            ]

            if not values:
                continue

            mean = sum(values) / len(values)

            notes = [
                note for note in notes if not (
                    cadence_bar * bar_ticks
                    <= note.tick
                    < (cadence_bar + 1) * bar_ticks
                )   # clear all notes in cadence bar
            ]

            velocity = cadence["velocity"]
            vel = int(
                max(
                    velocity["floor"],
                    min(
                        velocity["ceiling"],
                        velocity["base"] + (mean - scale.lo) / (scale.hi - scale.lo) * velocity["span"]
                    )
                )
            )

            notes.append(
                Note(
                    cadence_bar * bar_ticks,
                    cadence["slots"] * eighth,
                    scale.midi(scale.degree(mean)),
                    vel,
                    cadence["voice"],
                )
            )

        target.notes = notes

        tempo_map, volumes = TempoBuilder(config["tempo"], timing).build(dataset, config.get("series", "temp"))

        composition.tempo_map = tempo_map
        composition.meta["decade_volumes"] = volumes

        return composition


class TempoBuilder:
    """
    BPM: calculated with mean of temperature diffs in months
    """
    def __init__(self, config: dict, timing: Timing):
        self.config = config
        self.timing = timing

    def build(
        self, dataset: Dataset, series_id: str = "temp"
    ) -> tuple[list[tuple[int, int]], list[float]]:
        series = dataset.series[series_id]
        if series.slots is None:
            raise ValueError(f"series {series_id!r} has no intra-bar slots")

        section_bars = self.timing.section_bars
        tempo_map: list[tuple[int, int]] = []
        volumes: list[float] = []

        for bar in range(0, len(dataset.periods), section_bars): # len(data.periods) -> number of years
            slots = series.slots[bar : bar + section_bars]
            diffs = [
                abs(months[index] - months[index - 1]) for months in slots for index in range(1, len(months))
            ]

            # volume get bigger if diffs are big
            volume = sum(diffs) / len(diffs)
            volumes.append(volume)

            """
            1. BPM calculation
                1. Reference Offset: (volume - self.config[“reference”]): calculates the difference between the current decade’s volatility and the reference value.
                2. Scaling and Slope: Dividing by `window` and then multiplying by `slope` controls the sensitivity of volatility’s effect on tempo.
                3. self.config[“base”] sets the base tempo (e.g., 68 BPM by default).
                4. Using `min` and `ceiling`, as well as `max` and `floor`, strictly enforces the upper and lower limits of BPM, preventing excessive fluctuations
                5. `tempo_map.append((bar, bpm))` records “in which year (bar), the tempo changed to what BPM.”
            2. Musical Expressiveness
                1. More turbulent the climate, more urgent the music
                   When a particular year experiences drastic fluctuations between extreme cold and heat (increased volume), 
                   the overall tempo (BPM) automatically accelerates, creating an auditory experience of restlessness, tension, and oppression.
                2. More stable the climate, more melodious the music
                   Conversely, when the climate is stable, the tempo returns to the baseline, presenting a smooth rhythm.
            """
            bpm = int(
                max(
                    self.config["floor"],
                    min(
                        self.config["ceiling"],
                        round(self.config["base"] + (volume - self.config["reference"]) / self.config["window"] * self.config["slope"])
                    )
                )
            )

            tempo_map.append((bar, bpm))

        return tempo_map, volumes
