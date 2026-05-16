from __future__ import annotations

from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from services.storage import csv_values


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def sheets_service(credentials_path: Path, token_path: Path):
    if not credentials_path.exists():
        raise FileNotFoundError(f"Google credentials file not found: {credentials_path}")

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            token_path.parent.mkdir(parents=True, exist_ok=True)
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("sheets", "v4", credentials=creds)


def credentials_status(credentials_path: Path, token_path: Path) -> tuple[bool, bool]:
    return credentials_path.exists(), token_path.exists()


def start_manual_auth(credentials_path: Path) -> tuple[InstalledAppFlow, str]:
    if not credentials_path.exists():
        raise FileNotFoundError(f"Google credentials file not found: {credentials_path}")

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    flow.redirect_uri = "http://localhost"
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return flow, auth_url


def finish_manual_auth(flow: InstalledAppFlow, code: str, token_path: Path) -> Path:
    token_path.parent.mkdir(parents=True, exist_ok=True)
    flow.fetch_token(code=code.strip())
    token_path.write_text(flow.credentials.to_json(), encoding="utf-8")
    return token_path


def quote_sheet_name(sheet_name: str) -> str:
    return "'" + sheet_name.replace("'", "''") + "'"


def ensure_sheet_exists(service: Any, spreadsheet_id: str, sheet_name: str) -> None:
    spreadsheet = (
        service.spreadsheets()
        .get(spreadsheetId=spreadsheet_id, fields="sheets.properties.title")
        .execute()
    )
    titles = {
        sheet.get("properties", {}).get("title")
        for sheet in spreadsheet.get("sheets", [])
    }
    if sheet_name in titles:
        return

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [
                {
                    "addSheet": {
                        "properties": {
                            "title": sheet_name,
                        }
                    }
                }
            ]
        },
    ).execute()


def replace_sheet_with_csv(
    credentials_path: Path,
    token_path: Path,
    spreadsheet_id: str,
    sheet_name: str,
    csv_path: Path,
) -> int:
    values = csv_values(csv_path)
    if not values:
        raise ValueError(f"CSV has no rows: {csv_path}")

    service = sheets_service(credentials_path, token_path)
    ensure_sheet_exists(service, spreadsheet_id, sheet_name)
    sheet_range = quote_sheet_name(sheet_name)

    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range=sheet_range,
        body={},
    ).execute()

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_range}!A1",
        valueInputOption="USER_ENTERED",
        body={"values": values},
    ).execute()

    return len(values)
