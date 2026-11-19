"""
Render a Composition + Dataset as the web player payload.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..model import Composition, Dataset


class PlayerJsonWriter:
    def __init__(self, bar_ticks: int = 2880, config: dict | None = None):
        self.bar_ticks = bar_ticks
        self.config = (config or {}).get("player", {})

    @staticmethod
    def _number(value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return value
        return int(number) if number.is_integer() else round(number, 4)

    @staticmethod
    def _values(values, precision: int = 3):
        return [
            None if value is None else round(value, precision) for value in values
        ]

    def build_bars(self, composition: Composition, data: Dataset) -> dict:
        """
        Returns bars in JSON format:
            {
                "year":,
                "label":,
                "t",
                "d"
            }
        """
        times, total = composition.bar_times() # start time of each bar (year) and total duration in seconds
        periods = data.periods

        bars = []
        for index, period in enumerate(periods):
            # duration of each period (bar)
            duration = (
                times[index + 1] - times[index] if index + 1 < len(times) else total - times[index]
            )

            bars.append(
                {
                    "year": self._number(period.start), # year in number
                    "label": period.label, # year in str
                    "t": round(times[index], 4), # start time
                    "d": round(duration, 4), # duration
                }
            )
        return bars

    def build_notes(self, composition: Composition, bars: list[dict]) -> dict:
        """
        Bar index for a note: tick // bar_ticks
        Note start inside a bar: (tick % bar_ticks)
        """
        notes = []
        for note in composition.notes:
            bar = note.tick // self.bar_ticks
            bar_duration = bars[bar]["d"]
            t = (bars[bar]["t"] + (note.tick - bar * self.bar_ticks) / self.bar_ticks * bar_duration)

            entry = {
                "t": round(t, 4),
                "d": round(note.dur / self.bar_ticks * bar_duration, 4),
                "m": note.midi,
                "v": note.vel,
                "vc": note.voice
            }

            if note.art:
                entry["art"] = note.art

            notes.append(entry)

        notes.sort(key=lambda item: (item["t"], item["vc"], item["m"]))

        return notes    

    def build_sections(self, composition: Composition, data: Dataset) -> dict:
        _, total = composition.bar_times()
        periods = data.periods

        sections = []
        for section in composition.sections:
            anchor = section.anchor
            if anchor is None and 0 <= section.start < len(periods):
                anchor = periods[section.start].start

            sections.append(
                {
                    "year": self._number(anchor) if anchor is not None else section.label,
                    "label": section.label,
                    "start": section.start,
                    "end": section.end,
                    "mean": (round(section.mean, 3) if section.mean is not None else None)
                }
            )

        return sections

    def build_series(self, data: Dataset) -> dict:
        periods = data.periods

        series: dict = {"years": [self._number(period.start) for period in periods]}
        series_meta: dict = {}

        for series_id, values in data.series.items():
            if series_id != "years":
                series[series_id] = self._values(values.values)

            series_meta[series_id] = {
                "label": values.label,
                "unit": values.unit
            }

        return series, series_meta

    def build_co2_entry(self, composition: Composition, data: Dataset):
        periods = data.periods

        co2_entry = composition.meta.get("co2_entry_year")
        if co2_entry is None:
            co2 = data.series.get("co2")
            if co2 is not None:
                index = next((i for i, value in enumerate(co2.values) if value is not None), None)

                if index is not None:
                    co2_entry = self._number(periods[index].start)

        return co2_entry

    def build(self, composition: Composition, data: Dataset) -> dict:
        _, total = composition.bar_times()
        periods = data.periods

        bars = self.build_bars(composition, data)
        notes = self.build_notes(composition, bars)
        sections = self.build_sections(composition, data)
        series, series_meta = self.build_series(data)
        co2_entry = self.build_co2_entry(composition, data)

        start = self._number(periods[0].start) if periods else None
        end = self._number(periods[-1].start) if periods else None
        subtitle = self.config.get("subtitle", composition.meta.get("subtitle", ""))
        counts = {
            voice.label: len(voice.notes) for voice in composition.voices
        }

        return {
            "schema": "sonify/1",
            "meta": {
                "title": composition.meta.get("title", ""),
                "subtitle": subtitle,
                "start": start,
                "end": end,
                "duration": round(total, 3),
                "co2Entry": co2_entry,
                "counts": counts,
            },
            "bars": bars,
            "tempo": [[bar, bpm] for bar, bpm in composition.tempo_map],
            "sections": sections,
            "series": series,
            "series_meta": series_meta,
            "annotations": [
                {"at": self._number(a.at), "label": a.label} for a in data.annotations
            ],
            "voices": [
                {
                    "id": voice.id,
                    "label": voice.label,
                    "count": len(voice.notes),
                }
                for voice in composition.voices
            ],
            "notes": notes,
        }

    def write(
        self,
        composition: Composition,
        data: Dataset,
        path: Path,
        javascript: bool = True,
    ) -> dict:
        song = self.build(composition, data)
        text = json.dumps(song, ensure_ascii=False, separators=(",", ":"))
        if javascript:
            path.write_text("window.SONG = " + text + ";\n")
        else:
            path.write_text(text + "\n")
        return song
