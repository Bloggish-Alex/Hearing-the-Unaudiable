from ..scales import Scale
from .base import VoiceContext, VoiceGenerator
from .section_form import SectionForm, TempoBuilder
from .slots_melody import SlotsMelodyVoice
from .bassline import BasslineVoice

GENERATORS: dict[str, type[VoiceGenerator]] = {
    "slots_melody": SlotsMelodyVoice,
    "bassline": BasslineVoice
}

__all__ = [
    "GENERATORS",
    "VoiceContext",
    "VoiceGenerator",
    "build_generator",
    "SlotsMelodyVoice",
    "BasslineVoice",
    "SectionForm",
    "TempoBuilder",
]


def build_generator(
    name: str,
    voice_id: int,
    series_id: str,
    options: dict,
    scale: Scale | None = None,
) -> VoiceGenerator:

    try:
        generator = GENERATORS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown voice generator {name!r}") from exc

    return generator(voice_id, series_id, options, scale)
