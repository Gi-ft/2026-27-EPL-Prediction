from __future__ import annotations

import json
from pathlib import Path

from .simulator import run_monte_carlo


def main() -> None:
    payload = run_monte_carlo(
        ratings_path=Path("data/team_ratings.csv"),
        stats_path=Path("data/team_stats_2025_26.csv"),
        simulations=1000,
        seed=42,
    )
    summary = payload["single_season"]
    odds = payload["monte_carlo"]

    print("EPL simulation summary")
    for idx, row in enumerate(summary["table"], start=1):
        print(
            f"{idx:2d}. {row['team']:<18} {row['points']:>3} pts "
            f"GD {row['goal_difference']:>3} GF {row['goals_for']:>3} GA {row['goals_against']:>3}"
        )

    print("\nMonte Carlo probabilities")
    for row in odds["teams"]:
        print(
            f"{row['team']:<22} "
            f"Title {row['title_probability']:.1%}  "
            f"Top 4 {row['top_four_probability']:.1%}  "
            f"Relegation {row['relegation_probability']:.1%}"
        )

    out = Path("season_summary.json")
    out.write_text(json.dumps({"single_season": summary, "monte_carlo": odds}, indent=2), encoding="utf-8")
    print(f"\nWrote {out.resolve()}")
