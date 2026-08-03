from __future__ import annotations

import os
import subprocess
from pathlib import Path


def run_go_exporter(
    project_dir: Path,
    start_date: str,
    end_date: str,
    reports_dir: Path,
    spreadsheet_id: str,
    servings_sheet: str,
    daily_nutrition_sheet: str,
    biometrics_sheet: str,
    garmin_sheet: str,
    google_credentials: Path,
    google_token: Path,
    fetch_servings: bool,
    fetch_daily_nutrition: bool,
    fetch_biometrics: bool,
    fetch_notes: bool,
    sync_to_google_sheets: bool,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CRONOMETER_REPORTS_DIR"] = str(reports_dir)
    env["SPREADSHEET_ID"] = spreadsheet_id if sync_to_google_sheets else ""
    env["GOOGLE_SHEET_NAME"] = servings_sheet
    env["DAILY_NUTRITION_SHEET_NAME"] = daily_nutrition_sheet
    env["BIOMETRICS_SHEET_NAME"] = biometrics_sheet
    env["GARMIN_SLEEP_SHEET_NAME"] = garmin_sheet
    env["GOOGLE_CREDENTIALS_FILE"] = str(google_credentials)
    env["GOOGLE_TOKEN_FILE"] = str(google_token)
    env["CRONOMETER_FETCH_SERVINGS"] = "1" if fetch_servings else "0"
    env["CRONOMETER_FETCH_DAILY_NUTRITION"] = "1" if fetch_daily_nutrition else "0"
    env["CRONOMETER_FETCH_BIOMETRICS"] = "1" if fetch_biometrics else "0"
    env["CRONOMETER_FETCH_NOTES"] = "1" if fetch_notes else "0"

    if not project_dir.exists():
        raise FileNotFoundError(
            f"Cronometer Go project folder not found: {project_dir}. "
            "Set the correct path in Settings or set CRONOMETER_GO_PROJECT."
        )

    main_go = project_dir / "main.go"
    if not main_go.exists():
        raise FileNotFoundError(
            f"main.go not found in Cronometer Go project folder: {project_dir}"
        )

    return subprocess.run(
        ["go", "run", "main.go", start_date, end_date],
        cwd=project_dir,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
