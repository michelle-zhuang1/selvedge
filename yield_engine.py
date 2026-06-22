from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import NamedTuple
from cv_pipeline import GarmentAnalysis
from body_profile import BodyProfile


class _YieldFactor(NamedTuple):
    width_key: str
    width_factor: float
    length_key: str
    panels: float


_YIELD_FACTORS: dict[str, _YieldFactor] = {
    "shirt":    _YieldFactor("bust",  0.55, "length", 2.0),
    "jacket":   _YieldFactor("bust",  0.60, "length", 2.5),
    "dress":    _YieldFactor("hip",   0.55, "length", 2.0),
    "skirt":    _YieldFactor("hip",   0.55, "length", 2.0),
    "trousers": _YieldFactor("hip",   0.55, "length", 2.2),
}

_WASTE_FACTOR = 0.15  # 15% waste fraction for seam allowances and cutting waste

_CANDIDATES: tuple[str, ...] = ("skirt", "trousers")


@dataclass
class YieldEstimate:
    area_cm2: float
    width_cm: float
    length_cm: float


@dataclass
class FeasibilityResult:
    garment_type: str
    feasible: bool
    yield_pct: float   # ratio of available to required (≥1.0 = feasible)
    reason: str | None = None


def estimate_yield(analysis: GarmentAnalysis) -> YieldEstimate:
    factors = _YIELD_FACTORS.get(analysis.garment_type, ("bust", 0.55, "length", 2.0))
    width_key, width_factor, length_key, panels = factors
    width_cm = (analysis.dimensions.get(width_key) or 0.0) * width_factor
    length_cm = analysis.dimensions.get(length_key) or 0.0
    area_cm2 = width_cm * length_cm * panels
    return YieldEstimate(area_cm2=area_cm2, width_cm=width_cm, length_cm=length_cm)


def _required_area(garment_type: str, body: BodyProfile) -> tuple[float, str]:
    """Return (required_area_cm2, reason_if_missing)."""
    if garment_type == "skirt":
        min_length = 60.0  # midi minimum
        required = (body.hip + 10) * min_length * (1 + _WASTE_FACTOR)
        return required, f"need ~{required:.0f} cm² for a skirt (hip {body.hip}cm + ease, midi length)"
    if garment_type == "trousers":
        rise = 30.0
        inseam = body.inseam or 75.0
        required = (body.hip + 10) * (inseam + rise) * (1 + _WASTE_FACTOR)
        return required, f"need ~{required:.0f} cm² for trousers (hip {body.hip}cm + ease, inseam {inseam}cm)"
    return 0.0, ""


def rank_feasibility(yield_est: YieldEstimate, body: BodyProfile) -> list[FeasibilityResult]:
    results: list[FeasibilityResult] = []
    for candidate in _CANDIDATES:
        required, reason_template = _required_area(candidate, body)
        if required == 0:
            continue
        pct = yield_est.area_cm2 / required
        if pct >= 1.0:
            results.append(FeasibilityResult(garment_type=candidate, feasible=True, yield_pct=pct))
        else:
            results.append(FeasibilityResult(
                garment_type=candidate,
                feasible=False,
                yield_pct=pct,
                reason=f"insufficient fabric: {reason_template}, have ~{yield_est.area_cm2:.0f} cm²",
            ))
    results.sort(key=lambda r: (not r.feasible, -r.yield_pct))
    return results


def save_cv_output(analysis: GarmentAnalysis, yield_est: YieldEstimate, path: Path) -> None:
    data = {
        "garment_type": analysis.garment_type,
        "confidence": analysis.confidence,
        "dimensions": analysis.dimensions,
        "yield": asdict(yield_est),
    }
    Path(path).write_text(json.dumps(data, indent=2))
