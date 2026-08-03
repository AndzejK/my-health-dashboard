from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from services.cronometer import run_go_exporter
from services.storage import read_csv_dataframe


MEAL_ORDER = [
    "Breakfast",
    "Lunch",
    "Dinner",
    "Snacks",
    "Drinks",
    "Vitamins",
    "Minerals",
    "Amino Acids",
]

NUTRIENT_CATEGORIES: dict[str, list[str]] = {
    "Macros": [
        "Energy (kcal)",
        "Alcohol (g)",
        "Caffeine (mg)",
        "Water (g)",
        "Net Carbs (g)",
        "Carbs (g)",
        "Fiber (g)",
        "Fat (g)",
        "Protein (g)",
        "Cholesterol (mg)",
    ],
    "Vitamins": [
        "B1 (Thiamine) (mg)",
        "B2 (Riboflavin) (mg)",
        "B3 (Niacin) (mg)",
        "B5 (Pantothenic Acid) (mg)",
        "B6 (Pyridoxine) (mg)",
        "B12 (Cobalamin) (µg)",
        "Folate (µg)",
        "Vitamin A (µg)",
        "Vitamin C (mg)",
        "Vitamin D (IU)",
        "Vitamin E (mg)",
        "Vitamin K (µg)",
    ],
    "Minerals": [
        "Calcium (mg)",
        "Copper (mg)",
        "Iron (mg)",
        "Magnesium (mg)",
        "Manganese (mg)",
        "Phosphorus (mg)",
        "Potassium (mg)",
        "Selenium (µg)",
        "Sodium (mg)",
        "Zinc (mg)",
        "Oxalate (mg)",
        "Phytate (mg)",
    ],
    "Other nutrients": [
        "Omega-3 (g)",
        "ALA (g)",
        "DHA (g)",
        "EPA (g)",
        "Omega-6 (g)",
        "AA (g)",
        "LA (g)",
        "Cystine (g)",
        "Histidine (g)",
        "Isoleucine (g)",
        "Leucine (g)",
        "Lysine (g)",
        "Methionine (g)",
        "Phenylalanine (g)",
        "Threonine (g)",
        "Tryptophan (g)",
        "Tyrosine (g)",
        "Valine (g)",
    ],
}


def render_cronometer_controls(paths: dict) -> None:
    st.subheader("Cronometer Dashboard")
    st.caption("Pick a date range, fetch only the sections you want, and choose whether to sync to Google Sheets.")

    local_cache = load_latest_local_run(paths)
    if "cronometer_last_run" not in st.session_state and local_cache is not None:
        st.session_state.cronometer_last_run = local_cache

    cache_status = get_cache_status(paths)
    if cache_status:
        st.info(cache_status)

    today = date.today()
    col_start, col_end = st.columns(2)
    with col_start:
        start_date = st.date_input(
            "Start date",
            value=today - timedelta(days=1),
            key="cronometer_start_date",
        )
    with col_end:
        end_date = st.date_input(
            "End date",
            value=today - timedelta(days=1),
            key="cronometer_end_date",
        )

    sync_to_google_sheets = st.checkbox(
        "Sync to Google Sheets",
        value=True,
        key="cronometer_sync_to_google_sheets",
        help="Turn this off to keep the run local only.",
    )

    with st.expander("Fetch options", expanded=True):
        st.caption("Select only the sections you want Cronometer to fetch.")
        col_a, col_b = st.columns(2)
        with col_a:
            fetch_servings = st.checkbox("Food Diary", value=True, key="cronometer_fetch_servings")
            fetch_daily_nutrition = st.checkbox(
                "Micronutrients", value=True, key="cronometer_fetch_daily_nutrition"
            )
        with col_b:
            fetch_biometrics = st.checkbox("Biometrics", value=False, key="cronometer_fetch_biometrics")
            fetch_notes = st.checkbox("Notes", value=False, key="cronometer_fetch_notes")

    col_refresh, col_fetch = st.columns(2)
    with col_refresh:
        if st.button("Reload local cache"):
            refreshed_cache = load_latest_local_run(paths)
            if refreshed_cache is None:
                st.warning("No saved Cronometer files were found in the local output folder.")
            else:
                st.session_state.cronometer_last_run = refreshed_cache
                st.success("Loaded the latest local Cronometer files.")
                st.rerun()

    with col_fetch:
        fetch_clicked = st.button("Fetch Cronometer data")

    if fetch_clicked:
        if not any([fetch_servings, fetch_daily_nutrition, fetch_biometrics, fetch_notes]):
            st.warning("Select at least one Cronometer section to fetch.")
            return
        if end_date < start_date:
            st.error("End date must be on or after start date.")
            return
        if sync_to_google_sheets and not st.session_state.spreadsheet_id.strip():
            st.error("Set a Spreadsheet ID in Settings or turn off Google Sheets sync.")
            return

        result = run_go_exporter(
            project_dir=paths["cronometer_project"],
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            reports_dir=paths["cronometer_output_dir"],
            spreadsheet_id=st.session_state.spreadsheet_id,
            servings_sheet=st.session_state.servings_sheet,
            daily_nutrition_sheet=st.session_state.daily_nutrition_sheet,
            biometrics_sheet=st.session_state.biometrics_sheet,
            garmin_sheet=st.session_state.garmin_sheet,
            google_credentials=paths["google_credentials"],
            google_token=paths["google_token"],
            fetch_servings=fetch_servings,
            fetch_daily_nutrition=fetch_daily_nutrition,
            fetch_biometrics=fetch_biometrics,
            fetch_notes=fetch_notes,
            sync_to_google_sheets=sync_to_google_sheets,
        )

        range_label = format_range_label(start_date, end_date)
        st.session_state.cronometer_last_run = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "range_label": range_label,
            "fetch_servings": fetch_servings,
            "fetch_daily_nutrition": fetch_daily_nutrition,
            "fetch_biometrics": fetch_biometrics,
            "fetch_notes": fetch_notes,
            "sync_to_google_sheets": sync_to_google_sheets,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

        if result.returncode == 0:
            st.success("Cronometer fetch complete.")
        else:
            st.error(f"Cronometer exporter failed with exit code {result.returncode}")

    last_run = st.session_state.get("cronometer_last_run")
    if last_run:
        render_cronometer_results(paths, last_run)
        render_execution_log(last_run)


