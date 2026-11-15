"""
Melody driven by intra-bar slots, one value per slot.
"""

from __future__ import annotations

from ..model import Note
from .base import VoiceContext, VoiceGenerator


class SlotsMelodyVoice(VoiceGenerator):
    """
    Melody is declared in profile like:

        - id: 0
            name: melody
            generator: slots_melody # predefined and hardcoded, don't change the name
            series: temp  # refer to form.series
            scale: temperature  # refer to scales.temperature
                root: 57
                steps: [0, 3, 5, 7, 10]
                lo: -0.6
                hi: 1.5
                max_degree: 10
            velocity: {base: 60, span: 55, floor: 45, ceiling: 118}
            split_velocity: {drop: 8, floor: 40}
            rhythm:
                split_delta: 0.22
                split_offset: 0.08
                hold_delta: 0.06
                hold_delta_step: 0.05
                hold_max: 3
                staccato_delta: 0.15
                duration_factor: 0.55
    """

    def generate(self, ctx: VoiceContext) -> list[Note]:
        if self.scale is None:
            raise ValueError("slots_melody requires a scale")

        series = ctx.dataset.series[self.series_id]
        if series.slots is None:
            raise ValueError(f"series {self.series_id!r} has no intra-bar slots")

        notes: list[Note] = []
        previous_bar_last = series.slots[0][-1]

        for bar, months in enumerate(series.slots):    # year, months (12 slots per bar)
            n_slots = len(months)
            slot = 0
            index = 0
            
            while index < n_slots:
                value = months[index]
                previous = months[index - 1] if index > 0 else previous_bar_last

                notes_in_slot, next_steps = self._generate_step(previous, value, bar, index, slot, months, ctx)

                notes.extend(notes_in_slot)
                slot += next_steps
                index += next_steps
            
            previous_bar_last = months[-1]

        return notes


    def _generate_step(self,
                       previous: float,
                       value: float,
                       bar: int,
                       index: int,
                       slot: int,
                       months: list[float],
                       ctx: VoiceContext) -> tuple[list[Note], int]:
        
        if self.scale is None:
            raise ValueError("slots_melody requires a scale")

        scale = self.scale

        rhythm = self.options["rhythm"]
        velocity = self.options["velocity"]
        split_velocity = self.options["split_velocity"]
        eighth = ctx.timing.eighth
        bar_ticks = ctx.timing.bar_ticks

        n_slots = len(months)
        delta = abs(value - previous)

        notes: list[Note] = []

        """
        A way of rhythm for sharp change, split on eighth into two sixteenth with different pitch, duration and velocity.
        Shorten the duration, increase pitch -> feel tension, suitable for sharp change
        """
        if delta > rhythm["split_delta"] and index + 1 < n_slots:
            first = scale.degree(value)

            offset = rhythm["split_offset"] if value >= previous else -rhythm["split_offset"]
            second = scale.degree(value + offset)

            """
            Reduce duration using duration_factor, like staccato, to intrudce a sense of tension,
            The start position is till the slot start position.
            """
            duration = int((eighth // 2) * rhythm["duration_factor"])
            tick = bar * bar_ticks + slot * eighth  # start position
            vel = self.velocity(value, scale, velocity)

            notes.append(
                Note(tick, duration, scale.midi(first), vel, self.voice_id, -1)
            )
            notes.append(
                Note(
                    tick + eighth // 2,
                    duration,
                    scale.midi(second),
                    max(split_velocity["floor"], vel - split_velocity["drop"]), # drop to simulate human                            
                    self.voice_id,
                    -1,
                )
            )

            next_steps = 1
        else:

            """
            Hold -> feel relax, suitable for smootch change, number of eighth slots                
            """
            hold = 1
            if delta < rhythm["hold_delta"]:
                hold = 2
                if (rhythm["hold_max"] >= 3 and
                    index + 2 < n_slots and
                    abs(months[index + 1] - value) < rhythm["hold_delta_step"] and
                    abs(months[index + 2] - months[index + 1]) < rhythm["hold_delta_step"]
                ): # hold for the next and the next of next delta?
                    hold = 3

            hold = min(hold, rhythm["hold_max"], n_slots - slot) # number of hold, allowed maximum holds, and left slots
            duration = hold * eighth
            tick = bar * bar_ticks + slot * eighth
            vel = self.velocity(value, scale, velocity)

            art = -1 if delta > rhythm["staccato_delta"] else 0
            if art == -1:
                duration = int(duration * rhythm["duration_factor"])

            notes.append(
                Note(
                    tick,
                    duration,
                    scale.midi(scale.degree(value)),
                    vel,
                    self.voice_id,
                    art,
                )
            )

            next_steps = hold

        return (notes, next_steps)