from __future__ import annotations
import os
from pathlib import Path
import streamlit as st

APP_DIR = Path(__file__).resolve().parent

def get_default_paths() -> dict[str, Path]:
    reports_dir = Path(os.getenv("CRONOMETER_REPORTS_DIR", APP_DIR / "data" / "reports")).expanduser()
    cronometer_output_dir = Path(
        os.getenv("CRONOMETER_OUTPUT_DIR", reports_dir / "cronometer")
    ).expanduser()
    cronometer_project = Path(
        os.getenv(
            "CRONOMETER_GO_PROJECT",
            Path("/Users/rock/Documents/Code/GO/gocronometer/cronometerAPI"),
        )
    ).expanduser()
    
    return {
        "reports_dir": reports_dir,
        "garmin_output_dir": reports_dir / "garmin_sleep",
        "cronometer_output_dir": cronometer_output_dir,
        "garmin_token_dir": Path("/Users/rock/Documents/Code/secrets/garmin"),
        "google_credentials": Path("/Users/rock/Documents/Code/secrets/google/credentials.json"),
        "google_token": Path("/Users/rock/Documents/Code/secrets/google/google_token.json"),
        "cronometer_project": cronometer_project,
    }

def initialize_session_state():
    defaults = {
        "google_auth_flow": None,
        "google_auth_url": "",
        "spreadsheet_id": os.getenv("SPREADSHEET_ID", ""),
        "garmin_sheet": os.getenv("GARMIN_SLEEP_SHEET_NAME", "garminSleepReport"),
        "servings_sheet": os.getenv("GOOGLE_SHEET_NAME", ""),
        "daily_nutrition_sheet": os.getenv("DAILY_NUTRITION_SHEET_NAME", "dailyNutritionReport"),
        "biometrics_sheet": os.getenv("BIOMETRICS_SHEET_NAME", "biometricsReport"),
    }
    
    paths = get_default_paths()
    path_defaults = {
        "reports_dir": str(paths["reports_dir"]),
        "garmin_output_dir": str(paths["garmin_output_dir"]),
        "cronometer_output_dir": str(paths["cronometer_output_dir"]),
        "garmin_token_dir": str(paths["garmin_token_dir"]),
        "google_credentials": str(paths["google_credentials"]),
        "google_token": str(paths["google_token"]),
        "cronometer_project": str(paths["cronometer_project"]),
    }
    
    for key, value in {**defaults, **path_defaults}.items():
        st.session_state.setdefault(key, value)

def get_paths_from_session() -> dict[str, Path]:
    return {
        "reports_dir": Path(st.session_state.reports_dir).expanduser(),
        "garmin_output_dir": Path(st.session_state.garmin_output_dir).expanduser(),
        "cronometer_output_dir": Path(st.session_state.cronometer_output_dir).expanduser(),
        "garmin_token_dir": Path(st.session_state.garmin_token_dir).expanduser(),
        "google_credentials": Path(st.session_state.google_credentials).expanduser(),
        "google_token": Path(st.session_state.google_token).expanduser(),
        "cronometer_project": Path(st.session_state.cronometer_project).expanduser(),
    }
