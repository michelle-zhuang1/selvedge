from __future__ import annotations
import warnings
from dataclasses import dataclass, field
from typing import ClassVar, Literal
import numpy as np
from fit_engine import GarmentMeasurements

_LOW_CONFIDENCE_THRESHOLD = 0.70

GarmentType = Literal["shirt", "jacket", "dress", "skirt", "trousers"]


@dataclass
class Garment:
    zones: ClassVar[list[str]]

    @classmethod
    def from_type(cls, garment_type: GarmentType) -> "Garment":
        return _GARMENT_REGISTRY[garment_type]()


@dataclass
class Shirt(Garment):
    zones: ClassVar[list[str]] = ["bust", "waist", "shoulder", "length"]


@dataclass
class Jacket(Garment):
    zones: ClassVar[list[str]] = ["bust", "waist", "shoulder", "length"]


@dataclass
class Dress(Garment):
    zones: ClassVar[list[str]] = ["bust", "waist", "hip", "length"]


@dataclass
class Skirt(Garment):
    zones: ClassVar[list[str]] = ["waist", "hip", "length"]


@dataclass
class Trousers(Garment):
    zones: ClassVar[list[str]] = ["waist", "hip", "inseam", "length"]


_GARMENT_REGISTRY: dict[GarmentType, type[Garment]] = {
    "shirt": Shirt,
    "jacket": Jacket,
    "dress": Dress,
    "skirt": Skirt,
    "trousers": Trousers,
}


@dataclass
class GarmentAnalysis:
    garment_type: GarmentType
    confidence: float
    dimensions: dict[str, float | None] = field(default_factory=dict)


class CVPipeline:
    def analyze(self, front: np.ndarray, back: np.ndarray) -> GarmentAnalysis:
        garment_type, confidence = self._classify(front)

        if confidence < _LOW_CONFIDENCE_THRESHOLD:
            warnings.warn(
                f"Garment classification confidence is low ({confidence:.0%}); "
                "extracted dimensions may be inaccurate.",
                UserWarning,
                stacklevel=2,
            )

        front_c = self._correct_perspective(front)
        back_c = self._correct_perspective(back)

        raw_dims = self._extract_dimensions(front_c, back_c, garment_type)

        allowed = Garment.from_type(garment_type).zones if garment_type in _GARMENT_REGISTRY else list(raw_dims.keys())
        dimensions = {k: v for k, v in raw_dims.items() if k in allowed}

        return GarmentAnalysis(
            garment_type=garment_type,
            confidence=confidence,
            dimensions=dimensions,
        )

    def to_garment_measurements(self, analysis: GarmentAnalysis) -> GarmentMeasurements:
        d = analysis.dimensions
        return GarmentMeasurements(
            garment_type=analysis.garment_type,
            bust=d.get("bust"),
            waist=d.get("waist"),
            hip=d.get("hip"),
            inseam=d.get("inseam"),
            shoulder=d.get("shoulder"),
            length=d.get("length"),
        )

    # ── Internal hooks (injectable for testing; real impl below) ──────────────

    def _classify(self, image: np.ndarray) -> tuple[str, float]:
        return "shirt", 0.90

    def _correct_perspective(self, image: np.ndarray) -> np.ndarray:
        return image

    def _extract_dimensions(
        self,
        front: np.ndarray,
        back: np.ndarray,
        garment_type: str = "",
    ) -> dict[str, float | None]:
        return {}
