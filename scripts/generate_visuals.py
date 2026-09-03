from __future__ import annotations

import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import plotly.io as pio
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns


ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = ROOT / "data" / "season_summary.json"
OUTPUT_DIR = ROOT / "output_plots"

FIG_BG = "#0f172a"
PLOT_BG = "#111827"
TEXT = "#e5e7eb"
MUTED = "#94a3b8"
ACCENT = "#38bdf8"
GRID = "#334155"
HEATMAP_CMAP = "YlOrRd"

pio.templates["epl_dashboard"] = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor=FIG_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color=TEXT, family="Arial"),
        xaxis=dict(gridcolor=GRID, zeroline=False, linecolor=GRID),
        yaxis=dict(gridcolor=GRID, zeroline=False, linecolor=GRID),
    )
)


def load_summary(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Summary file not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(payload, list):
        df = pd.DataFrame(payload).rename(
            columns={
                "TITLE": "Title %",
                "UCL": "Top 4 %",
                "REL": "Relegation %",
            }
        )
        df["CurrentPoints"] = df["xPts"].astype(float)
        for column in ["Title %", "Top 4 %", "Relegation %"]:
            df[column] = df[column].astype(float) / 100
        return df.sort_values(by="CurrentPoints", ascending=False).reset_index(drop=True)

    teams = payload["monte_carlo"]["teams"]
    table = payload["single_season"]["table"]

    table_df = pd.DataFrame(table)[["team", "points"]].rename(columns={"team": "Team", "points": "CurrentPoints"})
    probs_df = pd.DataFrame(teams)[
        [
            "team",
            "title_probability",
            "top_four_probability",
            "relegation_probability",
            "points_distribution",
        ]
    ].rename(
        columns={
            "team": "Team",
            "title_probability": "Title %",
            "top_four_probability": "Top 4 %",
            "relegation_probability": "Relegation %",
        }
    )

    df = table_df.merge(probs_df, on="Team", how="inner")
    return df.sort_values(by="CurrentPoints", ascending=False).reset_index(drop=True)


def build_heatmap(df: pd.DataFrame) -> None:
    sns.set_theme(style="dark")
    plt.figure(figsize=(10.5, 12), facecolor=FIG_BG)
    heatmap_data = df.set_index("Team")[["Title %", "Top 4 %", "Relegation %"]] * 100

    ax = sns.heatmap(
        heatmap_data,
        annot=True,
        fmt=".2f",
        cmap=HEATMAP_CMAP,
        vmin=0,
        vmax=100,
        linewidths=0.5,
        linecolor="#334155",
        cbar_kws={"label": "Probability (%)", "shrink": 0.85},
        annot_kws={"size": 10, "weight": "bold", "color": "#0f172a"},
    )

    ax.set_facecolor(PLOT_BG)
    plt.title(
        "EPL Monte Carlo Outcome Probability Matrix",
        fontsize=14,
        pad=18,
        weight="bold",
        color=TEXT,
    )
    plt.ylabel("Clubs", color=TEXT, labelpad=12)
    plt.xlabel("Simulated Season Outcomes", color=TEXT, labelpad=10)
    plt.xticks(color=TEXT)
    plt.yticks(color=TEXT)
    colorbar = ax.collections[0].colorbar
    colorbar.ax.tick_params(colors=TEXT)
    colorbar.set_label("Probability (%)", color=TEXT)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "epl_probability_heatmap.png", dpi=300, facecolor=FIG_BG, edgecolor=FIG_BG)
    plt.close()


def build_points_chart(df: pd.DataFrame) -> None:
    fig = go.Figure()
    for _, row in df.iterrows():
        fig.add_trace(
            go.Box(
                x=row["points_distribution"],
                name=row["Team"],
                boxpoints=False,
                orientation="h",
                fillcolor="rgba(37, 99, 235, 0.25)",
                line=dict(color="#2563eb", width=1.6),
                marker=dict(color="#2563eb"),
            )
        )

    fig.update_layout(
        title=dict(
            text="<b>Final Points Variance Profile</b><br><sup>Monte Carlo season outcomes</sup>",
            x=0.5,
            xanchor="center",
            font=dict(size=22, color=TEXT),
        ),
        xaxis_title="Points",
        yaxis_title="Team",
        template="epl_dashboard",
        height=940,
        margin=dict(l=150, r=40, t=90, b=55),
        showlegend=False,
        xaxis=dict(
            title=dict(font=dict(color=TEXT, size=14)),
            tickfont=dict(color=TEXT),
            gridcolor=GRID,
            zeroline=False,
            showline=True,
            linecolor=GRID,
            tickmode="linear",
        ),
        yaxis=dict(
            title=dict(font=dict(color=TEXT, size=14)),
            tickfont=dict(color=TEXT),
            gridcolor=GRID,
            zeroline=False,
            showline=True,
            linecolor=GRID,
            autorange="reversed",
        ),
    )
    fig.write_html(OUTPUT_DIR / "points_snapshot.html")
    return fig


