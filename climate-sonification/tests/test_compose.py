"""
Composition tests against the legacy climate output.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sonify.compose import Composer
from sonify.model import Note
from sonify.profile import Profile
from sonify.sources import ClimateSource


class ClimateCompositionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = Profile.load(ROOT / "profiles" / "climate.yaml")
        dataset = ClimateSource(
            cls.profile.directory,
            cls.profile.start_year,
            cls.profile.end_year,
        ).load()
        cls.composition = Composer(cls.profile).compose(dataset)
        cls.notes = {
            voice.id: voice.notes for voice in cls.composition.voices
        }

    def test_profile_paths_and_scales(self) -> None:
        self.assertEqual(self.profile.directory, ROOT / "data")
        self.assertEqual(self.profile.timing.bar_ticks, 2880)
        self.assertEqual(self.profile.scales["temperature"].root, 57)

    def test_voice_counts(self) -> None:
        self.assertEqual(
            {
                voice_id: len(notes)
                for voice_id, notes in self.notes.items()
            },
            {0: 816},
        )

    def test_tempo_map(self) -> None:
        self.assertEqual(
            self.composition.tempo_map,
            [
                (0, 82),
                (10, 78),
                (20, 75),
                (30, 80),
                (40, 85),
                (50, 94),
                (60, 94),
                (70, 103),
                (80, 89),
                (90, 92),
            ],
        )

    def test_decade_volumes(self) -> None:
        self.assertEqual(
            [
                round(value, 6)
                for value in self.composition.meta["decade_volumes"]
            ],
            [
                0.086455,
                0.083182,
                0.080909,
                0.084273,
                0.088182,
                0.096,
                0.095727,
                0.103091,
                0.091818,
                0.093909,
            ],
        )

    def test_co2_entry(self) -> None:
        self.assertEqual(self.composition.meta["co2_start_bar"], 33)
        self.assertEqual(self.composition.meta["co2_entry_year"], 1958)

    def test_duration(self) -> None:
        _, total = self.composition.bar_times()
        self.assertAlmostEqual(total, 277.690867, places=6)

    def test_first_notes(self) -> None:
        self.assertEqual(self.notes[0][0], Note(0, 66, 60, 66, 0, -1))

    def test_sections(self) -> None:
        self.assertEqual(len(self.composition.sections), 10)
        self.assertEqual(self.composition.sections[0].start, 0)
        self.assertEqual(self.composition.sections[0].end, 10)
        self.assertEqual(self.composition.sections[-1].start, 90)
        self.assertEqual(self.composition.sections[-1].end, 100)


if __name__ == "__main__":
    unittest.main()
