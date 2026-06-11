import streamlit as st
from datetime import date
from pathlib import Path
from body_profile import BodyProfile, load, save, validate
from fit_engine import GarmentMeasurements, compute_alterations
from feedback import BODY_ZONES, ZoneRating, FitFeedback, save_feedback, load_feedback_history

GARMENTS_DIR = Path("garments")

PROFILE_PATH = Path("body_profile.json")

st.set_page_config(page_title="Selvedge", layout="centered")
st.title("Selvedge")

profile = load(PROFILE_PATH) or BodyProfile(
    bust=0.0, waist=0.0, hip=0.0,
    inseam=0.0, height=0.0, shoulder=0.0,
)

tab_profile, tab_alter, tab_feedback = st.tabs(["Body measurements", "Alter Mode", "Fit feedback"])

# ── Body measurements ──────────────────────────────────────────────────────────
with tab_profile:
    st.caption("All measurements in cm.")

    with st.form("measurements"):
        st.subheader("Core")
        col1, col2, col3 = st.columns(3)
        bust     = col1.number_input("Bust",     value=profile.bust,     min_value=0.0, step=0.5)
        waist    = col2.number_input("Waist",    value=profile.waist,    min_value=0.0, step=0.5)
        hip      = col3.number_input("Hip",      value=profile.hip,      min_value=0.0, step=0.5)
        inseam   = col1.number_input("Inseam",   value=profile.inseam,   min_value=0.0, step=0.5)
        height   = col2.number_input("Height",   value=profile.height,   min_value=0.0, step=0.5)
        shoulder = col3.number_input("Shoulder", value=profile.shoulder, min_value=0.0, step=0.5)

        st.subheader("Extended (optional)")
        col4, col5, col6 = st.columns(3)
        arm   = col4.number_input("Arm",   value=profile.arm   or 0.0, min_value=0.0, step=0.5)
        wrist = col5.number_input("Wrist", value=profile.wrist or 0.0, min_value=0.0, step=0.5)
        thigh = col6.number_input("Thigh", value=profile.thigh or 0.0, min_value=0.0, step=0.5)
        rise  = col4.number_input("Rise",  value=profile.rise  or 0.0, min_value=0.0, step=0.5)
        back  = col5.number_input("Back",  value=profile.back  or 0.0, min_value=0.0, step=0.5)
        neck  = col6.number_input("Neck",  value=profile.neck  or 0.0, min_value=0.0, step=0.5)

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
    profile_warnings = validate(profile)
    if profile_warnings:
        st.warning("Some body measurements may be incomplete or out of range — alteration accuracy may be affected.")

    garment_type = st.selectbox("Garment type", ["shirt", "dress", "skirt", "trousers", "jacket"])
    st.caption("Enter the garment's flat measurements in cm. Leave zones at 0 to skip them.")

    col1, col2, col3 = st.columns(3)
    g_bust     = col1.number_input("Bust",     min_value=0.0, step=0.5, key="g_bust")
    g_waist    = col2.number_input("Waist",    min_value=0.0, step=0.5, key="g_waist")
    g_hip      = col3.number_input("Hip",      min_value=0.0, step=0.5, key="g_hip")
    g_inseam   = col1.number_input("Inseam",   min_value=0.0, step=0.5, key="g_inseam")
    g_shoulder = col2.number_input("Shoulder", min_value=0.0, step=0.5, key="g_shoulder")

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

# ── Fit feedback ───────────────────────────────────────────────────────────────
with tab_feedback:
    st.caption("Record how a garment actually felt after wearing it.")

    garment_name = st.text_input("Garment name", placeholder="e.g. linen-shirt")
    feedback_date = st.date_input("Date worn", value=date.today())

    st.subheader("Zone ratings")
    st.caption("Rate fit per zone: 1 = too tight, 3 = good, 5 = too loose.")
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
