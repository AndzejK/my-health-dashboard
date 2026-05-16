from __future__ import annotations

import os
import subprocess
from pathlib import Path


def run_go_exporter(
    project_dir: Path,
    target_date: str,
    reports_dir: Path,
    spreadsheet_id: str,
    servings_sheet: str,
    biometrics_sheet: str,
    garmin_sheet: str,
    google_credentials: Path,
    google_token: Path,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CRONOMETER_REPORTS_DIR"] = str(reports_dir)
    env["SPREADSHEET_ID"] = spreadsheet_id
    env["GOOGLE_SHEET_NAME"] = servings_sheet
    env["BIOMETRICS_SHEET_NAME"] = biometrics_sheet
    env["GARMIN_SLEEP_SHEET_NAME"] = garmin_sheet
    env["GOOGLE_CREDENTIALS_FILE"] = str(google_credentials)
    env["GOOGLE_TOKEN_FILE"] = str(google_token)

    return subprocess.run(
        ["go", "run", "main.go", target_date],
        cwd=project_dir,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
