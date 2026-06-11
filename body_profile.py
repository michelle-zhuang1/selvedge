from __future__ import annotations
import json
from dataclasses import dataclass, asdict, fields
from pathlib import Path


@dataclass
class BodyProfile:
    # Core measurements (cm, required)
    bust: float
    waist: float
    hip: float
    inseam: float
    height: float
    shoulder: float
    # Extended measurements (cm, optional)
    arm: float | None = None
    wrist: float | None = None
    thigh: float | None = None
    rise: float | None = None
    back: float | None = None
    neck: float | None = None


_RANGES: dict[str, tuple[float, float]] = {
    "bust":     (60,  200),
    "waist":    (40,  200),
    "hip":      (60,  220),
    "inseam":   (50,  120),
    "height":   (100, 250),
    "shoulder": (20,  60),
    "arm":      (40,  80),
    "wrist":    (10,  30),
    "thigh":    (30,  100),
    "rise":     (15,  40),
    "back":     (30,  60),
    "neck":     (25,  60),
}


def validate(profile: BodyProfile) -> list[str]:
    warnings: list[str] = []
    for f in fields(profile):
        value = getattr(profile, f.name)
        if value is None:
            continue
        lo, hi = _RANGES[f.name]
        if not (lo <= value <= hi):
            warnings.append(
                f"{f.name}: {value} cm is outside expected range ({lo}–{hi} cm)"
            )
    return warnings


def save(profile: BodyProfile, path: Path) -> None:
    path = Path(path)
    path.write_text(json.dumps(asdict(profile), indent=2))


def load(path: Path) -> BodyProfile | None:
    path = Path(path)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return BodyProfile(**data)
