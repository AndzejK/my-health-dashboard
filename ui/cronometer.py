import streamlit as st
from datetime import date, timedelta
from services.cronometer import run_go_exporter

def render_cronometer_controls(paths: dict) -> None:
    st.subheader("Cronometer Exporter")
    today = date.today()
    col_start, col_end = st.columns(2)
    with col_start:
        start_date = st.date_input(
            "Start date",
            value=today - timedelta(days=1),
            key="cronometer_start_date",
        )
    with col_end:
        end_date = st.date_input(
            "End date",
            value=today - timedelta(days=1),
            key="cronometer_end_date",
        )

    st.caption("Select only the sections you want to fetch and push to Google Sheets.")
    col_a, col_b = st.columns(2)
    with col_a:
        fetch_servings = st.checkbox("Fetch servings", value=True, key="cronometer_fetch_servings")
        fetch_daily_nutrition = st.checkbox(
            "Fetch daily nutrition", value=True, key="cronometer_fetch_daily_nutrition"
        )
    with col_b:
        fetch_biometrics = st.checkbox("Fetch biometrics", value=False, key="cronometer_fetch_biometrics")
        fetch_notes = st.checkbox("Fetch notes", value=False, key="cronometer_fetch_notes")

    if not any([fetch_servings, fetch_daily_nutrition, fetch_biometrics, fetch_notes]):
        st.warning("Select at least one Cronometer section to fetch.")
        return

    if st.button("Run Cronometer Go exporter"):
        if end_date < start_date:
            st.error("End date must be on or after start date.")
            return
        result = run_go_exporter(
            project_dir=paths["cronometer_project"],
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            reports_dir=paths["cronometer_output_dir"],
            spreadsheet_id=st.session_state.spreadsheet_id,
            servings_sheet=st.session_state.servings_sheet,
            daily_nutrition_sheet=st.session_state.daily_nutrition_sheet,
            biometrics_sheet=st.session_state.biometrics_sheet,
            garmin_sheet=st.session_state.garmin_sheet,
            google_credentials=paths["google_credentials"],
            google_token=paths["google_token"],
            fetch_servings=fetch_servings,
            fetch_daily_nutrition=fetch_daily_nutrition,
            fetch_biometrics=fetch_biometrics,
            fetch_notes=fetch_notes,
        )
        if result.returncode == 0:
            st.success("Cronometer exporter finished")
        else:
            st.error(f"Cronometer exporter failed with exit code {result.returncode}")
        st.text_area("Output", value=(result.stdout + "\n" + result.stderr).strip(), height=320)
