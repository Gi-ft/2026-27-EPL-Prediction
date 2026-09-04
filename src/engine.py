"""Season-aware execution entry point for EPL league simulations."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from epl_sim.simulator import run_monte_carlo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEASON_MODES = ("final_archive_2526", "active_season_2627")


def initialize_simulation_data(season_path: str | os.PathLike[str]):
    """
    Safely route fixtures, results, and priors for one season sandbox.
    """
    fixtures_file = os.path.join(season_path, "epl_fixtures.csv")
    results_file = os.path.join(season_path, "epl_results.csv")
    priors_file = os.path.join(season_path, "pre_season_priors.csv")

    for path in (fixtures_file, results_file, priors_file):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Required simulation input not found: {path}")

    df_fixtures = pd.read_csv(fixtures_file)
    df_results = pd.read_csv(results_file)
    df_priors = pd.read_csv(priors_file)

    required_fixture_columns = {"HomeTeam", "AwayTeam"}
    if not required_fixture_columns.issubset(df_fixtures.columns):
        raise ValueError("Fixtures CSV must contain HomeTeam and AwayTeam columns")
    if not {"HomeTeam", "AwayTeam"}.issubset(df_results.columns):
        raise ValueError("Results CSV must contain HomeTeam and AwayTeam columns")
    if not {"Team", "Actual_Points"}.issubset(df_priors.columns):
        raise ValueError("Priors CSV must contain Team and Actual_Points columns")

    return df_fixtures, df_results, df_priors


def run_league_simulation(
    season_mode: str = "active_season_2627",
    *,
    simulations: int = 1000,
    seed: int | None = None,
) -> dict[str, object]:
    """
    Dynamically load team data and scheduling maps for the selected season.
    """
    if season_mode not in SEASON_MODES:
        valid_modes = ", ".join(SEASON_MODES)
        raise ValueError(f"Unknown season_mode '{season_mode}'. Choose from: {valid_modes}")

    season_path = os.path.join(PROJECT_ROOT, "data", season_mode)
    df_fixtures, df_results, df_priors = initialize_simulation_data(season_path)

    # The dataframes above validate the selected sandbox before execution.
    del df_fixtures, df_results, df_priors

    fixtures_file = os.path.join(season_path, "epl_fixtures.csv")
    results_file = os.path.join(season_path, "epl_results.csv")
    ratings_file = os.path.join(PROJECT_ROOT, "data", "team_ratings.csv")
    stats_file = os.path.join(PROJECT_ROOT, "data", "team_stats_2025_26.csv")

    return run_monte_carlo(
        ratings_path=ratings_file,
        stats_path=stats_file,
        simulations=simulations,
        seed=seed,
        fixtures_path=fixtures_file,
        results_path=results_file,
    )


if __name__ == "__main__":
    run_league_simulation()
