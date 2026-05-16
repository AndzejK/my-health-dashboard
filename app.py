import streamlit as st
from config.settings import initialize_session_state, get_paths_from_session
from ui.garmin import render_sleep_chart
from ui.garmin_controls import render_garmin_controls
from ui.cronometer import render_cronometer_controls
from ui.settings import render_settings

st.set_page_config(page_title="Health Data Sync", page_icon=":bar_chart:", layout="wide")

initialize_session_state()
paths = get_paths_from_session()

st.title("Health Data Sync")

tab_garmin, tab_cronometer, tab_settings = st.tabs(["Garmin", "Cronometer", "Settings"])

with tab_garmin:
    render_sleep_chart(paths["garmin_output_dir"] / "sleep_summary.csv")
    render_garmin_controls(paths)

with tab_cronometer:
    render_cronometer_controls(paths)

with tab_settings:
    render_settings(paths)
