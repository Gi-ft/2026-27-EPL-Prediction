"""Pre-season standings used as the simulation's historical prior."""

from __future__ import annotations

import pandas as pd


def initialize_pre_season_standings() -> pd.DataFrame:
    """Return the 2025/26 final-table points used as the 2026/27 prior."""
    pre_season_priors = {
        "Arsenal": 85.0,
        "Manchester City": 78.0,
        "Manchester United": 71.0,
        "Aston Villa": 65.0,
        "Liverpool": 60.0,
        "Bournemouth": 57.0,
        "Sunderland": 54.0,
        "Brighton": 53.0,
        "Brentford": 53.0,
        "Chelsea": 52.0,
        "Fulham": 52.0,
        "Newcastle United": 49.0,
        "Everton": 49.0,
        "Leeds United": 47.0,
        "Crystal Palace": 45.0,
        "Nottingham Forest": 44.0,
        "Tottenham Hotspur": 41.0,
        "Coventry City": 35.5,
        "Ipswich Town": 34.0,
        "Hull City": 32.0,
    }

    df_init = pd.DataFrame(
        [
            {
                "Team": team,
                "xPts": seeded_xpts,
                "GD": 0,
                "GF": 0,
                "GA": 0,
                "Title_Pct": 0.0,
                "Relegation_Pct": 0.0,
            }
            for team, seeded_xpts in pre_season_priors.items()
        ]
    )
    return df_init.sort_values(by="xPts", ascending=False).reset_index(drop=True)
