"""
Tests for the ABC notation renderer.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sonify.model import Composition, Note, Section, Voice
from sonify.render import ABCWriter


class ABCWriterTest(unittest.TestCase):
    def test_pitch(self) -> None:
        self.assertEqual(ABCWriter.pitch(57), "A,")
        self.assertEqual(ABCWriter.pitch(60), "C")
        self.assertEqual(ABCWriter.pitch(69), "A")
        self.assertEqual(ABCWriter.pitch(81), "a")
        self.assertEqual(ABCWriter.pitch(84), "c'")

    def test_length(self) -> None:
        self.assertEqual(ABCWriter.length(1), "")
        self.assertEqual(ABCWriter.length(0.5), "/2")
        self.assertEqual(ABCWriter.length(2), "2")
        # Legacy behavior: fractional durations are truncated.
        self.assertEqual(ABCWriter.length(66 / 240), "0")

    def test_length_modes(self) -> None:
        legacy = ABCWriter()
        exact = ABCWriter(config={"abc": {"length_mode": "exact"}})
        self.assertEqual(legacy._format_length(66 / 240), "0")
        self.assertEqual(exact._format_length(66 / 240), "11/40")

    def test_accidental_spelling(self) -> None:
        self.assertEqual(ABCWriter.pitch(61, "sharps"), "^C")
        self.assertEqual(ABCWriter.pitch(61, "flats"), "_D")

    def test_writes_header_voices_and_bars(self) -> None:
        composition = Composition(
            voices=[
                Voice(
                    0,
                    "melody",
                    [
                        Note(0, 240, 60, 100, 0),
                        Note(240, 480, 62, 90, 0),
                    ],
                ),
                Voice(1, "bass", [Note(0, 2880, 45, 80, 1)]),
            ],
            tempo_map=[(0, 60)],
            n_bars=1,
            sections=[Section("2000", 0, 1, mean=0.0)],
            meta={
                "title": "test",
                "start_year": 2000,
                "end_year": 2000,
            },
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.abc"
            ABCWriter(
                eighth=240,
                bar_ticks=2880,
                section_bars=10,
            ).write(composition, path)
            text = path.read_text()

        self.assertIn("X:1", text)
        self.assertIn("T:test (2000-2000)", text)
        self.assertIn("M:12/8", text)
        self.assertIn("L:1/8", text)
        self.assertIn("Q:3/8=60", text)
        self.assertIn("K:Am", text)
        self.assertIn('V:1 name="Temperature (flute)" clef=treble', text)
        self.assertIn('V:2 name="Bass (cello)" clef=bass', text)
        self.assertIn("% ===== 2000s =====", text)
        self.assertIn("[V:1] [Q:3/8=60] !p!", text)
        self.assertEqual(text.count("|"), 2)

    def test_configuration_overrides(self) -> None:
        composition = Composition(
            voices=[
                Voice(0, "melody", [Note(0, 1440, 61, 100, 0)]),
            ],
            tempo_map=[(0, 60)],
            n_bars=1,
            sections=[Section("2000", 0, 1, mean=0.0)],
            meta={
                "title": "config test",
                "start_year": 2000,
                "end_year": 2000,
            },
        )
        config = {
            "midi_program": {0: 1},
            "abc": {
                "key": "Dm",
                "time_signature": [3, 4],
                "tempo_unit": "1/4",
                "default_length": "1/4",
                "length_mode": "exact",
                "accidentals": "flats",
                "emit_midi_program": True,
                "dynamics": {
                    "marks": ["!pp!", "!ff!"],
                    "thresholds": [-1, 1],
                    "default": "!pp!",
                },
                "voice_names": {0: "Lead"},
                "voice_clefs": {0: "alto"},
                "credit": "Test credit",
                "comments": ["hello"],
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.abc"
            ABCWriter(
                eighth=240,
                bar_ticks=1440,
                config=config,
            ).write(composition, path)
            text = path.read_text()

        self.assertIn("M:3/4", text)
        self.assertIn("L:1/4", text)
        self.assertIn("Q:1/4=60", text)
        self.assertIn("K:Dm", text)
        self.assertIn('V:1 name="Lead" clef=alto', text)
        self.assertIn("%%MIDI program 1", text)
        self.assertIn("C:Test credit", text)
        self.assertIn("% hello", text)
        self.assertIn("[V:1] [Q:1/4=60] !pp!", text)
        self.assertIn("_D3", text)
        self.assertEqual(text.count("|"), 1)


if __name__ == "__main__":
    unittest.main()
