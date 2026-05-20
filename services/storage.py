from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pandas as pd


GARMIN_FIELDNAMES = [
    "date",
    "total_sleep",
    "total_sleep_hours",
    "deep_sleep",
    "deep_sleep_hours",
    "rem_sleep",
    "rem_sleep_hours",
    "sleep_score",
    "light_sleep",
    "light_sleep_hours",
    "awake",
    "awake_hours",
    "weight",
    "sleep_start_local",
    "sleep_end_local",
    "sleep_start_gmt",
    "sleep_end_gmt",
    "sleep_start_local_ms",
    "sleep_end_local_ms",
]


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def read_summary_rows(csv_path: Path) -> dict[str, dict[str, Any]]:
    if not csv_path.exists():
        return {}

    with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
        return {
            row["date"]: normalize_garmin_row(row)
            for row in csv.DictReader(csv_file)
            if row.get("date")
        }


def normalize_garmin_row(row: dict[str, Any]) -> dict[str, Any]:
    if "sleep_time" in row and "total_sleep" not in row:
        row["total_sleep"] = row.get("sleep_time", "")
    if "sleep_time_hours" in row and "total_sleep_hours" not in row:
        row["total_sleep_hours"] = row.get("sleep_time_hours", "")
    return row


def upsert_garmin_summary(output_dir: Path, rows: list[dict[str, Any]], filename: str = "garmin_metrics_summary.csv") -> Path:
    ensure_dir(output_dir)
    csv_path = output_dir / filename
    existing_rows = read_summary_rows(csv_path)

    for row in rows:
        existing_rows[row["date"]] = row

    sorted_rows = [
        existing_rows[row_date]
        for row_date in sorted(existing_rows.keys(), reverse=True)
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=GARMIN_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted_rows)

    return csv_path


def read_csv_dataframe(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        return pd.DataFrame()
    return pd.read_csv(csv_path)


def csv_values(csv_path: Path) -> list[list[Any]]:
    if not csv_path.exists():
        return []

    with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
        return [row for row in csv.reader(csv_file)]