def render_cronometer_results(paths: dict, run_info: dict) -> None:
    servings_path, daily_path, _, _ = build_export_paths(paths, run_info)
    servings_df = read_csv_dataframe(servings_path)
    daily_df = read_csv_dataframe(daily_path)

    available_dates = collect_available_dates(servings_df, daily_df)
    if not available_dates:
        st.info("No Cronometer data is available yet for the selected run.")
        return

    default_date = run_info.get("end_date") or available_dates[0]
    if default_date not in available_dates:
        default_date = available_dates[0]

    selected_date = st.selectbox(
        "View day",
        available_dates,
        index=available_dates.index(default_date),
        key=f"cronometer_view_day_{run_info.get('range_label', 'latest')}",
    )

    food_tab, micros_tab = st.tabs(["Food Diary", "Micronutrients"])
    with food_tab:
        render_food_diary_tab(servings_df, daily_df, selected_date)
    with micros_tab:
        render_micronutrients_tab(daily_df, selected_date)


def render_execution_log(run_info: dict) -> None:
    with st.expander("Execution log", expanded=False):
        stdout = run_info.get("stdout", "")
        stderr = run_info.get("stderr", "")
        st.text_area(
            "Output",
            value=(stdout + "\n" + stderr).strip(),
            height=320,
        )


def render_food_diary_tab(servings_df: pd.DataFrame, daily_df: pd.DataFrame, selected_date: str) -> None:
    st.caption("What you ate for the selected day, grouped by meal.")

    day_df = filter_day_frame(servings_df, "Day", selected_date)
    if day_df.empty:
        st.info("No food diary entries found for this day.")
    else:
        day_df = day_df.copy()
        for column in ["Group", "Food Name", "Amount", "Category"]:
            if column not in day_df.columns:
                day_df[column] = ""

        summary = get_daily_summary_row(daily_df, selected_date)
        if summary is not None:
            metric_cols = st.columns(4)
            metric_cols[0].metric("Energy", format_metric(summary.get("Energy (kcal)"), "kcal"))
            metric_cols[1].metric("Protein", format_metric(summary.get("Protein (g)"), "g"))
            metric_cols[2].metric("Carbs", format_metric(summary.get("Carbs (g)"), "g"))
            metric_cols[3].metric("Fat", format_metric(summary.get("Fat (g)"), "g"))

        st.dataframe(
            day_df[["Group", "Food Name", "Amount", "Category"]].reset_index(drop=True),
            width="stretch",
            hide_index=True,
        )

        st.markdown("#### Grouped by meal")
        meal_groups = ordered_groups(day_df["Group"].fillna("Other").astype(str).tolist())
        for group_name in meal_groups:
            meal_df = day_df[day_df["Group"].fillna("Other").astype(str) == group_name]
            with st.expander(group_name, expanded=(group_name == meal_groups[0])):
                st.dataframe(
                    meal_df[["Food Name", "Amount", "Category"]].reset_index(drop=True),
                    width="stretch",
                    hide_index=True,
                )


