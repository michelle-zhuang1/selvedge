from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path

BODY_ZONES = ["bust", "waist", "hip", "length", "shoulder", "sleeve"]


@dataclass
class ZoneRating:
    zone: str
    rating: int

    def __post_init__(self):
        if self.zone not in BODY_ZONES:
            raise ValueError(f"zone must be one of {BODY_ZONES}, got {self.zone!r}")
        if not (1 <= self.rating <= 5):
            raise ValueError(f"rating must be 1–5, got {self.rating}")


@dataclass
class FitFeedback:
    date: str
    zone_ratings: list[ZoneRating]
    notes: str = ""


def save_feedback(garment_dir: Path, feedback: FitFeedback) -> Path:
    garment_dir = Path(garment_dir)
    garment_dir.mkdir(parents=True, exist_ok=True)
    feedback_file = garment_dir / "fit_feedback.json"

    history = []
    if feedback_file.exists():
        history = json.loads(feedback_file.read_text())

    entry = {
        "date": feedback.date,
        "zone_ratings": [asdict(zr) for zr in feedback.zone_ratings],
        "notes": feedback.notes,
    }
    history.append(entry)
    feedback_file.write_text(json.dumps(history, indent=2))
    return feedback_file


def load_feedback_history(garment_dir: Path) -> list[FitFeedback]:
    feedback_file = Path(garment_dir) / "fit_feedback.json"
    if not feedback_file.exists():
        return []
    raw = json.loads(feedback_file.read_text())
    return [
        FitFeedback(
            date=entry["date"],
            zone_ratings=[ZoneRating(**zr) for zr in entry["zone_ratings"]],
            notes=entry.get("notes", ""),
        )
        for entry in raw
    ]
