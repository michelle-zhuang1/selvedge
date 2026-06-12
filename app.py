import tempfile
import streamlit as st
import streamlit.components.v1 as components
from datetime import date
from pathlib import Path
from body_profile import BodyProfile, load, save, validate
from fit_engine import GarmentMeasurements, compute_alterations
from feedback import BODY_ZONES, ZoneRating, FitFeedback, save_feedback, load_feedback_history
from yield_engine import estimate_yield, rank_feasibility, save_cv_output
from cv_pipeline import GarmentAnalysis
from pattern_engine import SkirtLength, generate_skirt, generate_trousers, save_svg, save_dxf, save_assembly_notes

GARMENTS_DIR = Path("garments")

def _tab0_warning(message: str) -> None:
    """Warning box with an inline 'Body Measurements' link that switches to tab 0."""
    components.html(f"""
    <style>body {{ margin: 0; padding: 0; }}</style>
    <div style="background:#fff3cd;border:1px solid #ffc107;border-radius:0.5rem;
                padding:0.75rem 1rem;font-family:sans-serif;font-size:0.875rem;color:#856404;">
        ⚠️ {message} Go to
        <a id="link" href="#"
           style="color:#856404;font-weight:700;text-decoration:underline;">
            Body Measurements
        </a> to complete your profile.
    </div>
    <script>
        document.getElementById('link').addEventListener('click', function(e) {{
            e.preventDefault();
            window.parent.document.querySelectorAll('button[role="tab"]')[0].click();
        }});
    </script>
    """, height=70)

PROFILE_PATH = Path("body_profile.json")

st.set_page_config(page_title="Selvedge", layout="centered")

st.markdown("""
<style>
/* Anchor the input row so we can absolutely position the hint */
div[data-testid="stNumberInput"] > div {
    position: relative;
}
/* Center the hint across the full box width */
div[data-testid="InputInstructions"] {
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    white-space: nowrap;
    pointer-events: none;
}
div[data-testid="stNumberInput"] {
    margin-bottom: 0.75rem;
}
</style>
""", unsafe_allow_html=True)

st.title("Selvedge")

profile = load(PROFILE_PATH) or BodyProfile(
    bust=0.0, waist=0.0, hip=0.0,
    inseam=0.0, height=0.0, shoulder=0.0,
)

tab_profile, tab_alter, tab_remake, tab_feedback = st.tabs(["Body Measurements", "Alter Mode", "Remake Mode", "Fit Feedback"])

# ── Body measurements ──────────────────────────────────────────────────────────
with tab_profile:
    st.caption("All measurements in cm. Hover the ℹ️ icon on each field for guidance.")

    with st.expander("📐 Measurement reference"):
        st.image("assets/measurement_reference.png", use_container_width=True)

    with st.form("measurements"):
        st.subheader("Core")
        col1, col2 = st.columns(2)
        bust     = col1.number_input("Bust",     value=profile.bust,     min_value=0.0, step=0.5,
                       help="(A) Measure around the fullest point of your chest, keeping the tape parallel to the floor.")
        waist    = col2.number_input("Waist",    value=profile.waist,    min_value=0.0, step=0.5,
                       help="(B) Measure around your waist at the narrowest point.")
        hip      = col1.number_input("Hip",      value=profile.hip,      min_value=0.0, step=0.5,
                       help="(C) Stand with heels together and measure around the fullest point of your hips.")
        inseam   = col2.number_input("Inseam",   value=profile.inseam,   min_value=0.0, step=0.5,
                       help="Measure along the inner leg from the crotch seam to the ankle bone.")
        height   = col1.number_input("Height",   value=profile.height,   min_value=0.0, step=0.5,
                       help="(J) Measure from the top of your head to the floor standing straight.")
        shoulder = col2.number_input("Shoulder", value=profile.shoulder, min_value=0.0, step=0.5,
                       help="(E) Measure across your back from the base of one neck to the shoulder bone, on one side.")

        st.subheader("Extended (optional)")
        col3, col4 = st.columns(2)
        arm   = col3.number_input("Arm",   value=profile.arm   or 0.0, min_value=0.0, step=0.5,
                    help="Measure from the shoulder bone to the wrist bone along the outside of a slightly bent arm.")
        wrist = col4.number_input("Wrist", value=profile.wrist or 0.0, min_value=0.0, step=0.5,
                    help="Measure around the wrist bone at its narrowest point.")
        thigh = col3.number_input("Thigh", value=profile.thigh or 0.0, min_value=0.0, step=0.5,
                    help="Measure around the fullest part of the upper thigh.")
        rise  = col4.number_input("Rise",  value=profile.rise  or 0.0, min_value=0.0, step=0.5,
                    help="Measure from the top of the waistband to the crotch seam at the front.")
        back  = col3.number_input("Back",  value=profile.back  or 0.0, min_value=0.0, step=0.5,
                    help="Measure from the nape of the neck (base of the cervical vertebra) straight down to the waist.")
        neck  = col4.number_input("Neck",  value=profile.neck  or 0.0, min_value=0.0, step=0.5,
                    help="(D) Measure around the base of the neck.")

        submitted = st.form_submit_button("Save measurements")

    if submitted:
        updated = BodyProfile(
            bust=bust, waist=waist, hip=hip,
            inseam=inseam, height=height, shoulder=shoulder,
            arm=arm or None, wrist=wrist or None, thigh=thigh or None,
            rise=rise or None, back=back or None, neck=neck or None,
        )
        profile_warnings = validate(updated)
        save(updated, PROFILE_PATH)
        profile = updated
        st.success("Measurements saved.")
        for w in profile_warnings:
            st.warning(w)

