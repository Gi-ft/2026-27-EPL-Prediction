"""Run the 2025/26 Monte Carlo engine and export raw universe-level results."""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from epl_sim.ratings import load_team_ratings
from epl_sim.simulator import round_robin_fixtures, simulate_season_with_fatigue
from process_simulation_logs import compute_opta_style_metrics


SIMULATIONS = 10_000
RAW_OUTPUT = ROOT / "data" / "all_simulated_universes_raw.csv"
SUMMARY_OUTPUT = ROOT / "data" / "season_summary.json"


def run_simulations(
    ratings_path: Path = ROOT / "data" / "team_ratings.csv",
    raw_output_path: Path = RAW_OUTPUT,
    simulations: int = SIMULATIONS,
    seed: int = 42,
) -> None:
    """Simulate complete seasons and write one row per team per universe."""
    teams = load_team_ratings(ratings_path)
    fixtures = round_robin_fixtures(teams)
    seed_generator = random.Random(seed)
    raw_output_path.parent.mkdir(parents=True, exist_ok=True)

    with raw_output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "SimulationRunID",
                "Team",
                "Points",
                "FinalRank",
                "GF",
                "GA",
                "GD",
            ],
        )
        writer.writeheader()

        for simulation_id in range(1, simulations + 1):
            season = simulate_season_with_fatigue(
                teams,
                fixtures,
                seed=seed_generator.randrange(1_000_000_000),
            )
            for final_rank, row in enumerate(season, start=1):
                writer.writerow(
                    {
                        "SimulationRunID": simulation_id,
                        "Team": row.team,
                        "Points": row.points,
                        "FinalRank": final_rank,
                        "GF": row.goals_for,
                        "GA": row.goals_against,
                        "GD": row.goal_difference,
                    }
                )

    print(f"Wrote {simulations:,} simulated seasons to '{raw_output_path}'")


def main() -> None:
    run_simulations()
    compute_opta_style_metrics(RAW_OUTPUT, SUMMARY_OUTPUT)


if __name__ == "__main__":
    main()
