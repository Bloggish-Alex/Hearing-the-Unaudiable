"""
Tests for the MIDI/audio renderers and the CLI.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import mido

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sonify.cli import main
from sonify.model import Composition, Note, Voice
from sonify.render import MidiWriter


class MidiWriterTest(unittest.TestCase):
    def test_writes_tempo_time_signature_and_notes(self) -> None:
        composition = Composition(
            voices=[
                Voice(
                    0,
                    "melody",
                    [
                        Note(0, 480, 60, 100, 0),
                        Note(480, 240, 62, 90, 0),
                    ],
                )
            ],
            tempo_map=[(0, 60)],
            n_bars=2,
            meta={"title": "test"},
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.mid"
            MidiWriter(
                ticks_per_beat=480,
                bar_ticks=2880,
            ).write(composition, path)
            mid = mido.MidiFile(path)

        self.assertEqual(mid.ticks_per_beat, 480)
        messages = [message for track in mid.tracks for message in track]

        tempos = [message.tempo for message in messages if message.type == "set_tempo"]
        self.assertEqual(tempos[0], mido.bpm2tempo(90))  # 1.5 * 60 BPM

        signature = next(
            message for message in messages if message.type == "time_signature"
        )
        self.assertEqual((signature.numerator, signature.denominator), (12, 8))

        note_ons = [
            (message.note, message.velocity)
            for message in messages
            if message.type == "note_on"
        ]
        self.assertIn((60, 100), note_ons)
        self.assertIn((62, 90), note_ons)

        names = [
            message.name for message in messages if message.type == "track_name"
        ]
        self.assertIn("melody", names)


class CliTest(unittest.TestCase):
    def test_writes_midi_with_voice_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "climate"
            code = main(
                [
                    "--profile",
                    str(ROOT / "profiles" / "climate.yaml"),
                    "--out",
                    str(out),
                    "--voices",
                    "1",
                    "--abc",
                ]
            )
            self.assertEqual(code, 0)
            self.assertTrue(out.with_suffix(".mid").exists())
            self.assertTrue(out.with_suffix(".abc").exists())


if __name__ == "__main__":
    unittest.main()
