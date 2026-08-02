import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path
from services.storage import read_csv_dataframe

def render_sleep_chart(garmin_csv: Path) -> None:
    st.header("Garmin Sleep")
    st.caption("Sleep trend from local Garmin summary data.")

    df = read_csv_dataframe(garmin_csv)
    if df.empty:
        st.info(f"No Garmin summary found at {garmin_csv}")
        return

    metric_columns = {
        "Deep Sleep, h": "deep_sleep_hours",
        "REM, h": "rem_sleep_hours",
        "Total Sleep, h": "total_sleep_hours",
        "Score (max 100)": "sleep_score",
        "Weight, kg": "weight",
        "Calories Burned": "calories_burned",
        "Calories Consumed": "calories_consumed",
    }

    plot_df = df[["date", *[col for col in metric_columns.values() if col in df.columns]]].copy()
    plot_df["date"] = pd.to_datetime(plot_df["date"], errors="coerce")
    plot_df = plot_df.dropna(subset=["date"]).sort_values("date")
    # Only iterate over keys that are actually present in the DataFrame columns
    valid_columns = [col for col in metric_columns.values() if col in plot_df.columns]
    
    for column in valid_columns:
        plot_df[column] = pd.to_numeric(plot_df[column], errors="coerce")

    melted = plot_df.melt(
        id_vars=["date"],
        value_vars=valid_columns,
        var_name="metric_key",
        value_name="value",
    ).dropna(subset=["value"])

    label_map = pd.DataFrame(
        {
            "metric_key": list(metric_columns.values()),
            "metric": list(metric_columns.keys()),
        }
    )
    melted = melted.merge(label_map, on="metric_key", how="left")

    chart = (
        alt.Chart(melted)
        .mark_line(point=True, strokeWidth=3)
        .encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("value:Q", title=None),
            color=alt.Color(
                "metric:N",
                legend=None,
                scale=alt.Scale(
                    domain=list(metric_columns.keys()),
                    range=["#2a9d8f", "#e76f51", "#f4a261", "#264653", "#8f2d56", "#6c5ce7"],
                ),
            ),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("metric:N", title="Metric"),
                alt.Tooltip("value:Q", title="Value", format=".2f"),
            ],
        )
        .properties(height=140)
        .facet(row=alt.Row("metric:N", header=alt.Header(labelFontSize=14, title=None)))
        .resolve_scale(y="independent")
    )

    st.altair_chart(chart, width="stretch")
