from __future__ import annotations
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import svgwrite
import ezdxf
from shapely.geometry import Polygon
from shapely import affinity

from body_profile import BodyProfile
from yield_engine import YieldEstimate

_SEAM_DEFAULT = 1.5   # cm
_HEM_ALLOWANCE = 3.0  # cm
_EASE_WAIST = 2.0     # cm
_EASE_HIP = 4.0       # cm
_WASTE_FACTOR = 1.15


class SkirtLength(float, Enum):
    SHORT = 40.0   # mini
    MIDI  = 65.0
    MAXI  = 90.0


@dataclass
class PatternPiece:
    name: str
    polygon: Polygon
    grain_line: str = "vertical"   # "vertical" | "horizontal"


@dataclass
class PatternOutput:
    pieces: list[PatternPiece]
    fits_yield: bool
    assembly_notes: str


# ── Geometry helpers ───────────────────────────────────────────────────────────

def _expand(polygon: Polygon, amount: float) -> Polygon:
    """Add seam allowance by buffering all edges outward."""
    return polygon.buffer(amount, join_style=2)   # join_style=2 = mitre


def _skirt_panel(waist_w: float, hip_w: float, length: float) -> Polygon:
    """Symmetric trapezoid: waist at top, hip at bottom."""
    flare = (hip_w - waist_w) / 2
    return Polygon([
        (flare, 0),
        (flare + waist_w, 0),
        (hip_w, length),
        (0, length),
    ])


def _rect(width: float, height: float) -> Polygon:
    return Polygon([(0, 0), (width, 0), (width, height), (0, height)])


# ── Pattern generators ─────────────────────────────────────────────────────────

def generate_skirt(
    body: BodyProfile,
    yield_est: YieldEstimate,
    length: SkirtLength = SkirtLength.MIDI,
    seam_allowance: float = _SEAM_DEFAULT,
) -> PatternOutput:
    waist_half = (body.waist + _EASE_WAIST) / 2
    hip_half   = (body.hip   + _EASE_HIP)   / 2

    panel = _expand(_skirt_panel(waist_half, hip_half, float(length) + _HEM_ALLOWANCE), seam_allowance)

    wb_width  = body.waist + _EASE_WAIST + 3.0 + 2 * seam_allowance  # +3cm overlap
    wb_height = 6.0 + 2 * seam_allowance                              # 3cm finished × 2
    waistband = _rect(wb_width, wb_height)

    pieces = [
        PatternPiece("front panel",  panel,     "vertical"),
        PatternPiece("back panel",   panel,     "vertical"),
        PatternPiece("waistband",    waistband, "horizontal"),
    ]

    total_area = sum(p.polygon.area for p in pieces) * _WASTE_FACTOR
    fits = total_area <= yield_est.area_cm2

    notes = _skirt_notes(length, seam_allowance, fits)
    return PatternOutput(pieces=pieces, fits_yield=fits, assembly_notes=notes)


def _skirt_notes(length: SkirtLength, sa: float, fits: bool) -> str:
    name = {SkirtLength.SHORT: "mini", SkirtLength.MIDI: "midi", SkirtLength.MAXI: "maxi"}[length]
    lines = [
        f"SKIRT — {name} ({float(length):.0f} cm finished length)",
        f"Seam allowance: {sa} cm throughout unless marked.",
        f"Hem allowance: {_HEM_ALLOWANCE} cm (fold twice for a clean hem).",
        "",
        "Assembly order:",
        "1. Stitch front and back panels together at side seams (right sides together).",
        "2. Press seams open.",
        "3. Attach waistband: fold in half lengthwise, stitch to waist edge.",
        "4. Insert zip at left side seam before closing waistband.",
        "5. Hem: press up hem allowance, topstitch or slip stitch.",
    ]
    if not fits:
        lines.insert(0, "⚠ WARNING: estimated fabric yield may be insufficient for this length.")
    return "\n".join(lines)


# ── Output writers ─────────────────────────────────────────────────────────────

def save_svg(output: PatternOutput, path: Path) -> None:
    path = Path(path)
    # Lay pieces out side by side with 10cm gap
    dwg = svgwrite.Drawing(str(path), profile="tiny")
    x_offset = 0.0
    for piece in output.pieces:
        coords = list(piece.polygon.exterior.coords)
        pts = [(x + x_offset, y) for x, y in coords]
        dwg.add(dwg.polygon(pts, stroke="black", fill="none", stroke_width=0.5))
        # Grain line label
        cx = x_offset + piece.polygon.centroid.x
        cy = piece.polygon.centroid.y
        dwg.add(dwg.text(piece.name, insert=(cx, cy), font_size=4,
                         text_anchor="middle", fill="black"))
        bbox = piece.polygon.bounds  # (minx, miny, maxx, maxy)
        x_offset += bbox[2] - bbox[0] + 10
    dwg.save()


def save_dxf(output: PatternOutput, path: Path) -> None:
    path = Path(path)
    doc = ezdxf.new()
    msp = doc.modelspace()
    x_offset = 0.0
    for piece in output.pieces:
        coords = list(piece.polygon.exterior.coords)
        pts = [(x + x_offset, y) for x, y in coords]
        msp.add_lwpolyline(pts, close=True)
        bbox = piece.polygon.bounds
        x_offset += bbox[2] - bbox[0] + 10
    doc.saveas(str(path))


def save_assembly_notes(output: PatternOutput, path: Path) -> None:
    Path(path).write_text(output.assembly_notes)
