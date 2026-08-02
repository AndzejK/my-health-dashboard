import streamlit as st
from services.sheets import (
    credentials_status,
    finish_manual_auth,
    start_manual_auth,
)
import os

def render_settings(paths: dict) -> None:
    st.header("Settings")

    st.subheader("Workspace")
    st.text_input("Reports folder", key="reports_dir")
    st.text_input("Garmin output folder", key="garmin_output_dir")
    st.text_input("Cronometer output folder", key="cronometer_output_dir")
    st.text_input("Garmin token folder", key="garmin_token_dir")
    st.text_input("Go project folder", key="cronometer_project")

    st.subheader("Google Sheets")
    st.text_input("Spreadsheet ID", key="spreadsheet_id")
    st.text_input("Garmin sheet", key="garmin_sheet")
    st.text_input("Servings sheet", key="servings_sheet")
    st.text_input("Daily nutrition sheet", key="daily_nutrition_sheet")
    st.text_input("Biometrics sheet", key="biometrics_sheet")
    st.text_input("Google credentials file", key="google_credentials")
    st.text_input("Google token file", key="google_token")

    has_credentials, has_token = credentials_status(paths["google_credentials"], paths["google_token"])
    st.write(f"Credentials file: `{'found' if has_credentials else 'missing'}`")
    st.write(f"Token file: `{'found' if has_token else 'missing'}`")

    col_auth_start, col_auth_clear = st.columns(2)
    with col_auth_start:
        if st.button("Start Google auth"):
            try:
                flow, auth_url = start_manual_auth(paths["google_credentials"])
                st.session_state.google_auth_flow = flow
                st.session_state.google_auth_url = auth_url
            except Exception as exc:
                st.error(str(exc))
    with col_auth_clear:
        if st.button("Forget pending auth"):
            st.session_state.google_auth_flow = None
            st.session_state.google_auth_url = ""

    if st.session_state.google_auth_url:
        st.text_area("Open this URL in your browser", value=st.session_state.google_auth_url, height=160)
        auth_code = st.text_input("Paste the Google authorization code")
        if st.button("Save Google token"):
            try:
                if st.session_state.google_auth_flow is None:
                    raise ValueError("No active Google auth flow. Start auth again.")
                token_path = finish_manual_auth(
                    flow=st.session_state.google_auth_flow,
                    code=auth_code,
                    token_path=paths["google_token"],
                )
                st.session_state.google_auth_flow = None
                st.session_state.google_auth_url = ""
                st.success(f"Saved Google token to {token_path}")
            except Exception as exc:
                st.error(str(exc))
