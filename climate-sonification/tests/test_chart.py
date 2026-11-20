"""
Tests for the chart/PNG renderer.
"""

from __future__ import annotations

import struct
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
from sonify.render import ChartWriter


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
            ),
            Voice(1, "bass", [Note(0, 2880, 45, 80, 1)]),
        ],
        tempo_map=[(0, 60)],
        n_bars=2,
        sections=[Section("2000", 0, 2, anchor=2000.0, mean=0.1)],
        meta={"title": "Chart test"},
    )
    data = Dataset(
        periods=[
            Period("2000", 2000.0, 2001.0),
            Period("2001", 2001.0, 2002.0),
        ],
        series={
            "temp": Series("temp", [0.1, 0.2], label="Temp", unit="°C"),
            "co2": Series("co2", [None, 315.0], label="CO₂", unit="ppm"),
            "contrast": Series(
                "contrast", [0.0, 0.1], label="NH−SH", unit="°C"
            ),
        },
        annotations=[Annotation(2001.0, "CO₂ enters")],
    )
    config = {
        "chart": {
            "title": "Test chart",
            "x_label": "Year",
            "series": [
                {"id": "temp", "axis": "left", "color": "#e74c3c"},
                {"id": "co2", "axis": "right", "color": "#16a085"},
                {"id": "contrast", "axis": "left", "color": "#9b59b6"},
            ],
            "voices": {
                0: {"color": "#e67e22", "alpha": 0.85},
                1: {"color": "#3498db", "alpha": 0.55},
            },
            "register_lines": [{"midi": 50, "color": "#1abc9c"}],
        }
    }
    return composition, data, config


class ChartWriterTest(unittest.TestCase):
    def test_writes_png(self) -> None:
        composition, data, config = sample()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chart.png"
            ChartWriter(
                composition,
                data,
                bar_ticks=2880,
                config=config,
            ).write(path)
            payload = path.read_bytes()

        self.assertEqual(payload[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", payload[16:24])
        self.assertGreater(width, 0)
        self.assertGreater(height, 0)
        self.assertGreater(len(payload), 1000)

    def test_cli_chart_flag(self) -> None:
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
                    "--chart",
                ]
            )
            self.assertEqual(code, 0)
            payload = out.with_suffix(".png").read_bytes()
        self.assertEqual(payload[:8], b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()