# ── Alter Mode ─────────────────────────────────────────────────────────────────
with tab_alter:
    st.info(
        "**Alter Mode** tells you what adjustments to make so a thrifted garment fits your body. "
        "Measure the garment flat (not on a body), enter its dimensions below, and Selvedge will "
        "calculate how much to take in or let out at each zone based on your saved measurements and standard wearing ease."
    )

    profile_warnings = validate(profile)
    if profile_warnings:
        _tab0_warning("Some body measurements may be incomplete or out of range — alteration accuracy may be affected.")

    garment_type = st.selectbox("Garment type", ["shirt", "dress", "skirt", "trousers", "jacket"])
    st.caption("Enter the garment's flat measurements in cm. Leave any zone at 0 to skip it.")

    col1, col2, col3 = st.columns(3)
    g_bust     = col1.number_input("Bust",     min_value=0.0, step=0.5, key="g_bust",
                     help="Measure across the fullest part of the garment front, double it for circumference.")
    g_waist    = col2.number_input("Waist",    min_value=0.0, step=0.5, key="g_waist",
                     help="Measure across the narrowest part of the garment front, double it for circumference.")
    g_hip      = col3.number_input("Hip",      min_value=0.0, step=0.5, key="g_hip",
                     help="Measure across the fullest part of the garment at hip level, double it for circumference.")
    g_inseam   = col1.number_input("Inseam",   min_value=0.0, step=0.5, key="g_inseam",
                     help="For trousers: measure along the inner leg seam from crotch to hem.")
    g_shoulder = col2.number_input("Shoulder", min_value=0.0, step=0.5, key="g_shoulder",
                     help="Measure straight across the back from shoulder seam to shoulder seam.")

    if st.button("Analyse fit"):
        garment = GarmentMeasurements(
            garment_type=garment_type,
            bust=g_bust or None,
            waist=g_waist or None,
            hip=g_hip or None,
            inseam=g_inseam or None,
            shoulder=g_shoulder or None,
        )
        instructions = compute_alterations(profile, garment)
        if not instructions:
            st.success("Garment fits within wearing ease — no alterations needed.")
        else:
            st.subheader("Alteration instructions")
            for instr in instructions:
                direction = "⬆ take in" if instr.delta_cm > 0 else "⬇ let out"
                st.markdown(f"**{instr.zone.capitalize()}** — {direction} **{abs(instr.delta_cm):.1f} cm**")

