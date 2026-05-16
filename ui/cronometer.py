import streamlit as st
from datetime import date, timedelta
from services.cronometer import run_go_exporter

def render_cronometer_controls(paths: dict) -> None:
    st.subheader("Cronometer Exporter")
    target_date = st.date_input("Cronometer date", value=date.today() - timedelta(days=1))
    
    if st.button("Run Cronometer Go exporter"):
        result = run_go_exporter(
            project_dir=paths["cronometer_project"],
            target_date=target_date.isoformat(),
            reports_dir=paths["reports_dir"],
            spreadsheet_id=st.session_state.spreadsheet_id,
            servings_sheet=st.session_state.servings_sheet,
            biometrics_sheet=st.session_state.biometrics_sheet,
            garmin_sheet=st.session_state.garmin_sheet,
            google_credentials=paths["google_credentials"],
            google_token=paths["google_token"],
        )
        if result.returncode == 0:
            st.success("Cronometer exporter finished")
        else:
            st.error(f"Cronometer exporter failed with exit code {result.returncode}")
        st.text_area("Output", value=(result.stdout + "\n" + result.stderr).strip(), height=320)
