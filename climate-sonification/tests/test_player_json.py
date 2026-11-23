"""
Tests for the web-player JSON renderer and CLI flag.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sonify.cli import main
from sonify.model import (
    Annotation,
    Composition,
    Dataset,
    Note,
    Period,
    Section,
    Series,
    Voice,
)
from sonify.render import PlayerJsonWriter


def sample():
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
        sections=[Section("2000", 0, 2, anchor=2000.0, mean=0.1)],
        meta={
            "title": "Test",
            "start_year": 2000,
            "end_year": 2001,
            "co2_entry_year": 2001,
        },
    )
    data = Dataset(
        periods=[
            Period("2000", 2000.0, 2001.0),
            Period("2001", 2001.0, 2002.0),
        ],
        series={
            "temp": Series(
                "temp", [0.1, 0.2], label="Temperature", unit="°C"
            ),
            "co2": Series("co2", [None, 315.0], label="CO₂", unit="ppm"),
            "contrast": Series(
                "contrast", [0.0, 0.1], label="NH−SH", unit="°C"
            ),
        },
        annotations=[Annotation(2001.0, "CO₂ enters")],
    )
    return composition, data


class PlayerJsonWriterTest(unittest.TestCase):
    def test_build(self) -> None:
        composition, data = sample()
        song = PlayerJsonWriter(bar_ticks=2880).build(composition, data)

        self.assertEqual(song["meta"]["start"], 2000)
        self.assertEqual(song["meta"]["end"], 2001)
        self.assertEqual(song["meta"]["duration"], 8.0)
        self.assertEqual(song["meta"]["co2Entry"], 2001)
        self.assertEqual(song["meta"]["counts"], {"melody": 2})
        self.assertEqual(song["bars"][0], {"year": 2000, "label": "2000", "t": 0.0, "d": 4.0})
        self.assertEqual(song["sections"][0]["year"], 2000)
        self.assertEqual(song["sections"][0]["mean"], 0.1)
        self.assertEqual(song["series"]["years"], [2000, 2001])
        self.assertEqual(song["series"]["temp"], [0.1, 0.2])
        self.assertEqual(song["series"]["co2"], [None, 315.0])
        self.assertEqual(song["series"]["contrast"], [0.0, 0.1])
        self.assertEqual(song["annotations"], [{"at": 2001, "label": "CO₂ enters"}])
        self.assertEqual(song["voices"][0]["id"], 0)
        self.assertEqual(len(song["notes"]), 2)
        self.assertEqual(song["notes"][0]["vc"], 0)
        self.assertEqual(song["notes"][0]["m"], 60)
        self.assertEqual(song["notes"][1]["m"], 62)

        presentation = song["presentation"]
        self.assertEqual(presentation["header"]["title"], "Test")
        self.assertEqual(presentation["readout"][0]["kind"], "period")
        self.assertEqual(presentation["readout"][-1]["kind"], "tempo")
        self.assertEqual(presentation["voices"][0]["id"], 0)
        self.assertEqual(presentation["voices"][0]["label"], "melody")

    def test_presentation_config(self) -> None:
        composition, data = sample()
        config = {
            "player": {
                "presentation": {
                    "header": {
                        "eyebrow": "EYEBROW",
                        "title": "Title",
                        "accent": "Accent",
                        "dek": "Dek",
                        "footer": ["Footer"],
                    },
                    "readout": [
                        {"kind": "period", "label": "YEAR"},
                        {
                            "label": "X",
                            "series": "temp",
                            "format": "signed",
                            "decimals": 1,
                            "unit": "°C",
                            "color": "#123456",
                        },
                    ],
                    "voices": [
                        {
                            "id": 0,
                            "label": "Lead",
                            "instrument": "flute",
                            "color": "#abcdef",
                            "alpha": 0.7,
                        }
                    ],
                }
            }
        }
        song = PlayerJsonWriter(bar_ticks=2880, config=config).build(
            composition, data
        )
        presentation = song["presentation"]
        self.assertEqual(presentation["header"]["eyebrow"], "EYEBROW")
        self.assertEqual(presentation["header"]["title"], "Title")
        self.assertEqual(presentation["header"]["accent"], "Accent")
        self.assertEqual(presentation["header"]["dek"], "Dek")
        self.assertEqual(presentation["header"]["footer"], ["Footer"])
        self.assertEqual(presentation["readout"][1]["color"], "#123456")
        self.assertEqual(presentation["voices"][0]["label"], "Lead")
        self.assertEqual(presentation["voices"][0]["instrument"], "flute")
        self.assertEqual(presentation["voices"][0]["color"], "#abcdef")
        self.assertEqual(presentation["voices"][0]["alpha"], 0.7)

    def test_javascript_and_json_output(self) -> None:
        composition, data = sample()
        writer = PlayerJsonWriter(bar_ticks=2880)

        with tempfile.TemporaryDirectory() as tmp:
            js_path = Path(tmp) / "player.js"
            json_path = Path(tmp) / "player.json"
            writer.write(composition, data, js_path)
            writer.write(composition, data, json_path, javascript=False)

            text = js_path.read_text()
            self.assertTrue(text.startswith("window.SONG = "))
            self.assertTrue(text.endswith(";\n"))
            payload = json.loads(text[len("window.SONG = ") : -2])
            self.assertEqual(payload["meta"]["title"], "Test")

            plain = json.loads(json_path.read_text())
            self.assertEqual(plain["schema"], "sonify/1")


class CliPlayerTest(unittest.TestCase):
    def test_cli_writes_player_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "climate"
            player_path = Path(tmp) / "player" / "player_data.js"
            code = main(
                [
                    "--profile",
                    str(ROOT / "profiles" / "climate.yaml"),
                    "--out",
                    str(out),
                    "--voices",
                    "1",
                    "--player-out",
                    str(player_path),
                ]
            )
            self.assertEqual(code, 0)

            text = player_path.read_text()
            self.assertTrue(text.startswith("window.SONG = "))
            payload = json.loads(text[len("window.SONG = ") : -2])
            self.assertEqual(list(payload["meta"]["counts"]), ["bass"])
            self.assertEqual(payload["meta"]["co2Entry"], 1958)
            self.assertTrue(all(note["vc"] == 1 for note in payload["notes"]))
            self.assertIn("temp", payload["series"])
            self.assertIn("co2", payload["series"])
            self.assertIn("contrast", payload["series"])
            presentation = payload["presentation"]
            self.assertEqual(presentation["header"]["title"], "One Hundred Years")
            self.assertEqual(presentation["header"]["accent"], "of Warming")
            self.assertEqual(presentation["readout"][1]["series"], "temp")
            self.assertEqual(presentation["voices"][0]["id"], 1)
            self.assertEqual(presentation["voices"][0]["label"], "Bass")
            self.assertEqual(presentation["voices"][0]["instrument"], "cello")


if __name__ == "__main__":
    unittest.main()
