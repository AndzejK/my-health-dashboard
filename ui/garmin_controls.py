import streamlit as st
import os
from datetime import date, timedelta
import pandas as pd
from services.garmin import pull_sleep_range
from services.sheets import replace_sheet_with_csv
from services.storage import read_csv_dataframe

def render_garmin_controls(paths: dict) -> None:
    st.subheader("Pull Sleep Data")
    today = date.today()
    col_start, col_end = st.columns(2)
    with col_start:
        start_date = st.date_input("Start date", value=today - timedelta(days=1))
    with col_end:
        end_date = st.date_input("End date", value=today)

    col_email, col_password, col_mfa = st.columns(3)
    with col_email:
        garmin_email = st.text_input("Garmin email", value=os.getenv("GARMIN_EMAIL", ""))
    with col_password:
        garmin_password = st.text_input("Garmin password", value=os.getenv("GARMIN_PASSWORD", ""), type="password")
    with col_mfa:
        garmin_mfa = st.text_input("MFA code, if prompted")

    save_json = st.checkbox("Save raw daily JSON", value=True)

    if st.button("Pull Garmin sleep", type="primary"):
        try:
            csv_path, rows = pull_sleep_range(
                start_date=start_date,
                end_date=end_date,
                output_dir=paths["garmin_output_dir"],
                token_dir=paths["garmin_token_dir"],
                email=garmin_email or None,
                password=garmin_password or None,
                mfa_code=garmin_mfa or None,
                save_json=save_json,
            )
            st.success(f"Updated {csv_path}")
            st.dataframe(pd.DataFrame(rows), width="stretch")
            st.session_state["garmin_data_pulled"] = True
        except Exception as exc:
            st.error(str(exc))

    st.subheader("Sync to Google Sheets")
    garmin_csv = paths["garmin_output_dir"] / "sleep_summary.csv"
    st.write(f"Source: `{garmin_csv}`")

    if st.button("Push to Google Sheets"):
        try:
            row_count = replace_sheet_with_csv(
                credentials_path=paths["google_credentials"],
                token_path=paths["google_token"],
                spreadsheet_id=st.session_state.spreadsheet_id,
                sheet_name=st.session_state.garmin_sheet,
                csv_path=garmin_csv,
            )
            st.success(f"Synced {row_count} rows to {st.session_state.garmin_sheet}")
        except Exception as exc:
            st.error(str(exc))