def render_micronutrients_tab(daily_df: pd.DataFrame, selected_date: str) -> None:
    st.caption("Micronutrients and nutrient totals for the selected day.")

    summary = get_daily_summary_row(daily_df, selected_date)
    if summary is None:
        st.info("No micronutrient summary found for this day.")
        return

    metric_cols = st.columns(4)
    metric_cols[0].metric("Energy", format_metric(summary.get("Energy (kcal)"), "kcal"))
    metric_cols[1].metric("Water", format_metric(summary.get("Water (g)"), "g"))
    metric_cols[2].metric("Protein", format_metric(summary.get("Protein (g)"), "g"))
    metric_cols[3].metric("Sodium", format_metric(summary.get("Sodium (mg)"), "mg"))

    category = st.selectbox(
        "Micronutrient category",
        list(NUTRIENT_CATEGORIES.keys()),
        key=f"cronometer_micronutrient_category_{selected_date}",
    )

    nutrient_df = build_nutrient_frame(summary, NUTRIENT_CATEGORIES[category])
    if nutrient_df.empty:
        st.info("No values found for this category.")
        return

    chart = (
        alt.Chart(nutrient_df)
        .mark_bar(color="#2a9d8f")
        .encode(
            y=alt.Y("nutrient:N", sort="-x", title=None),
            x=alt.X("value:Q", title=None),
            tooltip=[
                alt.Tooltip("nutrient:N", title="Nutrient"),
                alt.Tooltip("value:Q", title="Amount", format=".2f"),
                alt.Tooltip("unit:N", title="Unit"),
            ],
        )
        .properties(height=max(260, 24 * len(nutrient_df)))
    )

    st.altair_chart(chart, width="stretch")
    st.dataframe(nutrient_df, width="stretch", hide_index=True)


def build_export_paths(paths: dict, run_info: dict) -> tuple[Path, Path, Path, Path]:
    servings_path_str = str(run_info.get("servings_path", "")).strip()
    daily_path_str = str(run_info.get("daily_nutrition_path", "")).strip()
    biometrics_path_str = str(run_info.get("biometrics_path", "")).strip()
    notes_path_str = str(run_info.get("notes_path", "")).strip()
    range_label = run_info.get("range_label", "")

    servings_path = Path(servings_path_str) if servings_path_str else paths["cronometer_output_dir"] / f"servings_{range_label}.csv"
    daily_path = Path(daily_path_str) if daily_path_str else paths["cronometer_output_dir"] / "daily_nutrition.csv"
    biometrics_path = Path(biometrics_path_str) if biometrics_path_str else paths["cronometer_output_dir"] / f"biometrics_{range_label}.csv"
    notes_path = Path(notes_path_str) if notes_path_str else paths["cronometer_output_dir"] / f"notes_{range_label}.csv"

    return servings_path, daily_path, biometrics_path, notes_path


def collect_available_dates(servings_df: pd.DataFrame, daily_df: pd.DataFrame) -> list[str]:
    dates: set[str] = set()
    if not servings_df.empty and "Day" in servings_df.columns:
        dates.update(filter(None, servings_df["Day"].astype(str).tolist()))
    if not daily_df.empty and "Date" in daily_df.columns:
        dates.update(filter(None, daily_df["Date"].astype(str).tolist()))
    return sorted(dates, reverse=True)


def filter_day_frame(df: pd.DataFrame, date_column: str, selected_date: str) -> pd.DataFrame:
    if df.empty or date_column not in df.columns:
        return pd.DataFrame()
    filtered = df[df[date_column].astype(str) == selected_date].copy()
    if "Group" in filtered.columns:
        filtered["Group"] = filtered["Group"].fillna("Other")
    return filtered


