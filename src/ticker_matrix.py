import html

import numpy as np
import pandas as pd


def generate_html_full_38_ticker(
    df_current_standings: pd.DataFrame,
    master_fixtures_df: pd.DataFrame,
    played_results_df: pd.DataFrame,
) -> str:
    """Generate a horizontally scrollable FPL-style 38-gameweek ticker."""
    df_sorted = df_current_standings.sort_values(
        by="xPts", ascending=False
    ).reset_index(drop=True)
    num_teams = len(df_sorted)

    if num_teams == 0:
        return "<div style='color:#8b949e;'>No teams available.</div>"

    denominator = max(num_teams - 1, 1)
    team_difficulty = {}
    for index, row in df_sorted.iterrows():
        rank_tier = 5.0 - ((index / denominator) * 4.0)
        team_difficulty[row["Team"]] = int(np.clip(round(rank_tier), 1, 5))

    fdr_colors = {
        1: "#01573d",
        2: "#2e7d32",
        3: "#fbc02d",
        4: "#e53935", 
        5: "#800000",  
    }
    font_colors = {1: "#fff", 2: "#fff", 3: "#000", 4: "#fff", 5: "#fff"}

    played_set = set(
        played_results_df["HomeTeam"].astype(str).str.strip()
        + " vs "
        + played_results_df["AwayTeam"].astype(str).str.strip()
    )
    team_matrix = {team: [None] * 38 for team in df_sorted["Team"]}

    for _, row in master_fixtures_df.iterrows():
        gw = int(row["Gameweek"]) - 1
        if not 0 <= gw < 38:
            continue

        home, away = str(row["HomeTeam"]), str(row["AwayTeam"])
        is_played = f"{home} vs {away}" in played_set
        if home in team_matrix:
            team_matrix[home][gw] = {
                "opp": away,
                "venue": "h",
                "played": is_played,
                "rating": team_difficulty.get(away, 3),
            }
        if away in team_matrix:
            team_matrix[away][gw] = {
                "opp": home,
                "venue": "a",
                "played": is_played,
                "rating": team_difficulty.get(home, 3),
            }

    html_output = """
<div style="position:relative; isolation:isolate; overflow-x:auto; white-space:nowrap; width:100%; border:1px solid #30363d; border-radius:8px; padding:10px; background-color:#0d1117;">
<table style="border-collapse:separate; border-spacing:4px; font-family:Arial,sans-serif; min-width:2500px; position:relative;">
<tr style="color:#8b949e; text-align:center; background-color:#161b22;">
<th style="text-align:left; padding:12px 12px 12px 16px; position:sticky; left:-4px; background-color:#161b22; z-index:20; min-width:160px; border-radius:4px; box-shadow:4px 0 6px rgba(0,0,0,.45);">CLUB NAME</th>
"""
    for gw_num in range(1, 39):
        html_output += (
            f"<th style='padding:10px; min-width:55px; font-size:12px;'>GW{gw_num}</th>"
        )
    html_output += "</tr>"

    for team in df_sorted["Team"]:
        html_output += (
            "<tr>"
            "<td style='padding:12px 12px 12px 16px; font-weight:bold; background-color:#161b22; "
            "position:sticky; left:-4px; z-index:10; color:#f0f6fc; border-radius:4px; "
            "box-shadow:4px 0 6px rgba(0,0,0,.45);'>"
            f"{html.escape(str(team))}</td>"
        )
        for game in team_matrix[team]:
            if game is None:
                html_output += (
                    "<td style='background-color:#21262d; color:#8b949e; "
                    "text-align:center; border-radius:4px;'>-</td>"
                )
            elif game["played"]:
                opp_short = html.escape(game["opp"][:3].upper())
                html_output += (
                    "<td style='background-color:#21262d; color:#8b949e; "
                    f"text-align:center; font-size:11px; border-radius:4px; opacity:.5;'>"
                    f"{opp_short}<br><span style='color:#58a6ff; font-weight:bold;'>&#10003;</span></td>"
                )
            else:
                opp_short = html.escape(game["opp"][:3].upper())
                rating = game["rating"]
                html_output += (
                    f"<td style='background-color:{fdr_colors[rating]}; color:{font_colors[rating]}; "
                    "text-align:center; font-weight:bold; padding:8px; border-radius:4px; font-size:12px;'>"
                    f"{opp_short}<br><span style='font-size:9px; font-weight:normal; opacity:.8;'>({game['venue']})</span></td>"
                )
        html_output += "</tr>"

    legend = """
</table></div>
<div style="display:flex; flex-wrap:wrap; gap:10px 18px; align-items:center; padding:12px 2px 2px; color:#c9d1d9; font:12px Arial,sans-serif;">
<strong style="color:#f0f6fc;">FDR key</strong>
<span><b style="display:inline-block; width:12px; height:12px; margin-right:5px; vertical-align:-2px; background:#01573d; border-radius:2px;"></b>1 Very Easy</span>
<span><b style="display:inline-block; width:12px; height:12px; margin-right:5px; vertical-align:-2px; background:#2e7d32; border-radius:2px;"></b>2 Favorable</span>
<span><b style="display:inline-block; width:12px; height:12px; margin-right:5px; vertical-align:-2px; background:#fbc02d; border-radius:2px;"></b>3 Moderate / Neutral</span>
<span><b style="display:inline-block; width:12px; height:12px; margin-right:5px; vertical-align:-2px; background:#d32f2f; border-radius:2px;"></b>4 Difficult</span>
<span><b style="display:inline-block; width:12px; height:12px; margin-right:5px; vertical-align:-2px; background:#b71c1c; border-radius:2px;"></b>5 Brutal / Elite</span>
</div>
"""
    return html_output + legend
