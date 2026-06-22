# Selvedge

A local-first personal tool for upcycling thrifted garments. Selvedge digitizes flat garment photos, estimates fabric yield, and generates fitted pattern pieces ready for a laser cutter or home printer.

Two modes:
- **Alter Mode** — given a thrifted garment's flat measurements, calculates what to take in or let out at each zone to fit your body
- **Remake Mode** — estimates how much usable fabric a garment yields, then generates parametric pattern pieces (skirt and trousers) in SVG and DXF

Woven stable fabrics only — no stretch or knit.

## Setup

```bash
uv pip install -r requirements.txt
uv run streamlit run app.py
```

Tests:

```bash
uv run pytest tests/ -v
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

## Data layout

```
selvedge/
├── body_profile.json              # 6 core + 6 extended measurements (cm)
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

## Tech stack

| Layer | Library |
|-------|---------|
| UI | Streamlit |
| CV | OpenCV, Pillow |
| ML | PyTorch |
| Geometry | Shapely |
| Pattern output | svgwrite, ezdxf (SVG + DXF for laser cutter) |
| LLM | Anthropic Python SDK |
| Storage | JSON + filesystem (local only) |

## ML strategy

Rule-based baselines are fully functional without any trained models. ML layers activate progressively as personal data accumulates:

- **Garment classification** — fine-tuned ResNet/EfficientNet on DeepFashion2 + iMaterialist; >85% accuracy target
- **Yield estimation** — V1: lookup table + geometric correction; V2: regression model after ~20 labeled garments
- **Cutting layout optimizer** — No-Fit Polygon nesting (Shapely/Minkowski) with learned piece-ordering heuristics
- **Fit feedback model** — personalizes ease values after ~10–15 feedback entries

## Milestones

Follows 12 milestones (M1–M12) defined in `Selvedge_PRD.pdf`:

- **M1** — Streamlit shell + body profile schema + onboarding
- **M2–M3** — CV pipeline (classification, dimension extraction)
- **M4** — Alter Mode end-to-end
- **M5–M8** — Remake Mode (yield → pattern → NFP layout)
- **M9** — LLM creative layer
- **M10–M12** — Fit feedback loop + personal ML models
