"""
Render a Composition + Dataset as a static chart PNG.
"""

from __future__ import annotations

from pathlib import Path

from ..model import Composition, Dataset

import matplotlib

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

matplotlib.use("Agg")


DEFAULT_SERIES_COLORS = [
    "#e74c3c",
    "#16a085"
]

DEFAULT_VOICE_STYLES = {
    0: ("#e67e22", 0.85),
    1: ("#3498db", 0.55)
}

DEFAULT_ANNOTATION_COLOR = "#16a085"


class ChartWriter:
    def __init__(
        self,
        composition: Composition,
        data: Dataset,
        bar_ticks: int = 2880,
        config: dict | None = None,
    ):
        self.composition = composition
        self.data = data
        self.bar_ticks = bar_ticks
        self.config = config.get("chart", {}) if config else {}

    def write(self, path: Path) -> None:

        if not self.data.periods:
            raise ValueError("dataset has no periods")
        if self.bar_ticks <= 0:
            raise ValueError("bar_ticks must be positive")

        config = self.config        

        figsize = tuple(config.get("figsize", (13, 8.4)))
        ratios = config.get("height_ratios", (1, 1.55))
        fig, (ax1, ax2) = plt.subplots(
            2,
            1,
            figsize=figsize,
            gridspec_kw={"height_ratios": ratios},
            sharex=True,
        )

        self._plot_data(ax1)
        self._plot_piano_roll(ax2)

        plt.tight_layout()
        path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(path, dpi=config.get("dpi", 180))
        plt.close(fig)


    def _plot_data(self, ax: plt.Axes) -> None:

        data = self.data
        config = self.config
        periods = data.periods

        xs = [period.start for period in periods]

        specs = config.get("series")
        if not specs:
            specs = [{"id": series_id, "axis": "left"} for series_id in data.series]

        right_specs = [
            spec for spec in specs if spec.get("axis") == "right" and spec.get("id") in data.series]

        ax1b = ax.twinx() if right_specs else None

        for index, spec in enumerate(specs):
            series_id = spec.get("id")
            series = data.series.get(series_id)
            if series is None:
                continue

            target = ax1b if spec.get("axis") == "right" else ax
            if target is None:
                target = ax

            color = spec.get("color", DEFAULT_SERIES_COLORS[index % len(DEFAULT_SERIES_COLORS)])

            values = [float("nan") if value is None else value for value in series.values]

            line, = target.plot(
                xs,
                values,
                color=color,
                lw=spec.get("width", 2.0),
                ls="--" if spec.get("dashed") else "-",
                label=spec.get("label", series.label or series_id),
            )
            if spec.get("fill"):
                target.fill_between(xs, values, 0, color=color, alpha=0.10)

        left_color = config.get("left_color")
        right_color = config.get("right_color")

        ax.set_ylabel(config.get("left_ylabel", ""))
        ax.tick_params(axis="y", labelcolor=left_color) if left_color else None

        if left_color:
            ax.yaxis.label.set_color(left_color)

        if ax1b is not None:
            ax1b.set_ylabel(config.get("right_ylabel", ""))
            if right_color:
                ax1b.tick_params(axis="y", labelcolor=right_color)
                ax1b.yaxis.label.set_color(right_color)

        if config.get("zero_line"):
            ax.axhline(
                0,
                color=config.get("zero_color", "#7f8c8d"),
                lw=0.8,
                ls="--",
            )

        ax.set_title(config.get("title", ""))
        handles, labels = ax.get_legend_handles_labels()

        if ax1b is not None:
            more_handles, more_labels = ax1b.get_legend_handles_labels()
            handles += more_handles
            labels += more_labels

        if handles and config.get("legend", True):
            ax.legend(handles, labels, loc="upper left", fontsize=8, frameon=False)

    def _plot_piano_roll(self, ax: plt.Axes) -> None:       

        comp = self.composition
        data = self.data
        config = self.config
        periods = data.periods

        voices_config = config.get("voices", {})
        register_lines = config.get("register_lines", [])

        xlim = (periods[0].start, periods[-1].end)

        midi_values = []
        for note in comp.notes:
            bar = note.tick // self.bar_ticks

            if bar < 0 or bar >= len(periods):
                continue

            period = periods[bar]
            span = period.end - period.start

            if span <= 0:
                span = 1.0

            fraction = (note.tick - bar * self.bar_ticks) / self.bar_ticks
            x = period.start + fraction * span
            width = note.dur / self.bar_ticks * span
            style = voices_config.get(note.voice) or voices_config.get(str(note.voice)) or {}
            default_color, default_alpha = DEFAULT_VOICE_STYLES.get(note.voice, ("#95a5a6", 0.8))

            ax.add_patch(
                Rectangle(
                    (x, note.midi - 0.35),
                    max(width, 0.004),
                    0.7,
                    color=style.get("color", default_color),
                    alpha=style.get("alpha", default_alpha),
                    lw=0,
                )
            )
            midi_values.append(note.midi)

        # draw register lines (pitch range)
        for register in register_lines:
            midi = register.get("midi")
            if midi is None:
                continue

            ax.axhline(
                midi,
                color=register.get("color", "#1abc9c"),
                lw=0.4,
                ls=":",
            )
            midi_values.append(midi)

        ax.set_ylabel(config.get("roll_ylabel", "MIDI pitch"))
        ax.set_xlabel(config.get("x_label", ""))
        ax.set_xlim(*xlim)
        ax.grid(axis="y", color="#ecf0f1", lw=0.6)

        if midi_values:
            y_min, y_max = min(midi_values), max(midi_values)
            ax.set_ylim(y_min - 8, y_max + 5)
            text_y = y_min - 4
        else:
            ax.set_ylim(0, 127)
            text_y = 10

        annotation_color = config.get("annotation_color", DEFAULT_ANNOTATION_COLOR)

        x_span = xlim[1] - xlim[0]
        for annotation in data.annotations:
            if not (xlim[0] <= annotation.at <= xlim[1]):
                continue
            ax.axvline(
                annotation.at,
                color=annotation_color,
                lw=1.0,
                ls="--",
                alpha=0.7,
            )
            ax.text(
                annotation.at + max(x_span * 0.01, 0.5),
                text_y,
                annotation.label,
                color=annotation_color,
                fontsize=8,
            )
