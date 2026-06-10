from __future__ import annotations
from dataclasses import dataclass
from body_profile import BodyProfile

# Minimum wearing ease (Aldrich/Armstrong), in cm (converted from inches)
_EASE: dict[str, float] = {
    "bust":     5.08,  # 2 in
    "waist":    2.54,  # 1 in
    "hip":      3.81,  # 1.5 in
    "shoulder": 0.0,
    "inseam":   0.0,
    "length":   0.0,
}

_TOLERANCE = 0.5  # cm — delta within this range needs no alteration


@dataclass
class GarmentMeasurements:
    garment_type: str
    bust:     float | None = None
    waist:    float | None = None
    hip:      float | None = None
    inseam:   float | None = None
    shoulder: float | None = None
    length:   float | None = None


@dataclass
class AlterationInstruction:
    zone:        str
    delta_cm:    float  # positive = garment too big; negative = too small
    instruction: str


def compute_alterations(
    profile: BodyProfile,
    garment: GarmentMeasurements,
) -> list[AlterationInstruction]:
    instructions: list[AlterationInstruction] = []

    zones = {
        "bust":     (getattr(profile, "bust",     None), garment.bust),
        "waist":    (getattr(profile, "waist",    None), garment.waist),
        "hip":      (getattr(profile, "hip",      None), garment.hip),
        "inseam":   (getattr(profile, "inseam",   None), garment.inseam),
        "shoulder": (getattr(profile, "shoulder", None), garment.shoulder),
    }

    for zone, (body_val, garment_val) in zones.items():
        if garment_val is None or body_val is None:
            continue
        ease = _EASE.get(zone, 0.0)
        target = body_val + ease
        delta = garment_val - target
        if abs(delta) <= _TOLERANCE:
            continue
        if delta > 0:
            instruction = f"take in {zone} by {delta:.1f} cm"
        else:
            instruction = f"let out {zone} by {abs(delta):.1f} cm"
        instructions.append(AlterationInstruction(zone=zone, delta_cm=delta, instruction=instruction))

    return instructions