def build_dashboard_page(df: pd.DataFrame, points_fig: go.Figure) -> None:
    leaders = df.head(3)
    relegated = df.tail(3)

    kpi_cards = []
    for _, row in leaders.iterrows():
        kpi_cards.append(
            f"""
            <div class="kpi-card">
              <div class="kpi-label">{row['Team']}</div>
              <div class="kpi-value">{int(row['CurrentPoints'])} pts</div>
              <div class="kpi-meta">Title {row['Title %'] * 100:.1f}% | Top 4 {row['Top 4 %'] * 100:.1f}%</div>
            </div>
            """
        )

    relegation_list = "".join(
        f"<li><span>{row['Team']}</span><strong>{row['Relegation %'] * 100:.1f}%</strong></li>"
        for _, row in relegated.iterrows()
    )

    heatmap_html = (OUTPUT_DIR / "epl_probability_heatmap.png").as_posix()
    points_div = points_fig.to_html(full_html=False, include_plotlyjs="cdn", config={"displayModeBar": False})

    dashboard = f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>EPL Dashboard</title>
        <style>
          body {{
            margin: 0;
            background: {FIG_BG};
            color: {TEXT};
            font-family: Arial, sans-serif;
          }}
          .wrap {{
            max-width: 1500px;
            margin: 0 auto;
            padding: 24px;
          }}
          .hero {{
            background: linear-gradient(135deg, #111827 0%, #0f172a 100%);
            border: 1px solid {GRID};
            border-radius: 18px;
            padding: 24px;
            box-shadow: 0 18px 40px rgba(0,0,0,0.35);
          }}
          .eyebrow {{
            color: {ACCENT};
            text-transform: uppercase;
            letter-spacing: .18em;
            font-size: 12px;
            font-weight: 700;
          }}
          h1 {{
            margin: 10px 0 8px;
            font-size: 34px;
          }}
          .sub {{
            color: {MUTED};
            max-width: 900px;
            line-height: 1.5;
          }}
          .kpis {{
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px;
            margin-top: 18px;
          }}
          .kpi-card {{
            background: rgba(17,24,39,.82);
            border: 1px solid {GRID};
            border-radius: 16px;
            padding: 16px;
          }}
          .kpi-label {{
            font-size: 13px;
            color: {MUTED};
            margin-bottom: 8px;
          }}
          .kpi-value {{
            font-size: 28px;
            font-weight: 800;
            margin-bottom: 4px;
          }}
          .kpi-meta {{
            font-size: 13px;
            color: {TEXT};
          }}
          .grid {{
            display: grid;
            grid-template-columns: 1.3fr .7fr;
            gap: 18px;
            margin-top: 18px;
          }}
          .panel {{
            background: rgba(17,24,39,.82);
            border: 1px solid {GRID};
            border-radius: 18px;
            padding: 18px;
            box-shadow: 0 18px 40px rgba(0,0,0,0.24);
          }}
          .panel h2 {{
            margin: 0 0 14px;
            font-size: 18px;
          }}
          .heatmap-img {{
            width: 100%;
            border-radius: 12px;
            display: block;
          }}
          .zone-list {{
            list-style: none;
            padding: 0;
            margin: 0;
          }}
          .zone-list li {{
            display: flex;
            justify-content: space-between;
            padding: 14px 0;
            border-bottom: 1px solid {GRID};
          }}
          .zone-list li:last-child {{
            border-bottom: none;
          }}
          .section {{
            margin-top: 18px;
          }}
          .legend {{
            color: {MUTED};
            font-size: 13px;
          }}
          @media (max-width: 1100px) {{
            .grid, .kpis {{
              grid-template-columns: 1fr;
            }}
          }}
        </style>
      </head>
      <body>
        <div class="wrap">
          <div class="hero">
            <div class="eyebrow">EPL Monte Carlo Dashboard</div>
            <h1>Season outlook and variance view</h1>
            <div class="sub">
              Live simulation snapshot from the current season summary. The top cards show the leading clubs, the heatmap highlights title, top-four, and relegation probabilities, and the variance chart shows the distribution of simulated points totals.
            </div>
            <div class="kpis">
              {''.join(kpi_cards)}
            </div>
          </div>

          <div class="grid">
            <div class="panel">
              <h2>Probability Heatmap</h2>
              <img class="heatmap-img" src="{heatmap_html}" alt="Probability heatmap" />
              <div class="legend">Top 4 threshold and relegation watch areas are highlighted in the chart styling.</div>
            </div>
            <div class="panel">
              <h2>Relegation Watch</h2>
              <ul class="zone-list">
                {relegation_list}
              </ul>
            </div>
          </div>

          <div class="section panel">
            <h2>Points Variance</h2>
            {points_div}
          </div>
        </div>
      </body>
    </html>
    """

    (OUTPUT_DIR / "dashboard.html").write_text(dashboard, encoding="utf-8")


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = load_summary(SUMMARY_PATH)
    build_heatmap(df)
    points_fig = build_points_chart(df)
    build_dashboard_page(df, points_fig)

    print("Static visualization generation complete!")
    print(f" -> Check '{OUTPUT_DIR / 'epl_probability_heatmap.png'}'")
    print(f" -> Check '{OUTPUT_DIR / 'points_snapshot.html'}'")
    print(f" -> Check '{OUTPUT_DIR / 'dashboard.html'}'")


if __name__ == "__main__":
    main()
