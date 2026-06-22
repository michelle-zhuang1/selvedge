# CLAUDE.md

## Project Overview

**Selvedge** is a local-first personal tool for upcycling thrifted garments. Two modes: **Alter Mode** (fit adjustments) and **Remake Mode** (fabric yield → new pattern pieces). Woven stable fabrics only — no stretch/knit.

## Commands

```bash
uv pip install -r requirements.txt
uv run streamlit run app.py
uv run pytest tests/ -v          # or: npm test
```

## Architecture

Seven-layer pipeline:

1. **Photo Input** — Streamlit UI, front + back flat-lay photos
2. **CV Pipeline** — classification → silhouette extraction → dimension measurement → seam detection (Remake only)
3. **Fit Engine** — rule-based ease (Aldrich/Armstrong standards) + body profile delta
4. **ML Layer** — yield estimation, layout optimization, fit feedback (progressive; rule-based baselines first)
5. **Pattern Engine** — Shapely geometry → parametric pattern pieces → SVG/DXF
6. **LLM Layer** — Claude API for constrained-yield creative suggestions (only external network call)
7. **Interface** — Streamlit, local only

## Data Layout

```
selvedge/
├── body_profile.json              # 6 core + 6 extended measurements
└── garments/
    └── YYYY-MM-DD-{name}/
        ├── front.jpg
        ├── back.jpg
        ├── cv_output.json         # classification, dimensions, yield
        ├── fit_feedback.json      # zone feedback, 1–5 rating, notes
        └── remake_output/
            ├── pattern_pieces.svg
            ├── cutting_layout.svg
            └── assembly_notes.txt
```

## Coding Conventions

### Type annotations
All module-level constants, function signatures, and dataclass fields must have explicit type annotations. Prefer named types over anonymous structures:
- Use `NamedTuple` subclasses instead of bare `tuple[str, float, ...]` for structured data (e.g. `_YieldFactor(NamedTuple)` in `yield_engine.py`)
- Use `tuple[str, ...]` or `frozenset[str]` for immutable collections instead of `list` — mutable module-level lists are a common source of accidental mutation bugs

### Waste factor convention
`_WASTE_FACTOR` represents the **waste fraction** (e.g. `0.15` = 15%), not the multiplier. Always apply it as `value * (1 + _WASTE_FACTOR)`. Using `1.15` directly as a constant is wrong — it prevents negative values from being meaningful and obscures the intent. This convention must be consistent across `yield_engine.py` and `pattern_engine.py`.

