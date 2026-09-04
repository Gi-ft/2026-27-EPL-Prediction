import json
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from scripts.generate_visuals import build_heatmap

# ==========================================
# 1. PAGE CONFIGURATION & DARK THEME HOOK
# ==========================================
st.set_page_config(
    page_title="EPL 25/26 Simulation Hub",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Injected style sheet overrides to enforce full-width dark geometry
st.markdown(
    """
    <style>
        .stApp { background-color: #0d1117; color: #c9d1d9; }
        
        /* Dashboard Card Styling */
        div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"] {
            background-color: #161b22 !important;
            border: 1px solid #30363d !important;
            border-radius: 8px !important;
            padding: 20px !important;
        }
        
        /* KPI Metric Container Formatting */
        div[data-testid="stMetric"] {
            background-color: #21262d;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 12px 15px;
        }

        div[data-testid="stMetricLabel"] {
            font-weight: 700 !important;
        }

        div[data-testid="stMetricValue"] {
            font-weight: 800 !important;
        }

        div[data-testid="stMetricDelta"] {
            font-weight: 600 !important;
        }
        
        button[data-baseweb="tab"] { color: #8b949e !important; }
        button[aria-selected="true"] { color: #58a6ff !important; border-color: #58a6ff !important; }
    </style>
""",
    unsafe_allow_html=True,
)

ROOT = Path(__file__).resolve().parent
SUMMARY_PATH = ROOT / "data" / "season_summary.json"
HEATMAP_PATH = ROOT / "output_plots" / "epl_probability_heatmap.png"


def render_dashboard_table(df: pd.DataFrame, column_config: dict) -> None:
    """Render a native table, with an HTML fallback when PyArrow is blocked."""
    try:
        st.dataframe(
            df,
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            height=800,
        )
    except (ImportError, OSError) as error:
        error_text = str(error).lower()
        if "pyarrow" not in error_text and "dll" not in error_text:
            raise

        st.caption("Native Streamlit tables are unavailable because Windows blocked PyArrow; showing a compatible table.")
        bar_colors = {
            "Title_Pct": "#58a6ff",
            "Relegation_Pct": "#ff7b72",
            "Risk %": "#ff4d4d",
        }
        header_labels = {
            "Team": "Club Name",
            "xPts": "xPts",
            "Title_Pct": "Title Probability",
            "Relegation_Pct": "Relegation Risk",
            "Risk %": "Risk %",
        }
        headers = "".join(
            f"<th>{escape(header_labels.get(column, str(column)))}</th>"
            for column in df.columns
        )
        rows = []
        for _, row in df.iterrows():
            cells = []
            for column, value in row.items():
                if column in bar_colors:
                    percentage = max(0.0, min(100.0, float(value)))
                    cells.append(
                        "<td><div class='metric-cell'>"
                        f"<span>{percentage:.1f}%</span>"
                        f"<span class='metric-bar'><span style='width:{percentage:.1f}%;background:{bar_colors[column]};'></span></span>"
                        "</div></td>"
                    )
                elif column == "xPts":
                    cells.append(f"<td>{float(value):.2f}</td>")
                else:
                    cells.append(f"<td>{escape(str(value))}</td>")
            rows.append(f"<tr>{''.join(cells)}</tr>")

        table_html = (
            "<style>"
            ".dashboard-table-wrap{width:100%;max-width:100%;max-height:800px;overflow:auto;}"
            ".dashboard-table{width:100%;min-width:560px;border-collapse:collapse;color:#c9d1d9;}"
            ".dashboard-table th,.dashboard-table td{padding:8px 10px;text-align:left;border-bottom:1px solid #30363d;}"
            ".dashboard-table th{color:#8b949e;font-weight:600;}"
            ".metric-cell{display:flex;align-items:center;gap:8px;min-width:110px;}"
            ".metric-bar{display:inline-block;width:64px;height:6px;background:#30363d;border-radius:4px;overflow:hidden;}"
            ".metric-bar span{display:block;height:100%;border-radius:4px;}"
            "</style>"
            f"<div class='dashboard-table-wrap'><table class='dashboard-table'><thead><tr>{headers}</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>"
        )
        st.markdown(table_html, unsafe_allow_html=True)


def load_dashboard_data(path: Path) -> pd.DataFrame:
    """Load dashboard data from either the legacy summary or the Opta-style summary."""
    payload = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(payload, list):
        df = pd.DataFrame(payload)
        rename_map = {"TITLE": "Title_Pct", "UCL": "Top4_Pct", "REL": "Relegation_Pct"}
        df = df.rename(columns=rename_map)
        if "Team" not in df.columns and "team" in df.columns:
            df = df.rename(columns={"team": "Team"})
        if "GA" not in df.columns and "TO" in df.columns:
            df = df.rename(columns={"TO": "GA"})
        for column in ["Title_Pct", "Top4_Pct", "Relegation_Pct"]:
            if column in df.columns:
                df[column] = df[column].astype(float)
        if "Points" not in df.columns:
            df["Points"] = df["xPts"]
        if "GD" not in df.columns:
            df["GD"] = 0
        if "GF" not in df.columns:
            df["GF"] = 0
        if "GA" not in df.columns:
            df["GA"] = 0
        if "points_distribution" not in df.columns:
            df["points_distribution"] = [[] for _ in range(len(df))]
        return df.sort_values(by="xPts", ascending=False).reset_index(drop=True)

    table_df = pd.DataFrame(payload["single_season"]["table"])
    monte_carlo_df = pd.DataFrame(payload["monte_carlo"]["teams"])

    table_df = table_df.rename(
        columns={
            "team": "Team",
            "points": "Points",
            "goal_difference": "GD",
            "goals_for": "GF",
            "goals_against": "GA",
            "TO": "GA",
        }
    )
    monte_carlo_df = monte_carlo_df.rename(
        columns={
            "team": "Team",
            "title_probability": "Title_Pct",
            "top_four_probability": "Top4_Pct",
            "relegation_probability": "Relegation_Pct",
        }
    )

    df = table_df.merge(
        monte_carlo_df[["Team", "Title_Pct", "Top4_Pct", "Relegation_Pct", "points_distribution"]],
        on="Team",
        how="inner",
    )
    for column in ["Title_Pct", "Top4_Pct", "Relegation_Pct"]:
        df[column] *= 100
    df["xPts"] = df["Points"].astype(float)
    return df.sort_values(by="Points", ascending=False).reset_index(drop=True)


summary_source = SUMMARY_PATH
if not summary_source.exists():
    st.error(f"Monte Carlo summary not found: {SUMMARY_PATH}")
    st.stop()

summary_source_label = summary_source.relative_to(ROOT).as_posix()
df_summary = load_dashboard_data(summary_source)
HEATMAP_PATH.parent.mkdir(parents=True, exist_ok=True)
heatmap_df = df_summary.copy()
for column in ["Title_Pct", "Top4_Pct", "Relegation_Pct"]:
    heatmap_df[column] /= 100
build_heatmap(
    heatmap_df.rename(
        columns={
            "Title_Pct": "Title %",
            "Top4_Pct": "Top 4 %",
            "Relegation_Pct": "Relegation %",
            "Points": "CurrentPoints",
        }
    )
)

# ==========================================
# 3. LAYOUT SIDEBAR CONTROLS
# ==========================================
st.sidebar.header("Dashboard Filters")
focus_team = st.sidebar.selectbox("Focus Team Search", ["All Teams"] + list(df_summary["Team"]))
comparisons = st.sidebar.multiselect(
    "Points Variance Comparison",
    list(df_summary["Team"]),
    default=["Arsenal", "Manchester City", "Manchester United", "Newcastle United"]
)

# ==========================================
# 4. EXECUTIVE BANNER METRIC ROW (TITLE PROBABILITY ORDER)
# ==========================================
# Keep the standings xPts order separate from the title-probability podium.
df_podium = df_summary.sort_values(
    by=["Title_Pct", "xPts"], ascending=False
).reset_index(drop=True)
t1_name, t1_pts, t1_chance = str(df_podium.loc[0, "Team"]), float(df_podium.loc[0, "xPts"]), float(df_podium.loc[0, "Title_Pct"])
t2_name, t2_pts, t2_chance = str(df_podium.loc[1, "Team"]), float(df_podium.loc[1, "xPts"]), float(df_podium.loc[1, "Title_Pct"])
t3_name, t3_pts, t3_chance = str(df_podium.loc[2, "Team"]), float(df_podium.loc[2, "xPts"]), float(df_podium.loc[2, "Title_Pct"])

with st.container():
    st.markdown("<h2 style='margin:0; color:#f0f6fc;'>Season Outlook & Variance Insights</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#8b949e; margin-bottom:15px;'>Live source: <code style='color:#ff7b72;'>{summary_source_label}</code></p>", unsafe_allow_html=True)

    # Keep the favorite centered, with the challenger on the left.
    m2, m1, m3 = st.columns(3)
    m1.metric(label=f"Title Favorite: {t1_name}", value=f"{t1_pts:.2f} xPts", delta=f"Chance: {t1_chance:.2f}%")
    m2.metric(label=f"Challenger: {t2_name}", value=f"{t2_pts:.2f} xPts", delta=f"Chance: {t2_chance:.2f}%")
    m3.metric(label=f"Longshot: {t3_name}", value=f"{t3_pts:.2f} xPts", delta=f"Chance: {t3_chance:.2f}%")

# ==========================================
# 5. TAB CONTROL ARCHITECTURE
# ==========================================
tab1, tab2 = st.tabs(["League Standings & Watchlists", "Probability & Variance Analytics"])

with tab1:
    st.markdown("<h3 style='color:#f0f6fc; margin-bottom:15px;'>Expected League Standings</h3>", unsafe_allow_html=True)
    
    # Opta-style order: expected points determine the displayed position.
    df_display = df_summary.sort_values(
        by=["xPts", "Title_Pct"], ascending=False
    ).reset_index(drop=True)
    df_display["Rank"] = df_display["XPOS"] if "XPOS" in df_display else df_display.index + 1

    if focus_team != "All Teams":
        df_display = df_display[df_display["Team"] == focus_team]

    # Reorder columns to put Rank first
    df_display = df_display[["Rank", "Team", "xPts", "GF", "GA", "GD", "Title_Pct", "Relegation_Pct"]]

    render_dashboard_table(
        df_display,
        column_config={
            "Rank": st.column_config.NumberColumn("Rank", width="small"),
            "Team": st.column_config.TextColumn("Club Name", width="medium"),
            "xPts": st.column_config.NumberColumn("xPts", format="%.2f", width="small"),
            "GD": st.column_config.NumberColumn("GD", width="small"),
            "GF": st.column_config.NumberColumn("GF", width="small"),
            "GA": st.column_config.NumberColumn("GA", width="small"),
            "Title_Pct": st.column_config.ProgressColumn(
                "Title Probability", format="%.1f%%", min_value=0, max_value=100, color="#58a6ff"
            ),
            "Relegation_Pct": st.column_config.ProgressColumn(
                "Relegation Risk", format="%.1f%%", min_value=0, max_value=100, color="#ff7b72"
            )
        }
    )

with tab2:
    st.markdown("<h3 style='color:#f0f6fc; margin-bottom:15px;'>Monte Carlo Heat Map</h3>", unsafe_allow_html=True)

    if HEATMAP_PATH.exists():
        st.image(str(HEATMAP_PATH), use_container_width=True)
        st.caption("Probability matrix generated from the Monte Carlo season summary.")
    else:
        st.warning("Heat map image not found in `output_plots/`. Showing an in-app fallback chart instead.")
        heatmap_df = df_summary.set_index("Team")[["Title_Pct", "Top4_Pct", "Relegation_Pct"]]
        heatmap_df.columns = ["Title %", "Top 4 %", "Relegation %"]

        fig_heat = go.Figure(
            data=go.Heatmap(
                z=heatmap_df.to_numpy(),
                x=list(heatmap_df.columns),
                y=list(heatmap_df.index),
                colorscale="YlOrRd",
                zmin=0,
                zmax=100,
                hovertemplate="%{y}<br>%{x}: %{z:.1f}%<extra></extra>",
            )
        )
        fig_heat.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0d1117",
            plot_bgcolor="#161b22",
            height=700,
            margin=dict(l=150, r=20, t=20, b=20),
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    st.markdown("<h3 style='color:#f0f6fc; margin-bottom:15px; margin-top:22px;'>Analytical Deep-Dives</h3>", unsafe_allow_html=True)
    g1, g2 = st.columns(2)

    with g1:
        st.markdown("<h4 style='color:#c9d1d9; text-align:center;'>Probability Distributions</h4>", unsafe_allow_html=True)
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(name="Title %", x=df_summary["Team"], y=df_summary["Title_Pct"], marker_color="#58a6ff"))
        fig_bar.add_trace(go.Bar(name="Relegation %", x=df_summary["Team"], y=df_summary["Relegation_Pct"], marker_color="#ff7b72"))
        fig_bar.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=380, margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with g2:
        st.markdown("<h4 style='color:#c9d1d9; text-align:center;'>Points Variance Projection</h4>", unsafe_allow_html=True)
        fig_box = go.Figure()
        
        for team in comparisons:
            distribution = df_summary.loc[df_summary["Team"] == team, "points_distribution"]
            if not distribution.empty:
                fig_box.add_trace(
                    go.Box(
                        x=distribution.iloc[0],
                        name=str(team),
                        boxpoints="all",
                        jitter=0.3,
                    )
                )

        fig_box.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=380, margin=dict(l=10, r=10, t=10, b=10)
        )
        st.plotly_chart(fig_box, use_container_width=True)