# ── Remake Mode ────────────────────────────────────────────────────────────────
with tab_remake:
    st.info(
        "**Remake Mode** helps you decide whether a thrifted garment has enough fabric to be cut apart "
        "and remade into something new — before you commit to seam-ripping. "
        "Measure the source garment flat, enter its dimensions, and Selvedge will estimate the usable fabric "
        "area and rank which new garment types (skirt, trousers) are feasible for your body."
    )

    profile_warnings = validate(profile)
    if profile_warnings:
        _tab0_warning("Some body measurements may be incomplete — feasibility estimates may be inaccurate.")

    st.caption("Enter the source garment's flat measurements in cm to estimate fabric yield.")

    r_garment_type = st.selectbox("Source garment type", ["shirt", "dress", "jacket", "skirt", "trousers"], key="r_type",
                        help="What type of garment are you starting with? This determines how fabric area is calculated.")
    r_confidence = st.slider("Classification confidence", 0.0, 1.0, 0.9, 0.01, key="r_conf",
                        help="How confident are you in the garment type? Lower this if you're unsure — it will be used in future CV automation.")

    col1, col2, col3 = st.columns(3)
    r_bust     = col1.number_input("Bust",     min_value=0.0, step=0.5, key="r_bust",
                     help="Measure across the fullest part of the garment front and double it.")
    r_waist    = col2.number_input("Waist",    min_value=0.0, step=0.5, key="r_waist",
                     help="Measure across the narrowest part of the garment front and double it.")
    r_hip      = col3.number_input("Hip",      min_value=0.0, step=0.5, key="r_hip",
                     help="Measure across the fullest part at hip level and double it.")
    r_inseam   = col1.number_input("Inseam",   min_value=0.0, step=0.5, key="r_inseam",
                     help="For trousers: measure the inner leg seam from crotch to hem.")
    r_shoulder = col2.number_input("Shoulder", min_value=0.0, step=0.5, key="r_shoulder",
                     help="Measure straight across the back from shoulder seam to shoulder seam.")
    r_length   = col3.number_input("Length",   min_value=0.0, step=0.5, key="r_length",
                     help="Measure from the highest point (shoulder or waistband) straight down to the hem.")

    r_garment_name = st.text_input("Garment name (for saving)", placeholder="e.g. plaid-shirt")

    if st.button("Estimate yield"):
        dims = {
            k: v or None for k, v in {
                "bust": r_bust, "waist": r_waist, "hip": r_hip,
                "inseam": r_inseam, "shoulder": r_shoulder, "length": r_length,
            }.items()
        }
        analysis = GarmentAnalysis(
            garment_type=r_garment_type,
            confidence=r_confidence,
            dimensions=dims,
        )
        yield_est = estimate_yield(analysis)
        results = rank_feasibility(yield_est, profile)

        st.subheader(f"Estimated yield: ~{yield_est.area_cm2:.0f} cm²")
        st.caption(f"Approx {yield_est.width_cm:.0f} cm wide × {yield_est.length_cm:.0f} cm long")

        st.subheader("Feasibility ranking")
        for r in results:
            if r.feasible:
                st.success(f"**{r.garment_type.capitalize()}** — feasible ({r.yield_pct:.0%} of required fabric)")
            else:
                st.error(f"**{r.garment_type.capitalize()}** — {r.reason}")

        skirt_feasible = any(r.garment_type == "skirt" and r.feasible for r in results)
        if skirt_feasible:
            st.divider()
            st.subheader("Generate skirt pattern")
            skirt_length = st.selectbox(
                "Finished skirt length",
                [SkirtLength.SHORT, SkirtLength.MIDI, SkirtLength.MAXI],
                format_func=lambda l: {
                    SkirtLength.SHORT: f"Mini ({int(float(l))} cm)",
                    SkirtLength.MIDI:  f"Midi ({int(float(l))} cm)",
                    SkirtLength.MAXI:  f"Maxi ({int(float(l))} cm)",
                }[l],
                index=1,
                key="skirt_length",
            )
            if st.button("Generate pattern", key="gen_pattern"):
                pattern = generate_skirt(profile, yield_est, skirt_length)
                if not pattern.fits_yield:
                    st.warning("Fabric yield may be insufficient for this length — review the assembly notes.")

                with tempfile.TemporaryDirectory() as tmp:
                    tmp = Path(tmp)
                    svg_path   = tmp / "skirt.svg"
                    dxf_path   = tmp / "skirt.dxf"
                    notes_path = tmp / "assembly_notes.txt"
                    save_svg(pattern, svg_path)
                    save_dxf(pattern, dxf_path)
                    save_assembly_notes(pattern, notes_path)

                    col_a, col_b, col_c = st.columns(3)
                    col_a.download_button("Download SVG", svg_path.read_bytes(),
                                          file_name="skirt_pattern.svg", mime="image/svg+xml")
                    col_b.download_button("Download DXF", dxf_path.read_bytes(),
                                          file_name="skirt_pattern.dxf", mime="application/octet-stream")
                    col_c.download_button("Download notes", notes_path.read_text(),
                                          file_name="assembly_notes.txt", mime="text/plain")

                    st.code(pattern.assembly_notes)

        trousers_feasible = any(r.garment_type == "trousers" and r.feasible for r in results)
        if trousers_feasible:
            st.divider()
            st.subheader("Generate trouser pattern")
            if st.button("Generate pattern", key="gen_trousers"):
                pattern = generate_trousers(profile, yield_est)
                if not pattern.fits_yield:
                    st.warning("Fabric yield may be insufficient for these trousers — review the assembly notes.")

                with tempfile.TemporaryDirectory() as tmp:
                    tmp = Path(tmp)
                    svg_path   = tmp / "trousers.svg"
                    dxf_path   = tmp / "trousers.dxf"
                    notes_path = tmp / "assembly_notes.txt"
                    save_svg(pattern, svg_path)
                    save_dxf(pattern, dxf_path)
                    save_assembly_notes(pattern, notes_path)

                    col_a, col_b, col_c = st.columns(3)
                    col_a.download_button("Download SVG", svg_path.read_bytes(),
                                          file_name="trouser_pattern.svg", mime="image/svg+xml")
                    col_b.download_button("Download DXF", dxf_path.read_bytes(),
                                          file_name="trouser_pattern.dxf", mime="application/octet-stream")
                    col_c.download_button("Download notes", notes_path.read_text(),
                                          file_name="assembly_notes.txt", mime="text/plain")

                    st.code(pattern.assembly_notes)

        if r_garment_name.strip():
            session = f"{date.today().isoformat()}-{r_garment_name.strip().lower().replace(' ', '-')}"
            garment_dir = GARMENTS_DIR / session
            garment_dir.mkdir(parents=True, exist_ok=True)
            save_cv_output(analysis, yield_est, garment_dir / "cv_output.json")
            st.info(f"Saved to garments/{session}/cv_output.json")

