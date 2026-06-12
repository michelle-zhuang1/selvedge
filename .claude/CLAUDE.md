# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Selvedge** is a local-first personal tool for upcycling thrifted garments. It digitizes flat garment photos, estimates fabric yield, and generates fitted/laser-cuttable pattern pieces. Two modes: **Alter Mode** (fit adjustments for any garment) and **Remake Mode** (fabric yield → new pattern generation, Skirts & Trousers only). Woven stable fabrics only — no stretch/knit.

The primary spec is `Selvedge_PRD.pdf`. The project is pre-implementation; development follows 12 milestones defined there (M1–M12).

## Planned Tech Stack

| Layer | Library |
|-------|---------|
| UI | Streamlit |
| CV | OpenCV, Pillow |
| ML | PyTorch |
| Geometry | Shapely |
| Pattern output | svgwrite, ezdxf (SVG display + DXF for laser cutter) |
| LLM | Anthropic Python SDK (Claude API) |
| Storage | JSON + filesystem (local only) |

## Running the App

```bash
pip install -r requirements.txt   # once requirements.txt exists
streamlit run app.py
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

## ML Strategy

Rule-based baselines are fully functional without any trained models. ML layers activate progressively once enough personal data accumulates:

- **Garment classification** — fine-tuned ResNet/EfficientNet on DeepFashion2 + iMaterialist; >85% accuracy target
- **Yield estimation** — V1: lookup table + geometric correction; V2: regression model after ~20 labeled garments
- **Cutting layout optimizer** — No-Fit Polygon nesting (Shapely/Minkowski) with learned piece-ordering heuristics
- **Fit feedback model** — personalizes ease values after ~10–15 feedback entries

## Development Order

Follow milestones M1 → M12 from the PRD. Suggested order for initial implementation:
- **M1** — Streamlit shell + body_profile.json schema + onboarding
- **M2–M3** — CV pipeline (classification, dimension extraction)
- **M4** — Alter Mode end-to-end (simplest validation loop)
- **M5–M8** — Remake Mode (yield → pattern → NFP layout)
- **M9** — LLM creative layer (Claude API integration)
- **M10–M12** — Fit feedback loop + personal ML models
