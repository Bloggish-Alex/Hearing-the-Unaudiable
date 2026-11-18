"""
Render a Composition as ABC notation.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

from ..model import Composition, Note, Section

DYNAMICS = ["!p!", "!mp!", "!mf!", "!f!", "!ff!"]
DEFAULT_DYNAMIC_THRESHOLDS = [-0.4, 0.05, 0.5, 0.95, 1.4]
DEFAULT_CREDIT = "Data: NASA GISTEMP v4 + NOAA Mauna Loa CO2. Public domain."
DEFAULT_COMMENTS = [
    "temperature: A minor pentatonic A3-A5; pitch=anomaly, rhythm=volatility",
    "CO2: D Dorian D3-D4, one long note every 2 years, enters 1958",
    "contrast: NH-SH -> A minor pentatonic A5-A6, one sustained note per year",
    "form: 10-bar decades; breath rests at bars 4 and 8; cadence + motif at bar 10",
]

VOICE_NAMES = {
    0: "Temperature (flute)",
    1: "Bass (cello)",
    2: "CO2 (bassoon)",
    3: "Decade motif (glockenspiel)",
    4: "Hemispheres (pad)",
}

VOICE_CLEFS = {
    0: "treble",
    1: "bass",
    2: "alto",
    3: "treble",
    4: "treble",
}

SHARP_LETTERS = {
    0: "C",
    1: "^C",
    2: "D",
    3: "^D",
    4: "E",
    5: "F",
    6: "^F",
    7: "G",
    8: "^G",
    9: "A",
    10: "^A",
    11: "B",
}

FLAT_LETTERS = {
    0: "C",
    1: "_D",
    2: "D",
    3: "_E",
    4: "E",
    5: "F",
    6: "_G",
    7: "G",
    8: "_A",
    9: "A",
    10: "_B",
    11: "B",
}


class ABCWriter:
    def __init__(
        self,
        eighth: int = 240,
        bar_ticks: int = 2880,
        section_bars: int = 10,
        config: dict | None = None,
    ):
        render_config = config or {}
        abc = render_config.get("abc", render_config)

        self.eighth = eighth
        self.bar_ticks = bar_ticks
        self.section_bars = section_bars

        self.key = str(abc.get("key", "Am"))
        self.time_signature = tuple(abc.get("time_signature", (12, 8)))
        self.tempo_unit = str(abc.get("tempo_unit", "3/8"))
        self.default_length = str(abc.get("default_length", "1/8"))

        self.length_mode = abc.get("length_mode", "legacy")
        if self.length_mode not in ("legacy", "exact"):
            raise ValueError("abc.length_mode must be 'legacy' or 'exact'")

        self.accidentals = abc.get("accidentals", "sharps")
        if self.accidentals not in ("sharps", "flats"):
            raise ValueError("abc.accidentals must be 'sharps' or 'flats'")

        self.emit_midi_program = bool(abc.get("emit_midi_program", False))

        dynamics = abc.get("dynamics", {})
        self.dynamics_marks = dynamics.get("marks", DYNAMICS)
        self.dynamics_thresholds = dynamics.get("thresholds", DEFAULT_DYNAMIC_THRESHOLDS)
        self.default_dynamics = dynamics.get("default", "!mf!")

        self.voice_names = {
            **VOICE_NAMES,
            **{int(key): value for key, value in abc.get("voice_names", {}).items()}
        }

        self.voice_clefs = {
            **VOICE_CLEFS,
            **{int(key): value for key, value in abc.get("voice_clefs", {}).items()}
        }

        self.credit = abc.get("credit", DEFAULT_CREDIT)
        self.comments = list(abc.get("comments", DEFAULT_COMMENTS))

        self.midi_programs = {
            int(key): value for key, value in render_config.get("midi_program", {}).items()
        }

        self.length_unit_ticks = (Fraction(8 * self.eighth) * Fraction(self.default_length))
        if self.length_unit_ticks <= 0:
            raise ValueError("abc.default_length must be positive")

        self.bar_slots = float(Fraction(self.bar_ticks) / self.length_unit_ticks)

    @staticmethod
    def pitch(midi: int, accidentals: str = "sharps") -> str:
        letters = FLAT_LETTERS if accidentals == "flats" else SHARP_LETTERS
        letter = letters[midi % 12]

        octave = midi // 12 - 1
        if octave >= 5:
            return letter.lower() + "'" * (octave - 5)

        return letter + "," * max(0, 4 - octave)

    @staticmethod
    def length(dur_eighths: float) -> str:
        if dur_eighths == 1:
            return ""

        if dur_eighths == 0.5:
            return "/2"

        return str(int(dur_eighths))

    @staticmethod
    def _exact_length(duration: float) -> str:
        value = Fraction(duration).limit_denominator(960)
        if value.denominator == 1:
            return "" if value.numerator == 1 else str(value.numerator)

        if value.numerator == 1:
            return f"/{value.denominator}"

        return f"{value.numerator}/{value.denominator}"

    def _format_length(self, duration: float) -> str:
        if self.length_mode == "exact":
            return self._exact_length(duration)

        return self.length(duration)

    def by_bar(self, notes: list[Note]) -> dict[int, list[Note]]:
        bars: dict[int, list[Note]] = {}

        for note in notes:
            bars.setdefault(note.tick // self.bar_ticks, []).append(note)

        for notes_in_bar in bars.values():
            notes_in_bar.sort(key=lambda note: note.tick)

        return bars

    def render_bar(self, notes: list[Note], bar: int) -> str:
        unit = float(self.length_unit_ticks)
        out, slot = [], 0.0

        for note in notes:
            start = (note.tick - bar * self.bar_ticks) / unit
            if start > slot:
                out.append("z" + self._format_length(start - slot))

            duration = note.dur / unit
            out.append(
                self.pitch(note.midi, self.accidentals)
                + self._format_length(duration)
            )
            slot = max(slot, start + duration)

        if slot < self.bar_slots:
            out.append("z" + self._format_length(self.bar_slots - slot))
            slot = self.bar_slots

        assert abs(slot - self.bar_slots) < 1e-6, (bar, slot, out)

        return " ".join(out)

    @staticmethod
    def _clef(notes: list[Note]) -> str:
        if not notes:
            return "treble"

        pitches = sorted(note.midi for note in notes)

        return "bass" if pitches[len(pitches) // 2] < 60 else "treble"

    def _dynamic(self, mean: float | None) -> str:
        if mean is None:
            return self.default_dynamics

        index = 0
        for position, threshold in enumerate(self.dynamics_thresholds):
            if mean >= threshold:
                index = position

        return self.dynamics_marks[
            min(index, len(self.dynamics_marks) - 1)
        ]

    def _sections(self, composition: Composition) -> list[Section]:
        if composition.sections:
            return composition.sections

        return [
            Section(
                label=str(start),
                start=start,
                end=min(start + self.section_bars, composition.n_bars),
            )
            for start in range(0, composition.n_bars, self.section_bars)
        ]

    def write(self, composition: Composition, path: Path) -> None:
        if not composition.tempo_map:
            raise ValueError("composition has no tempo map")

        voices = sorted(composition.voices, key=lambda voice: voice.id)
        voice_numbers = {
            voice.id: index for index, voice in enumerate(voices, 1)
        }
        bars_by_voice = {
            voice.id: self.by_bar(voice.notes) for voice in voices
        }

        start_year = composition.meta.get("start_year")
        end_year = composition.meta.get("end_year")
        title = composition.meta.get("title", "One Hundred Years of Warming")

        if start_year is not None and end_year is not None:
            title = f"{title} ({start_year}-{end_year})"

        numerator, denominator = self.time_signature

        lines = ["X:1", f"T:{title}"]

        if self.credit:
            lines.append(f"C:{self.credit}")

        lines.extend(
            [
                f"M:{numerator}/{denominator}",
                f"L:{self.default_length}",
                f"Q:{self.tempo_unit}={composition.tempo_map[0][1]}",
                f"K:{self.key}",
            ]
        )

        for voice in voices:
            number = voice_numbers[voice.id]
            name = self.voice_names.get(voice.id, voice.label)
            clef = self.voice_clefs.get(voice.id, self._clef(voice.notes))

            lines.append(f'V:{number} name="{name}" clef={clef}')

            if self.emit_midi_program:
                program = self.midi_programs.get(voice.id)
                if program is not None:
                    lines.append(f"%%MIDI program {program}")

        if self.comments:
            lines.append("")
            for comment in self.comments:
                lines.append(comment if comment.startswith("%") else f"% {comment}")

        tempo_by_bar = dict(composition.tempo_map)

        for section in self._sections(composition):
            bpm = tempo_by_bar.get(section.start, composition.tempo_map[0][1])
            dyn_mark = self._dynamic(section.mean)

            lines.append(f"% ===== {section.label}s =====")

            voice_lines = []
            for voice in voices:
                number = voice_numbers[voice.id]
                if number == 1:
                    tokens = [f"[V:{number}] [Q:{self.tempo_unit}={bpm}] {dyn_mark}"]
                else:
                    tokens = [f"[V:{number}]"]

                for bar in range(section.start, section.end):
                    tokens.append(self.render_bar(bars_by_voice[voice.id].get(bar, []), bar) + " |")

                voice_lines.append(" ".join(tokens))

            lines.extend(voice_lines)
            lines.append("")

        path.write_text("\n".join(lines) + "\n")