# ── Fit feedback ───────────────────────────────────────────────────────────────
with tab_feedback:
    st.info(
        "**Fit Feedback** lets you record how a garment actually felt after wearing it. "
        "Rate the fit zone by zone and add notes on what worked or didn't. "
        "Over time this data will be used to personalise the ease values in Alter Mode — "
        "so the more you log, the more accurate your alteration instructions become."
    )

    garment_name = st.text_input("Garment name", placeholder="e.g. linen-shirt",
                      help="Use the same name as the garment session you created in Remake or Alter Mode, e.g. 2026-06-11-linen-shirt.")
    feedback_date = st.date_input("Date worn", value=date.today())

    st.subheader("Zone ratings")
    st.caption("Rate fit per zone — 1 = too tight, 3 = fits well, 5 = too loose.")
    zone_ratings: list[ZoneRating] = []
    cols = st.columns(3)
    for i, zone in enumerate(BODY_ZONES):
        rating = cols[i % 3].slider(zone.capitalize(), min_value=1, max_value=5, value=3, key=f"fb_{zone}")
        zone_ratings.append(ZoneRating(zone=zone, rating=rating))

    notes = st.text_area("Notes", placeholder="Any observations about the fit…")

    if st.button("Save feedback", disabled=not garment_name.strip()):
        session = f"{feedback_date.isoformat()}-{garment_name.strip().lower().replace(' ', '-')}"
        garment_dir = GARMENTS_DIR / session
        feedback = FitFeedback(
            date=feedback_date.isoformat(),
            zone_ratings=zone_ratings,
            notes=notes,
        )
        save_feedback(garment_dir, feedback)
        st.success(f"Feedback saved to garments/{session}/fit_feedback.json")

    st.divider()
    st.subheader("Feedback history")
    history_name = st.text_input("Look up garment session", placeholder="YYYY-MM-DD-name", key="hist_name")
    if history_name.strip():
        history = load_feedback_history(GARMENTS_DIR / history_name.strip())
        if not history:
            st.info("No feedback recorded for this session yet.")
        else:
            for entry in history:
                with st.expander(f"{entry.date}"):
                    for zr in entry.zone_ratings:
                        st.write(f"**{zr.zone.capitalize()}**: {zr.rating}/5")
                    if entry.notes:
                        st.write(f"Notes: {entry.notes}")
