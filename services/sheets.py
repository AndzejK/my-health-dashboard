from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from services.storage import csv_values


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _read_json_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _is_client_secrets_file(path: Path) -> bool:
    try:
        data = _read_json_file(path)
    except Exception:
        return False
    return "installed" in data or "web" in data


def _is_authorized_user_file(path: Path) -> bool:
    try:
        data = _read_json_file(path)
    except Exception:
        return False
    return "refresh_token" in data and "token_uri" in data


def _client_secret_payload(credentials_path: Path) -> dict[str, Any]:
    data = _read_json_file(credentials_path)
    if "installed" in data:
        return data["installed"]
    if "web" in data:
        return data["web"]
    raise ValueError(
        f"Google credentials file is not a valid OAuth client secrets JSON: {credentials_path}"
    )


def _load_authorized_credentials(credentials_path: Path, token_path: Path) -> Credentials:
    token_data = _read_json_file(token_path)
    secrets_data = _client_secret_payload(credentials_path)

    merged = dict(token_data)
    merged.setdefault("client_id", secrets_data.get("client_id"))
    merged.setdefault("client_secret", secrets_data.get("client_secret"))
    merged.setdefault("token_uri", secrets_data.get("token_uri"))
    merged.setdefault("scopes", SCOPES)

    return Credentials.from_authorized_user_info(merged, SCOPES)


def sheets_service(credentials_path: Path, token_path: Path):
    if not credentials_path.exists():
        raise FileNotFoundError(f"Google credentials file not found: {credentials_path}")
    if not _is_client_secrets_file(credentials_path):
        raise ValueError(
            f"Google credentials file is not a valid OAuth client secrets JSON: {credentials_path}. "
            "Make sure this points to the downloaded Google OAuth client file, not the token file."
        )

    creds = None
    if token_path.exists():
        if not _is_authorized_user_file(token_path):
            raise ValueError(
                f"Google token file is not a valid authorized-user JSON: {token_path}. "
                "Delete it and re-run Google auth if needed."
            )
        creds = _load_authorized_credentials(credentials_path, token_path)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            token_path.parent.mkdir(parents=True, exist_ok=True)
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_payload = json.loads(creds.to_json())
        secrets_data = _client_secret_payload(credentials_path)
        token_payload.setdefault("client_id", secrets_data.get("client_id"))
        token_payload.setdefault("client_secret", secrets_data.get("client_secret"))
        token_payload.setdefault("token_uri", secrets_data.get("token_uri"))
        token_payload.setdefault("scopes", SCOPES)
        token_path.write_text(json.dumps(token_payload, indent=2, sort_keys=True), encoding="utf-8")

    return build("sheets", "v4", credentials=creds)


def credentials_status(credentials_path: Path, token_path: Path) -> tuple[bool, bool]:
    return credentials_path.exists(), token_path.exists()


def start_manual_auth(credentials_path: Path) -> tuple[InstalledAppFlow, str]:
    if not credentials_path.exists():
        raise FileNotFoundError(f"Google credentials file not found: {credentials_path}")
    if not _is_client_secrets_file(credentials_path):
        raise ValueError(
            f"Google credentials file is not a valid OAuth client secrets JSON: {credentials_path}. "
            "Make sure this points to the downloaded Google OAuth client file, not the token file."
        )

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
    token_payload = json.loads(flow.credentials.to_json())
    token_payload.setdefault("client_id", flow.client_config.get("client_id"))
    token_payload.setdefault("client_secret", flow.client_config.get("client_secret"))
    token_payload.setdefault("token_uri", flow.client_config.get("token_uri"))
    token_payload.setdefault("scopes", SCOPES)
    token_path.write_text(json.dumps(token_payload, indent=2, sort_keys=True), encoding="utf-8")
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
