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
        # Fetch body composition data for weight
        body_data = client.get_body_composition(date_text)
        daily_summary = client.get_user_summary(date_text)
        nutrition_food_log = client.get_nutrition_daily_food_log(date_text)
        nutrition_meals = client.get_nutrition_daily_meals(date_text)
        nutrition_settings = client.get_nutrition_daily_settings(date_text)
        
        if save_json:
            write_json(output_dir / f"sleep_{date_text}.json", sleep_data)
            write_json(output_dir / f"body_{date_text}.json", body_data)
            write_json(output_dir / f"daily_summary_{date_text}.json", daily_summary)
            write_json(output_dir / f"nutrition_food_log_{date_text}.json", nutrition_food_log)
            write_json(output_dir / f"nutrition_meals_{date_text}.json", nutrition_meals)
            write_json(output_dir / f"nutrition_settings_{date_text}.json", nutrition_settings)
            
        rows.append(
            sleep_summary_row(
                date_text,
                sleep_data,
                body_data,
                daily_summary,
                nutrition_food_log,
                nutrition_meals,
                nutrition_settings,
            )
        )

    csv_path = upsert_garmin_summary(output_dir, rows, "garmin_metrics_summary.csv")
    return csv_path, rows


def sleep_summary_row(
    cdate: str,
    sleep_data: dict[str, Any],
    body_data: dict[str, Any],
    daily_summary: dict[str, Any],
    nutrition_food_log: dict[str, Any],
    nutrition_meals: dict[str, Any],
    nutrition_settings: dict[str, Any],
) -> dict[str, Any]:
    sleep = sleep_data.get("dailySleepDTO") or {}
    scores = sleep.get("sleepScores") or {}
    overall_score = scores.get("overall") or {}
    calories_burned = extract_burned_calories(daily_summary)
    calories_consumed = extract_calories_consumed(
        nutrition_food_log,
        nutrition_meals,
        nutrition_settings,
    )
    
    # Extract weight from totalAverage object in body composition data
    weight = ""
    if body_data and "totalAverage" in body_data:
        raw_weight = body_data["totalAverage"].get("weight")
        if raw_weight:
            weight = f"{float(raw_weight) / 1000:.2f}"

    return {
        "date": cdate,
        "weight": weight,
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
        "calories_burned": calories_burned,
        "calories_consumed": calories_consumed,
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


def extract_calories_consumed(*payloads: dict[str, Any]) -> str:
    for payload in payloads:
        value = _find_calories_consumed_value(payload)
        if value is not None:
            return f"{float(value):.0f}"
    return ""


def extract_burned_calories(payload: dict[str, Any]) -> str:
    candidates = {
        _normalize_key("totalKilocalories"),
        _normalize_key("totalCalories"),
        _normalize_key("calories"),
        _normalize_key("total_kilocalories"),
        _normalize_key("total_calories"),
    }
    value = _find_value_by_keys(payload, candidates)
    return _format_numeric(value)


def _find_calories_consumed_value(payload: Any) -> float | int | None:
    if isinstance(payload, dict):
        summary_value = _extract_summary_calories(payload)
        if summary_value is not None:
            return summary_value

        direct_value = _extract_item_calories(payload)
        if direct_value is not None:
            return direct_value

        for key, value in payload.items():
            key_text = str(key).lower()
            if _looks_like_calorie_key(key_text):
                numeric = _coerce_numeric(value)
                if numeric is not None:
                    return numeric
        for value in payload.values():
            found = _find_calories_consumed_value(value)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _find_calories_consumed_value(item)
            if found is not None:
                return found
    return None


def _find_value_by_keys(payload: Any, candidate_keys: set[str]) -> float | int | None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            normalized = _normalize_key(key)
            if normalized in candidate_keys:
                numeric = _coerce_numeric(value)
                if numeric is not None:
                    return numeric
        for value in payload.values():
            found = _find_value_by_keys(value, candidate_keys)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _find_value_by_keys(item, candidate_keys)
            if found is not None:
                return found
    return None


def _extract_summary_calories(payload: dict[str, Any]) -> float | int | None:
    preferred_keys = [
        "caloriesconsumed",
        "consumedcalories",
        "consumedkcal",
        "dailycaloriesconsumed",
        "totalkilocalories",
        "totalkilocalories",
        "totalcalories",
        "calories",
        "kcal",
        "energy",
    ]
    for key, value in payload.items():
        key_text = _normalize_key(key)
        if any(token in key_text for token in preferred_keys):
            numeric = _coerce_numeric(value)
            if numeric is not None:
                return numeric
    return None


def _extract_item_calories(payload: dict[str, Any]) -> float | int | None:
    total = 0.0
    matched = False
    for key, value in payload.items():
        if isinstance(value, list):
            for item in value:
                item_total = _find_calories_consumed_value(item)
                if item_total is not None:
                    total += float(item_total)
                    matched = True
        elif isinstance(value, dict):
            item_total = _find_calories_consumed_value(value)
            if item_total is not None:
                total += float(item_total)
                matched = True
    return total if matched else None


def _looks_like_calorie_key(key_text: str) -> bool:
    return (
        "calor" in key_text
        or "kcal" in key_text
        or "energy" in key_text
    )


def _normalize_key(key: Any) -> str:
    text = str(key).lower()
    return "".join(ch for ch in text if ch.isalnum())


def _coerce_numeric(value: Any) -> float | int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def _format_numeric(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):.0f}"
    except (TypeError, ValueError):
        return ""
