"""Fixture Difficulty Index calculations for the simulation and dashboard."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEASON_FILES = {
    "final_archive_2526": {
        "fixtures": "data/final_archive_2526/epl_2526_fixtures.csv",
        "priors": "data/final_archive_2526/pre_season_priors.csv",
    },
    "active_season_2627": {
        "fixtures": "data/active_season_2627/epl_2627_fixtures.csv",
        "priors": "data/active_season_2627/pre_season_priors.csv",
    },
}


def load_season_inputs(
    season_mode: str = "active_season_2627",
) -> tuple[pd.DataFrame, list[tuple[str, str]]]:
    """Load season priors and fixture pairs for the selected campaign."""
    if season_mode not in SEASON_FILES:
        valid_modes = ", ".join(sorted(SEASON_FILES))
        raise ValueError(f"Unknown season_mode '{season_mode}'. Choose from: {valid_modes}")

    paths = SEASON_FILES[season_mode]
    priors_path = PROJECT_ROOT / paths["priors"]
    fixtures_path = PROJECT_ROOT / paths["fixtures"]

    if not priors_path.exists():
        raise FileNotFoundError(f"Season priors file not found: {priors_path}")
    if not fixtures_path.exists():
        raise FileNotFoundError(f"Season fixtures file not found: {fixtures_path}")

    standings = pd.read_csv(priors_path)
    if not {"Team", "Actual_Points"}.issubset(standings.columns):
        raise ValueError("Season priors must contain Team and Actual_Points columns")
    standings = standings.rename(columns={"Actual_Points": "xPts"})

    fixtures = pd.read_csv(fixtures_path)
    required = {"HomeTeam", "AwayTeam"}
    if not required.issubset(fixtures.columns):
        raise ValueError("Season fixtures must contain HomeTeam and AwayTeam columns")
    fixture_pairs = list(fixtures[["HomeTeam", "AwayTeam"]].itertuples(index=False, name=None))

    return standings, fixture_pairs


def calculate_fixture_difficulty(
    df_current_standings: pd.DataFrame | None = None,
    remaining_fixtures: list[tuple[str, str]] | None = None,
    *,
    season_mode: str = "active_season_2627",
):
    """
    Compute FDI from supplied inputs or the selected season's data sandbox.
    """
    if df_current_standings is None or remaining_fixtures is None:
        season_standings, season_fixtures = load_season_inputs(season_mode)
        df_current_standings = season_standings if df_current_standings is None else df_current_standings
        remaining_fixtures = season_fixtures if remaining_fixtures is None else remaining_fixtures

    df_sorted = (
        df_current_standings
        .sort_values(by="xPts", ascending=False)
        .reset_index(drop=True)
    )

    num_teams = len(df_sorted)
    if num_teams < 2:
        raise ValueError("At least two teams are required to calculate FDI")

    team_difficulty = {}
    for index, row in df_sorted.iterrows():
        rank_tier = 5.0 - ((index / (num_teams - 1)) * 4.0)
        team_difficulty[row["Team"]] = round(rank_tier, 2)

    team_upcoming_difficulty = {team: [] for team in df_sorted["Team"]}
    for home, away in remaining_fixtures:
        if home not in team_difficulty or away not in team_difficulty:
            continue
        if len(team_upcoming_difficulty[home]) < 5:
            team_upcoming_difficulty[home].append(team_difficulty[away])
        if len(team_upcoming_difficulty[away]) < 5:
            team_upcoming_difficulty[away].append(team_difficulty[home])

    fdi_summary = []
    for team, diff_list in team_upcoming_difficulty.items():
        avg_fdi = np.mean(diff_list) if diff_list else 3.0
        if avg_fdi >= 3.6:
            tier = "Brutal"
        elif avg_fdi <= 2.4:
            tier = "Favorable"
        else:
            tier = "Moderate"
        fdi_summary.append(
            {
                "Team": team,
                "FDI_Remaining": round(float(avg_fdi), 2),
                "FDI_Tier": tier,
            }
        )

    return team_difficulty, pd.DataFrame(fdi_summary)


def fdi_goal_modifier(opponent_strength: float) -> float:
    """Convert a 1-to-5 opponent tier into a 0.90-to-1.10 goal modifier."""
    return float(np.clip(1.15 - (opponent_strength * 0.05), 0.90, 1.10))