def get_daily_summary_row(daily_df: pd.DataFrame, selected_date: str) -> pd.Series | None:
    if daily_df.empty or "Date" not in daily_df.columns:
        return None
    matches = daily_df[daily_df["Date"].astype(str) == selected_date]
    if matches.empty:
        return None
    return matches.iloc[0]


def build_nutrient_frame(summary: pd.Series, nutrient_columns: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for column in nutrient_columns:
        if column not in summary.index:
            continue
        value = pd.to_numeric(pd.Series([summary.get(column)]), errors="coerce").iloc[0]
        if pd.isna(value):
            continue
        unit = column[column.rfind("(") + 1 : column.rfind(")")] if "(" in column and ")" in column else ""
        rows.append(
            {
                "nutrient": column,
                "value": float(value),
                "unit": unit,
            }
        )

    nutrient_df = pd.DataFrame(rows)
    if nutrient_df.empty:
        return nutrient_df
    return nutrient_df.sort_values("value", ascending=False).reset_index(drop=True)


def ordered_groups(groups: list[str]) -> list[str]:
    seen: list[str] = []
    for group in groups:
        if group not in seen:
            seen.append(group)
    preferred = [group for group in MEAL_ORDER if group in seen]
    remaining = [group for group in seen if group not in preferred]
    return preferred + remaining


def format_metric(value: object, unit: str) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "N/A"
    return f"{numeric:.2f} {unit}".strip()


def format_range_label(start_date: date, end_date: date) -> str:
    start = start_date.isoformat()
    end = end_date.isoformat()
    if start == end:
        return start
    return f"{start}_to_{end}"


def load_latest_local_run(paths: dict) -> dict | None:
    output_dir = paths["cronometer_output_dir"]
    if not output_dir.exists():
        return None

    servings_files = sorted(output_dir.glob("servings_*.csv"), key=lambda path: path.stat().st_mtime, reverse=True)
    latest_servings = servings_files[0] if servings_files else None
    daily_path = output_dir / "daily_nutrition.csv"
    biometrics_files = sorted(output_dir.glob("biometrics_*.csv"), key=lambda path: path.stat().st_mtime, reverse=True)
    latest_biometrics = biometrics_files[0] if biometrics_files else None
    notes_files = sorted(output_dir.glob("notes_*.csv"), key=lambda path: path.stat().st_mtime, reverse=True)
    latest_notes = notes_files[0] if notes_files else None

    if latest_servings is None and not daily_path.exists() and latest_biometrics is None and latest_notes is None:
        return None

    range_label = latest_servings.stem.removeprefix("servings_") if latest_servings else "local_cache"
    servings_df = read_csv_dataframe(latest_servings) if latest_servings else pd.DataFrame()
    daily_df = read_csv_dataframe(daily_path) if daily_path.exists() else pd.DataFrame()

    available_dates = collect_available_dates(servings_df, daily_df)
    end_date = available_dates[0] if available_dates else ""

    return {
        "source": "local_cache",
        "range_label": range_label,
        "servings_path": str(latest_servings) if latest_servings else "",
        "daily_nutrition_path": str(daily_path) if daily_path.exists() else "",
        "biometrics_path": str(latest_biometrics) if latest_biometrics else "",
        "notes_path": str(latest_notes) if latest_notes else "",
        "start_date": "",
        "end_date": end_date,
        "fetch_servings": True,
        "fetch_daily_nutrition": daily_path.exists(),
        "fetch_biometrics": latest_biometrics is not None,
        "fetch_notes": latest_notes is not None,
        "sync_to_google_sheets": False,
        "stdout": "",
        "stderr": "",
        "returncode": 0,
    }


def get_cache_status(paths: dict) -> str | None:
    local_run = load_latest_local_run(paths)
    if local_run is None:
        return "No cached Cronometer files found yet. Fetch once and the app will show them here on future visits."

    servings_path = local_run.get("servings_path")
    daily_path = local_run.get("daily_nutrition_path")
    details = []
    if servings_path:
        details.append(f"Food Diary: `{Path(servings_path).name}`")
    if daily_path:
        details.append(f"Micronutrients: `{Path(daily_path).name}`")
    return "Using saved local Cronometer files. " + " | ".join(details)
