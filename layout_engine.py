"""Greedy strip-packing cutting layout optimizer for Selvedge."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import svgwrite
from shapely import affinity
from shapely.geometry import Polygon

from pattern_engine import PatternPiece

_GAP_CM: float = 1.0  # gap between pieces in cm


@dataclass
class PlacedPiece:
    name: str
    polygon: Polygon  # translated to final position on the fabric


@dataclass
class LayoutResult:
    placements: list[PlacedPiece]
    utilization: float   # 0.0–1.0 fraction of fabric area covered by pieces
    fits_fabric: bool    # True when all pieces fit within width × length


def compute_layout(
    pieces: list[PatternPiece],
    fabric_width_cm: float,
    fabric_length_cm: float,
) -> LayoutResult:
    """Place pieces using greedy strip-packing (tallest-first, left-to-right rows)."""
    # Sort by bounding-box height descending (tallest first)
    sorted_pieces = sorted(
        pieces,
        key=lambda p: p.polygon.bounds[3] - p.polygon.bounds[1],
        reverse=True,
    )

    placements: list[PlacedPiece] = []
    x_cursor: float = 0.0
    y_cursor: float = 0.0
    row_height: float = 0.0

    for piece in sorted_pieces:
        bounds = piece.polygon.bounds  # (minx, miny, maxx, maxy)
        piece_w = bounds[2] - bounds[0]
        piece_h = bounds[3] - bounds[1]

        # Start a new row if this piece would exceed fabric width
        if x_cursor > 0 and x_cursor + piece_w > fabric_width_cm:
            y_cursor += row_height + _GAP_CM
            x_cursor = 0.0
            row_height = 0.0

        # Translate piece so its bounding-box top-left is at (x_cursor, y_cursor)
        tx = x_cursor - bounds[0]
        ty = y_cursor - bounds[1]
        placed_poly = affinity.translate(piece.polygon, xoff=tx, yoff=ty)

        placements.append(PlacedPiece(name=piece.name, polygon=placed_poly))

        x_cursor += piece_w + _GAP_CM
        row_height = max(row_height, piece_h)

    # Total height used = y_cursor + last row height
    total_height_used = y_cursor + row_height
    fits_fabric = total_height_used <= fabric_length_cm

    fabric_area = fabric_width_cm * fabric_length_cm
    piece_area = sum(p.polygon.area for p in placements)
    utilization = piece_area / fabric_area if fabric_area > 0 else 0.0

    return LayoutResult(
        placements=placements,
        utilization=utilization,
        fits_fabric=fits_fabric,
    )


def save_layout_svg(
    result: LayoutResult,
    fabric_width_cm: float,
    fabric_length_cm: float,
    path: Path,
) -> None:
    """Write cutting layout to SVG with fabric boundary and piece outlines."""
    path = Path(path)
    # Use 1 cm = 1 SVG user unit for simplicity
    dwg = svgwrite.Drawing(
        str(path),
        size=(f"{fabric_width_cm}cm", f"{fabric_length_cm}cm"),
        viewBox=f"0 0 {fabric_width_cm} {fabric_length_cm}",
        profile="tiny",
    )

    # Fabric boundary rectangle
    dwg.add(dwg.rect(
        insert=(0, 0),
        size=(fabric_width_cm, fabric_length_cm),
        fill="#f0f0f0",
        stroke="#999999",
        stroke_width=0.3,
    ))

    # Each piece: outline + name label at centroid
    for placed in result.placements:
        coords = list(placed.polygon.exterior.coords)
        dwg.add(dwg.polygon(
            coords,
            stroke="black",
            fill="none",
            stroke_width=0.3,
        ))
        cx = placed.polygon.centroid.x
        cy = placed.polygon.centroid.y
        dwg.add(dwg.text(
            placed.name,
            insert=(cx, cy),
            font_size=3,
            text_anchor="middle",
            fill="black",
        ))

    dwg.save()
