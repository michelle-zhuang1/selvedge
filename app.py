import streamlit as st
from pathlib import Path
from body_profile import BodyProfile, load, save, validate

PROFILE_PATH = Path("body_profile.json")

st.set_page_config(page_title="Selvedge", layout="centered")
st.title("Selvedge")

profile = load(PROFILE_PATH) or BodyProfile(
    bust=0.0, waist=0.0, hip=0.0,
    inseam=0.0, height=0.0, shoulder=0.0,
)

st.header("Body measurements")
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
    warnings = validate(updated)
    save(updated, PROFILE_PATH)
    st.success("Measurements saved.")
    for w in warnings:
        st.warning(w)
