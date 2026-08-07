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
            "servings_path": str(paths["cronometer_output_dir"] / "servings.csv"),
            "daily_nutrition_path": str(paths["cronometer_output_dir"] / "daily_nutrition.csv"),
            "biometrics_path": str(paths["cronometer_output_dir"] / "biometrics.csv"),
            "notes_path": str(paths["cronometer_output_dir"] / "notes.csv"),
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

    food_tab, micros_tab, trends_tab = st.tabs(["Food Diary", "Micronutrients", "Trends"])
    with food_tab:
        render_food_diary_tab(servings_df, daily_df, selected_date)
    with micros_tab:
        render_micronutrients_tab(daily_df, selected_date)
    with trends_tab:
        render_trends_tab(servings_df, daily_df, run_info)


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


def render_trends_tab(servings_df: pd.DataFrame, daily_df: pd.DataFrame, run_info: dict) -> None:
    st.caption("Compare a date range against your full saved history.")

    if daily_df.empty or "Date" not in daily_df.columns:
        st.info("No saved micronutrient history is available yet.")
        return

    history_dates = pd.to_datetime(daily_df["Date"], errors="coerce").dropna().dt.date
    if history_dates.empty:
        st.info("No valid dates were found in the saved micronutrient file.")
        return

    history_start = min(history_dates)
    history_end = max(history_dates)

    default_start = parse_iso_date(run_info.get("start_date")) or history_start
    default_end = parse_iso_date(run_info.get("end_date")) or history_end
    if default_start < history_start:
        default_start = history_start
    if default_end > history_end:
        default_end = history_end

    col_start, col_end = st.columns(2)
    with col_start:
        trend_start = st.date_input(
            "Trend start",
            value=default_start,
            min_value=history_start,
            max_value=history_end,
            key=f"cronometer_trend_start_{run_info.get('range_label', 'latest')}",
        )
    with col_end:
        trend_end = st.date_input(
            "Trend end",
            value=default_end,
            min_value=history_start,
            max_value=history_end,
            key=f"cronometer_trend_end_{run_info.get('range_label', 'latest')}",
        )

    if trend_end < trend_start:
        st.error("Trend end must be on or after trend start.")
        return

    range_df = filter_range_frame(daily_df, "Date", trend_start, trend_end)
    if range_df.empty:
        st.info("No micronutrient rows were found for that range.")
        return

    range_servings_df = filter_range_frame(servings_df, "Day", trend_start, trend_end)
    range_label = f"{trend_start.isoformat()} to {trend_end.isoformat()}"
    st.markdown(f"#### Range: {range_label}")

    summary_cols = st.columns(4)
    summary_cols[0].metric("Days", str(range_df.shape[0]))
    summary_cols[1].metric("Average Energy", format_metric(range_df["Energy (kcal)"].mean(), "kcal"))
    summary_cols[2].metric("Average Protein", format_metric(range_df["Protein (g)"].mean(), "g"))
    summary_cols[3].metric("Average Water", format_metric(range_df["Water (g)"].mean(), "g"))

    category = st.selectbox(
        "Trend category",
        list(NUTRIENT_CATEGORIES.keys()),
        key=f"cronometer_trend_category_{run_info.get('range_label', 'latest')}",
    )

    comparison_df = build_average_comparison_frame(
        range_df=range_df,
        history_df=daily_df,
        nutrient_columns=NUTRIENT_CATEGORIES[category],
    )
    if comparison_df.empty:
        st.info("No values found for that category in the selected range.")
    else:
        chart_df = comparison_df.melt(
            id_vars=["nutrient"],
            value_vars=["range_average", "history_average"],
            var_name="source",
            value_name="value",
        )
        chart_df["source"] = chart_df["source"].replace(
            {
                "range_average": "Selected range",
                "history_average": "Full saved history",
            }
        )

        chart = (
            alt.Chart(chart_df)
            .mark_bar()
            .encode(
                y=alt.Y("nutrient:N", sort="-x", title=None),
                x=alt.X("value:Q", title=None),
                color=alt.Color("source:N", legend=alt.Legend(title=None)),
                tooltip=[
                    alt.Tooltip("nutrient:N", title="Nutrient"),
                    alt.Tooltip("source:N", title="Source"),
                    alt.Tooltip("value:Q", title="Value", format=".2f"),
                ],
            )
            .properties(height=max(260, 24 * len(comparison_df)))
        )
        st.altair_chart(chart, width="stretch")
        st.dataframe(comparison_df, width="stretch", hide_index=True)

    if not range_servings_df.empty and "Food Name" in range_servings_df.columns:
        st.markdown("#### Most frequent foods in this range")
        food_counts = (
            range_servings_df["Food Name"]
            .fillna("")
            .astype(str)
            .value_counts()
            .head(10)
            .reset_index()
        )
        food_counts.columns = ["Food Name", "Count"]
        st.dataframe(food_counts, width="stretch", hide_index=True)


