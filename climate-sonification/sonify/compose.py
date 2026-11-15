"""
Compose a Dataset into a score using a Profile.
"""

from __future__ import annotations

from .model import Composition, Dataset, Section, Voice
from .profile import Profile
from .voices import SectionForm, VoiceContext, build_generator


class Composer:

    def __init__(self, profile: Profile):
        self.profile = profile

    def compose(self, dataset: Dataset) -> Composition:
        timing = self.profile.timing
        form_config = self.profile.form
        ctx = VoiceContext(dataset=dataset, timing=timing)

        specs = {spec.id: spec for spec in self.profile.voices}
        voices: dict[int, Voice] = {}

        # generate notes for every voice declared in the profile
        for spec in self.profile.voices:
            scale = self.profile.scales[spec.scale] if spec.scale else None

            generator = build_generator(
                spec.generator, # generator name
                spec.id,
                spec.series,    # section in dataset
                spec.options,
                scale,
            )

            voices[spec.id] = Voice(
                spec.id, spec.name, generator.generate(ctx)
            )

        co2_start_bar = next(
            (
                index
                for index, value in enumerate(dataset.series["co2"].values)
                if value is not None
            ),
            None
        )

        composition = Composition(
            voices=[voices[index] for index in sorted(voices)],
            tempo_map=[],
            n_bars=len(dataset.periods),
            sections=self._sections(dataset),
            meta={
                **dataset.meta,
                "title": self.profile.title,
                "co2_start_bar": co2_start_bar
            }
        )

        # post-processing stage over the whole composition
        melody_id = form_config["cadence"]["voice"]
        melody_spec = specs[melody_id]
        if melody_spec.scale is None:
            raise ValueError("The melody voice must declare a scale")

        return SectionForm(form_config, timing).apply(
            composition,
            dataset,
            self.profile.scales[melody_spec.scale],
        )

    def _sections(self, dataset: Dataset) -> list[Section]:
        section_bars = self.profile.timing.section_bars
        series = dataset.series[self.profile.form.get("series", "temp")]
        sections = []

        for start in range(0, len(dataset.periods), section_bars):
            values = [
                value
                for value in series.values[start : start + section_bars]
                if value is not None
            ]
            sections.append(
                Section(
                    label=str(int(dataset.periods[start].start)),
                    start=start,
                    end=min(start + section_bars, len(dataset.periods)),
                    anchor=dataset.periods[start].start,
                    mean=sum(values) / len(values) if values else None
                )
            )

        return sections
