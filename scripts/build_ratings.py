from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATS_PATH = ROOT / "data" / "team_stats_2025_26.csv"
RATINGS_PATH = ROOT / "data" / "team_ratings.csv"

PROMOTED_TEAM_MAP = {
    # Source-season clubs are replaced by the promoted clubs below.
    "Wolverhampton Wanderers": "Coventry City",
    "Burnley": "Ipswich Town",
    "West Ham United": "Hull City",
}


def impute_promoted_team_ratings(
    premier_league_profiles: list[dict[str, float | str]],
    league_averages: dict[str, float],
) -> list[dict[str, float | str]]:
    """Replace relegated teams with promoted-team estimates.

    The promoted clubs are estimated from Championship-style output translated
    into Premier League strength so the downstream simulator keeps a full
    20-team league.
    """

    promoted_championship_data = {
        "Coventry City": {"gf_pg": 2.11, "ga_pg": 0.98},
        "Ipswich Town": {"gf_pg": 1.74, "ga_pg": 1.02},
        "Hull City": {"gf_pg": 1.52, "ga_pg": 1.43},
    }

    pl_avg_home_goals = league_averages["home_goals_avg"]
    pl_avg_away_goals = league_averages["away_goals_avg"]

    updated_profiles: list[dict[str, float | str]] = []
    promoted_lookup = {old_name: new_name for old_name, new_name in PROMOTED_TEAM_MAP.items()}

    for row in premier_league_profiles:
        if row["name"] not in promoted_lookup:
            updated_profiles.append(row)
            continue

        team = promoted_lookup[row["name"]]
        stats = promoted_championship_data[team]
        estimated_pl_gf = stats["gf_pg"] * 0.70
        # Promotion adjustment increases expected goals conceded at Premier League level.
        estimated_pl_ga = stats["ga_pg"] / 0.70

        updated_profiles.append(
            {
                "name": team,
                "attack": round((estimated_pl_gf / max(pl_avg_home_goals, 1e-6)) - 1.0, 3),
                "defense": round((pl_avg_away_goals / max(estimated_pl_ga, 1e-6)) - 1.0, 3),
                "home_advantage": round(
                    ((estimated_pl_gf * 1.1) / max(pl_avg_home_goals, 1e-6))
                    - ((estimated_pl_gf * 0.9) / max(pl_avg_away_goals, 1e-6)),
                    3,
                ),
            }
        )

    return updated_profiles


def main() -> None:
    with STATS_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    league_avg_gf = sum(float(row["goals_for"]) for row in rows) / len(rows) / 38.0
    league_avg_ga = sum(float(row["goals_against"]) for row in rows) / len(rows) / 38.0
    league_avg_home_goals = sum(float(row["home_goals_for"]) for row in rows) / len(rows) / 19.0
    league_avg_away_goals = sum(float(row["away_goals_for"]) for row in rows) / len(rows) / 19.0

    output_rows = []
    for row in rows:
        gf = float(row["goals_for"]) / 38.0
        ga = float(row["goals_against"]) / 38.0
        hgf = float(row["home_goals_for"]) / 19.0
        agf = float(row["away_goals_for"]) / 19.0

        attack = round((gf / league_avg_gf - 1.0) * 0.55, 3)
        defense = round((league_avg_ga / ga - 1.0) * 0.55, 3)
        home_advantage = round((hgf - agf) * 0.08, 3)

        output_rows.append(
            {
                "name": row["name"].replace("AFC Bournemouth", "Bournemouth").replace(
                    "Brighton & Hove Albion", "Brighton"
                ),
                "attack": attack,
                "defense": defense,
                "home_advantage": home_advantage,
            }
        )

    output_rows = impute_promoted_team_ratings(
        output_rows,
        {
            "home_goals_avg": league_avg_home_goals,
            "away_goals_avg": league_avg_away_goals,
            "goals_for_avg": league_avg_gf,
            "goals_against_avg": league_avg_ga,
        },
    )
    output_rows.sort(key=lambda row: row["name"])

    with RATINGS_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["name", "attack", "defense", "home_advantage"])
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Wrote {RATINGS_PATH}")


if __name__ == "__main__":
    main()

