from __future__ import annotations

import sys
import unittest
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from epl_sim.ratings import load_team_ratings
from epl_sim.simulator import (
    FatigueConfig,
    compute_ratings,
    generate_remaining_fixtures,
    load_data,
    round_robin_fixtures,
    simulate_many_seasons,
    simulate_season,
)


class SimulatorTests(unittest.TestCase):
    def test_round_robin_fixture_count(self) -> None:
        teams = load_team_ratings(ROOT / "data" / "team_ratings.csv")
        fixtures = round_robin_fixtures(teams)
        self.assertEqual(len(fixtures), len(teams) * (len(teams) - 1))

    def test_season_table_has_all_teams(self) -> None:
        teams = load_team_ratings(ROOT / "data" / "team_ratings.csv")
        rows = simulate_season(teams, round_robin_fixtures(teams), seed=42)
        self.assertEqual(len(rows), len(teams))
        self.assertEqual({row.team for row in rows}, {team.name for team in teams})
        self.assertTrue(all(row.played == (len(teams) - 1) * 2 for row in rows))

    def test_round_robin_is_home_and_away(self) -> None:
        teams = load_team_ratings(ROOT / "data" / "team_ratings.csv")
        fixtures = round_robin_fixtures(teams)
        pair_counts: dict[tuple[str, str], int] = {}
        for home, away in fixtures:
            key = tuple(sorted((home, away)))
            pair_counts[key] = pair_counts.get(key, 0) + 1
        self.assertTrue(all(count == 2 for count in pair_counts.values()))

    def test_monte_carlo_results_track_probabilities(self) -> None:
        teams = load_team_ratings(ROOT / "data" / "team_ratings.csv")
        fixtures = round_robin_fixtures(teams)
        results = simulate_many_seasons(teams, fixtures, simulations=25, seed=7)
        self.assertEqual(len(results), len(teams))
        self.assertTrue(all(result.simulations == 25 for result in results))
        self.assertTrue(all(0.0 <= result.title_probability <= 1.0 for result in results))
        self.assertTrue(all(0.0 <= result.top_four_probability <= 1.0 for result in results))
        self.assertTrue(all(0.0 <= result.relegation_probability <= 1.0 for result in results))

    def test_compute_ratings_from_stats(self) -> None:
        stats = load_data(ROOT / "data" / "team_stats_2025_26.csv")
        ratings = compute_ratings(stats)
        self.assertEqual(len(ratings), len(stats))
        self.assertTrue(all(isinstance(team.name, str) for team in ratings))

    def test_load_team_ratings_from_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ratings.csv"
            path.write_text(
                "name,attack,defense,home_advantage\n"
                "Team A,0.1,0.2,0.05\n"
                "Team B,0.2,0.1,0.03\n",
                encoding="utf-8",
            )
            teams = load_team_ratings(path)
            self.assertEqual(len(teams), 2)
            self.assertEqual(teams[0].name, "Team A")
            self.assertAlmostEqual(teams[1].attack, 0.2)

    def test_generate_remaining_fixtures_skips_played_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fixtures_path = Path(tmpdir) / "fixtures.csv"
            results_path = Path(tmpdir) / "results.csv"

            fixtures_path.write_text(
                "HomeTeam,AwayTeam\n"
                "Arsenal,Chelsea\n"
                "Liverpool,Everton\n"
                "Tottenham Hotspur,Manchester City\n",
                encoding="utf-8",
            )
            results_path.write_text(
                "HomeTeam,AwayTeam,HomeGoals,AwayGoals\n"
                "Arsenal,Chelsea,2,1\n"
                "Tottenham Hotspur,Manchester City,0,0\n",
                encoding="utf-8",
            )

            remaining = generate_remaining_fixtures(fixtures_path, results_path)
            self.assertEqual(remaining, [("Liverpool", "Everton")])

    def test_fatigue_config_changes_simulation_path(self) -> None:
        teams = load_team_ratings(ROOT / "data" / "team_ratings.csv")
        fixtures = round_robin_fixtures(teams)
        fatigue_config = FatigueConfig(
            european_teams=frozenset({teams[0].name}),
            midweek_drain=25,
            recovery=0,
            european_match_probability=1.0,
        )
        fatigue_rows = simulate_season(teams, fixtures, seed=42)
        fatigue_rows_custom = simulate_many_seasons(
            teams, fixtures, simulations=1, seed=42, fatigue_config=fatigue_config
        )
        self.assertEqual(len(fatigue_rows), len(teams))
        self.assertEqual(len(fatigue_rows_custom), len(teams))


if __name__ == "__main__":
    unittest.main()