def filter_range_frame(df: pd.DataFrame, date_column: str, start_date: date, end_date: date) -> pd.DataFrame:
    if df.empty or date_column not in df.columns:
        return pd.DataFrame()

    frame = df.copy()
    frame[date_column] = pd.to_datetime(frame[date_column], errors="coerce").dt.date
    mask = (frame[date_column] >= start_date) & (frame[date_column] <= end_date)
    return frame.loc[mask].copy()


def build_export_paths(paths: dict, run_info: dict) -> tuple[Path, Path, Path, Path]:
    servings_path_str = str(run_info.get("servings_path", "")).strip()
    daily_path_str = str(run_info.get("daily_nutrition_path", "")).strip()
    biometrics_path_str = str(run_info.get("biometrics_path", "")).strip()
    notes_path_str = str(run_info.get("notes_path", "")).strip()
    output_dir = paths["cronometer_output_dir"]

    servings_path = Path(servings_path_str) if servings_path_str else output_dir / "servings.csv"
    daily_path = Path(daily_path_str) if daily_path_str else output_dir / "daily_nutrition.csv"
    biometrics_path = Path(biometrics_path_str) if biometrics_path_str else output_dir / "biometrics.csv"
    notes_path = Path(notes_path_str) if notes_path_str else output_dir / "notes.csv"

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


def build_average_comparison_frame(
    range_df: pd.DataFrame,
    history_df: pd.DataFrame,
    nutrient_columns: list[str],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for column in nutrient_columns:
        if column not in range_df.columns or column not in history_df.columns:
            continue

        range_values = pd.to_numeric(range_df[column], errors="coerce").dropna()
        history_values = pd.to_numeric(history_df[column], errors="coerce").dropna()
        if range_values.empty or history_values.empty:
            continue

        range_average = float(range_values.mean())
        history_average = float(history_values.mean())
        delta = range_average - history_average
        delta_pct = (delta / history_average * 100.0) if history_average else None
        unit = column[column.rfind("(") + 1 : column.rfind(")")] if "(" in column and ")" in column else ""
        rows.append(
            {
                "nutrient": column,
                "unit": unit,
                "range_average": range_average,
                "history_average": history_average,
                "delta": delta,
                "delta_pct": delta_pct,
            }
        )

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows)
    result["abs_delta_pct"] = result["delta_pct"].abs().fillna(0.0)
    return result.sort_values("abs_delta_pct", ascending=False).drop(columns=["abs_delta_pct"]).reset_index(drop=True)


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


def parse_iso_date(value: object) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def load_latest_local_run(paths: dict) -> dict | None:
    output_dir = paths["cronometer_output_dir"]
    if not output_dir.exists():
        return None

    servings_path = output_dir / "servings.csv"
    daily_path = output_dir / "daily_nutrition.csv"
    biometrics_path = output_dir / "biometrics.csv"
    notes_path = output_dir / "notes.csv"

    fallback_servings = sorted(output_dir.glob("servings_*.csv"), key=lambda path: path.stat().st_mtime, reverse=True)
    fallback_biometrics = sorted(output_dir.glob("biometrics_*.csv"), key=lambda path: path.stat().st_mtime, reverse=True)
    fallback_notes = sorted(output_dir.glob("notes_*.csv"), key=lambda path: path.stat().st_mtime, reverse=True)

    if not servings_path.exists() and fallback_servings:
        servings_path = fallback_servings[0]
    if not biometrics_path.exists() and fallback_biometrics:
        biometrics_path = fallback_biometrics[0]
    if not notes_path.exists() and fallback_notes:
        notes_path = fallback_notes[0]

    if not servings_path.exists() and not daily_path.exists() and not biometrics_path.exists() and not notes_path.exists():
        return None

    servings_df = read_csv_dataframe(servings_path) if servings_path.exists() else pd.DataFrame()
    daily_df = read_csv_dataframe(daily_path) if daily_path.exists() else pd.DataFrame()

    available_dates = collect_available_dates(servings_df, daily_df)
    end_date = available_dates[0] if available_dates else ""

    return {
        "source": "local_cache",
        "range_label": "local_cache",
        "servings_path": str(servings_path) if servings_path.exists() else "",
        "daily_nutrition_path": str(daily_path) if daily_path.exists() else "",
        "biometrics_path": str(biometrics_path) if biometrics_path.exists() else "",
        "notes_path": str(notes_path) if notes_path.exists() else "",
        "start_date": "",
        "end_date": end_date,
        "fetch_servings": True,
        "fetch_daily_nutrition": daily_path.exists(),
        "fetch_biometrics": biometrics_path.exists(),
        "fetch_notes": notes_path.exists(),
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
