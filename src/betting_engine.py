import numpy as np
import pandas as pd


def generate_gameweek_betting_insights(
    selected_gw_str: str,
    df_summary: pd.DataFrame,
    master_fixtures_df: pd.DataFrame,
    played_results_df: pd.DataFrame,
) -> list[dict]:
    """Generate betting value insights for every fixture in a gameweek."""
    try:
        gw_num = int(selected_gw_str.replace("Gameweek ", "").strip())
    except ValueError:
        gw_num = 1

    gw_fixtures = master_fixtures_df[master_fixtures_df["Gameweek"] == gw_num]
    if gw_fixtures.empty:
        return []

    sim_lookup = df_summary.set_index("Team").to_dict(orient="index")
    played_set = set(
        played_results_df["HomeTeam"] + " vs " + played_results_df["AwayTeam"]
    )
    betting_insights = []

    for _, row in gw_fixtures.iterrows():
        home, away = row["HomeTeam"], row["AwayTeam"]
        match_token = f"{home} vs {away}"
        home_metrics = sim_lookup.get(home, {"Title_Pct": 5.0, "Relegation_Pct": 10.0})
        away_metrics = sim_lookup.get(away, {"Title_Pct": 5.0, "Relegation_Pct": 10.0})

        total_weight = home_metrics["Title_Pct"] + (100 - away_metrics["Relegation_Pct"]) + 10
        home_win_prob = max(10.0, min(80.0, (total_weight / 200) * 80))
        away_win_prob = max(10.0, min(80.0, ((200 - total_weight) / 200) * 80))
        draw_prob = 100.0 - home_win_prob - away_win_prob

        fair_home_odds = 1 / (home_win_prob / 100.0)
        bookie_home_odds = round(fair_home_odds * np.random.uniform(0.92, 1.18), 2)
        bookie_draw_odds = round((1 / (draw_prob / 100.0)) * np.random.uniform(0.95, 1.10), 2)
        bookie_away_odds = round((1 / (away_win_prob / 100.0)) * np.random.uniform(0.95, 1.10), 2)

        edge_detected = bookie_home_odds > fair_home_odds
        edge_pct = ((bookie_home_odds - fair_home_odds) / fair_home_odds) * 100 if edge_detected else 0.0

        betting_insights.append(
            {
                "home": home,
                "away": away,
                "played": match_token in played_set,
                "sim_home_win": round(home_win_prob, 1),
                "sim_draw": round(draw_prob, 1),
                "sim_away_win": round(away_win_prob, 1),
                "fair_home_odds": round(fair_home_odds, 2),
                "bookie_home_odds": bookie_home_odds,
                "bookie_draw_odds": bookie_draw_odds,
                "bookie_away_odds": bookie_away_odds,
                "edge_detected": edge_detected,
                "edge_pct": round(edge_pct, 1),
            }
        )

    return betting_insights