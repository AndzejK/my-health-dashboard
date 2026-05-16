from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from garminconnect import Garmin

from services.storage import upsert_garmin_summary, write_json


def date_range(start_date: date, end_date: date) -> list[date]:
    if start_date > end_date:
        raise ValueError("Start date cannot be after end date.")
    day_count = (end_date - start_date).days + 1
    return [start_date + timedelta(days=offset) for offset in range(day_count)]


def login(
    token_dir: Path,
    email: str | None,
    password: str | None,
    mfa_callback: Callable[[], str],
) -> Garmin:
    token_dir.mkdir(parents=True, exist_ok=True)
    has_saved_tokens = any(token_dir.iterdir())

    if not has_saved_tokens and (not email or not password):
        raise ValueError("Garmin email and password are required for the first login.")

    client = Garmin(
        email=email,
        password=password,
        prompt_mfa=mfa_callback,
    )
    client.login(str(token_dir))
    return client


def pull_sleep_range(
    start_date: date,
    end_date: date,
    output_dir: Path,
    token_dir: Path,
    email: str | None,
    password: str | None,
    mfa_code: str | None,
    save_json: bool,
) -> tuple[Path, list[dict[str, Any]]]:
    client = login(
        token_dir=token_dir,
        email=email,
        password=password,
        mfa_callback=lambda: mfa_code or "",
    )

    rows: list[dict[str, Any]] = []
    for current_date in date_range(start_date, end_date):
        date_text = current_date.isoformat()
        sleep_data = client.get_sleep_data(date_text)
        if save_json:
            write_json(output_dir / f"sleep_{date_text}.json", sleep_data)
        rows.append(sleep_summary_row(date_text, sleep_data))

    csv_path = upsert_garmin_summary(output_dir, rows)
    return csv_path, rows


def sleep_summary_row(cdate: str, sleep_data: dict[str, Any]) -> dict[str, Any]:
    sleep = sleep_data.get("dailySleepDTO") or {}
    scores = sleep.get("sleepScores") or {}
    overall_score = scores.get("overall") or {}

    return {
        "date": cdate,
        "total_sleep": seconds_to_hm(sleep.get("sleepTimeSeconds")),
        "total_sleep_hours": seconds_to_hours(sleep.get("sleepTimeSeconds")),
        "deep_sleep": seconds_to_hm(sleep.get("deepSleepSeconds")),
        "deep_sleep_hours": seconds_to_hours(sleep.get("deepSleepSeconds")),
        "rem_sleep": seconds_to_hm(sleep.get("remSleepSeconds")),
        "rem_sleep_hours": seconds_to_hours(sleep.get("remSleepSeconds")),
        "sleep_score": overall_score.get("value", ""),
        "light_sleep": seconds_to_hm(sleep.get("lightSleepSeconds")),
        "light_sleep_hours": seconds_to_hours(sleep.get("lightSleepSeconds")),
        "awake": seconds_to_hm(sleep.get("awakeSleepSeconds")),
        "awake_hours": seconds_to_hours(sleep.get("awakeSleepSeconds")),
        "sleep_start_local": epoch_ms_to_datetime(sleep.get("sleepStartTimestampLocal")),
        "sleep_end_local": epoch_ms_to_datetime(sleep.get("sleepEndTimestampLocal")),
        "sleep_start_gmt": epoch_ms_to_datetime(sleep.get("sleepStartTimestampGMT")),
        "sleep_end_gmt": epoch_ms_to_datetime(sleep.get("sleepEndTimestampGMT")),
        "sleep_start_local_ms": sleep.get("sleepStartTimestampLocal", ""),
        "sleep_end_local_ms": sleep.get("sleepEndTimestampLocal", ""),
    }


def seconds_to_hours(value: Any) -> str:
    if value is None:
        return ""
    return f"{float(value) / 3600:.2f}"


def seconds_to_hm(value: Any) -> str:
    if value is None:
        return ""

    total_minutes = round(float(value) / 60)
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours}:{minutes:02d}"


def epoch_ms_to_datetime(value: Any) -> str:
    if value in (None, ""):
        return ""

    return datetime.fromtimestamp(float(value) / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
