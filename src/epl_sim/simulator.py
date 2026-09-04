from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

from .models import SeasonResult, TableRow, TeamRating
from .ratings import load_team_ratings


@dataclass(frozen=True)
class FatigueConfig:
    european_teams: frozenset[str] = frozenset()
    midweek_drain: int = 15
    recovery: int = 10
    european_match_probability: float = 0.70
    minimum_energy: int = 20


@dataclass(frozen=True)
class RawTeamStats:
    name: str
    goals_for: float
    goals_against: float
    home_goals_for: float
    away_goals_for: float


def load_data(path: str | Path) -> list[RawTeamStats]:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Stats file not found: {source}")

    with source.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"name", "goals_for", "goals_against", "home_goals_for", "away_goals_for"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                "Stats CSV must contain name, goals_for, goals_against, home_goals_for, away_goals_for columns"
            )

        rows: list[RawTeamStats] = []
        for row in reader:
            rows.append(
                RawTeamStats(
                    name=row["name"].strip(),
                    goals_for=float(row["goals_for"]),
                    goals_against=float(row["goals_against"]),
                    home_goals_for=float(row["home_goals_for"]),
                    away_goals_for=float(row["away_goals_for"]),
                )
            )

    if len(rows) < 2:
        raise ValueError("Stats file must contain at least two teams")

    return rows


def compute_ratings(rows: list[RawTeamStats]) -> list[TeamRating]:
    league_avg_gf = sum(row.goals_for for row in rows) / len(rows) / 38.0
    league_avg_ga = sum(row.goals_against for row in rows) / len(rows) / 38.0
    league_avg_home_gf = sum(row.home_goals_for for row in rows) / len(rows) / 19.0
    league_avg_away_gf = sum(row.away_goals_for for row in rows) / len(rows) / 19.0

    # Shrink extreme teams toward the league average so the simulation stays stable.
    attack_center = league_avg_gf
    defense_center = league_avg_ga

    ratings: list[TeamRating] = []
    for row in rows:
        gf = row.goals_for / 38.0
        ga = row.goals_against / 38.0
        hgf = row.home_goals_for / 19.0
        agf = row.away_goals_for / 19.0

        attack_raw = (gf - attack_center) / attack_center
        defense_raw = (defense_center - ga) / defense_center
        home_raw = (hgf - agf) / max(0.1, (league_avg_home_gf + league_avg_away_gf) / 2)

        attack = round(max(-0.25, min(0.75, attack_raw * 0.45)), 3)
        defense = round(max(-0.25, min(0.75, defense_raw * 0.45)), 3)
        home_advantage = round(max(-0.05, min(0.25, home_raw * 0.08)), 3)

        ratings.append(
            TeamRating(
                name=row.name.replace("AFC Bournemouth", "Bournemouth").replace(
                    "Brighton & Hove Albion", "Brighton"
                ),
                attack=attack,
                defense=defense,
                home_advantage=home_advantage,
            )
        )

    return ratings


def round_robin_fixtures(teams: list[TeamRating]) -> list[tuple[str, str]]:
    if len(teams) < 2:
        raise ValueError("Need at least two teams to build fixtures")

    names = [team.name for team in teams]
    if len(names) % 2 == 1:
        names.append("__BYE__")

    rounds = len(names) - 1
    half = len(names) // 2
    rotation = names[:]
    fixtures: list[tuple[str, str]] = []

    for _ in range(rounds):
        left = rotation[:half]
        right = list(reversed(rotation[half:]))

        for home, away in zip(left, right, strict=True):
            if home != "__BYE__" and away != "__BYE__":
                fixtures.append((home, away))

        fixed = rotation[0]
        moving = rotation[1:]
        moving = [moving[-1], *moving[:-1]]
        rotation = [fixed, *moving]

    return fixtures + [(away, home) for home, away in fixtures]


def generate_remaining_fixtures(
    fixtures_file_path: str | Path, results_file_path: str | Path
) -> list[tuple[str, str]]:
    """Return only fixtures that have not been played yet.

    The master calendar should contain at least ``HomeTeam`` and ``AwayTeam``.
    The results file should contain at least ``HomeTeam`` and ``AwayTeam`` for
    completed matches. Any master fixture already present in the results file is
    excluded from the returned simulation queue.
    """

    fixtures_source = Path(fixtures_file_path)
    results_source = Path(results_file_path)

    if not fixtures_source.exists():
        raise FileNotFoundError(f"Fixtures file not found: {fixtures_source}")
    if not results_source.exists():
        raise FileNotFoundError(f"Results file not found: {results_source}")

    with fixtures_source.open("r", encoding="utf-8", newline="") as handle:
        fixtures_reader = csv.DictReader(handle)
        required = {"HomeTeam", "AwayTeam"}
        if not fixtures_reader.fieldnames or not required.issubset(set(fixtures_reader.fieldnames)):
            raise ValueError("Fixtures CSV must contain HomeTeam and AwayTeam columns")
        master_fixtures = list(fixtures_reader)

    with results_source.open("r", encoding="utf-8", newline="") as handle:
        results_reader = csv.DictReader(handle)
        required = {"HomeTeam", "AwayTeam"}
        if not results_reader.fieldnames or not required.issubset(set(results_reader.fieldnames)):
            raise ValueError("Results CSV must contain HomeTeam and AwayTeam columns")
        played_tokens = {
            f"{row['HomeTeam'].strip()} vs {row['AwayTeam'].strip()}" for row in results_reader
        }

    remaining_fixtures: list[tuple[str, str]] = []
    for row in master_fixtures:
        home = row["HomeTeam"].strip()
        away = row["AwayTeam"].strip()
        if f"{home} vs {away}" not in played_tokens:
            remaining_fixtures.append((home, away))

    return remaining_fixtures


def expected_goals(home: TeamRating, away: TeamRating) -> tuple[float, float]:
    home_xg = max(0.2, 1.35 + home.attack - away.defense + home.home_advantage)
    away_xg = max(0.2, 1.05 + away.attack - home.defense)
    return home_xg, away_xg


def apply_fatigue(
    rng: random.Random, energy: dict[str, int], home: str, away: str, config: FatigueConfig
) -> tuple[float, float]:
    if home in config.european_teams and rng.random() < config.european_match_probability:
        energy[home] = max(config.minimum_energy, energy[home] - config.midweek_drain)
    if away in config.european_teams and rng.random() < config.european_match_probability:
        energy[away] = max(config.minimum_energy, energy[away] - config.midweek_drain)

    home_fatigue_mod = energy[home] / 100.0
    away_fatigue_mod = energy[away] / 100.0
    return home_fatigue_mod, away_fatigue_mod


def fatigue_adjusted_expected_goals(
    home: TeamRating,
    away: TeamRating,
    home_fatigue_mod: float,
    away_fatigue_mod: float,
) -> tuple[float, float]:
    home_xg, away_xg = expected_goals(home, away)
    home_xg = (home_xg * home_fatigue_mod) / max(away_fatigue_mod, 0.1)
    away_xg = (away_xg * away_fatigue_mod) / max(home_fatigue_mod, 0.1)
    return max(0.1, home_xg), max(0.1, away_xg)


def poisson_sample(rng: random.Random, lam: float) -> int:
    limit = math.exp(-lam)
    k = 0
    p = 1.0
    while p > limit:
        k += 1
        p *= rng.random()
    return k - 1


def simulate_match(
    rng: random.Random, home: TeamRating, away: TeamRating
) -> tuple[int, int]:
    home_xg, away_xg = expected_goals(home, away)
    return poisson_sample(rng, home_xg), poisson_sample(rng, away_xg)


def simulate_match_with_fatigue(
    rng: random.Random,
    home: TeamRating,
    away: TeamRating,
    home_fatigue_mod: float,
    away_fatigue_mod: float,
) -> tuple[int, int]:
    home_xg, away_xg = fatigue_adjusted_expected_goals(
        home, away, home_fatigue_mod, away_fatigue_mod
    )
    return poisson_sample(rng, home_xg), poisson_sample(rng, away_xg)


def empty_table(teams: Iterable[TeamRating]) -> dict[str, TableRow]:
    return {team.name: TableRow(team=team.name) for team in teams}


def record_result(table: dict[str, TableRow], home: str, away: str, hg: int, ag: int) -> None:
    home_row = table[home]
    away_row = table[away]

    home_row.played += 1
    away_row.played += 1
    home_row.goals_for += hg
    home_row.goals_against += ag
    away_row.goals_for += ag
    away_row.goals_against += hg

    if hg > ag:
        home_row.wins += 1
        away_row.losses += 1
    elif hg < ag:
        away_row.wins += 1
        home_row.losses += 1
    else:
        home_row.draws += 1
        away_row.draws += 1


def simulate_season(
    teams: list[TeamRating], fixtures: list[tuple[str, str]], seed: int | None = None
) -> list[TableRow]:
    return simulate_season_with_fatigue(teams, fixtures, seed=seed)


def simulate_season_with_fatigue(
    teams: list[TeamRating],
    fixtures: list[tuple[str, str]],
    seed: int | None = None,
    fatigue_config: FatigueConfig | None = None,
) -> list[TableRow]:
    rng = random.Random(seed)
    team_map = {team.name: team for team in teams}
    table = empty_table(teams)
    fatigue_config = fatigue_config or FatigueConfig()
    energy = {team.name: 100 for team in teams}

    for home_name, away_name in fixtures:
        home = team_map[home_name]
        away = team_map[away_name]
        home_fatigue_mod, away_fatigue_mod = apply_fatigue(
            rng, energy, home_name, away_name, fatigue_config
        )
        hg, ag = simulate_match_with_fatigue(
            rng, home, away, home_fatigue_mod, away_fatigue_mod
        )
        record_result(table, home_name, away_name, hg, ag)
        energy[home_name] = min(100, energy[home_name] + fatigue_config.recovery)
        energy[away_name] = min(100, energy[away_name] + fatigue_config.recovery)

    return sorted(
        table.values(),
        key=lambda row: (row.points, row.goal_difference, row.goals_for),
        reverse=True,
    )


def season_summary(rows: list[TableRow]) -> dict[str, object]:
    return {
        "table": [asdict(row) | {"points": row.points, "goal_difference": row.goal_difference} for row in rows]
    }


def simulate_many_seasons(
    teams: list[TeamRating],
    fixtures: list[tuple[str, str]],
    simulations: int = 1000,
    seed: int | None = None,
    fatigue_config: FatigueConfig | None = None,
) -> list[SeasonResult]:
    if simulations < 1:
        raise ValueError("simulations must be at least 1")

    rng = random.Random(seed)
    results = {team.name: SeasonResult(team=team.name, simulations=simulations) for team in teams}

    for _ in range(simulations):
        season_seed = rng.randrange(1_000_000_000)
        table = simulate_season_with_fatigue(
            teams, fixtures, seed=season_seed, fatigue_config=fatigue_config
        )

        for idx, row in enumerate(table):
            result = results[row.team]
            if idx == 0:
                result.titles += 1
            if idx < 4:
                result.top_four += 1
            if idx >= len(table) - 3:
                result.relegations += 1

    return sorted(
        results.values(),
        key=lambda result: (result.title_probability, result.top_four_probability, -result.relegation_probability),
        reverse=True,
    )


def simulate_many_seasons_with_points(
    teams: list[TeamRating],
    fixtures: list[tuple[str, str]],
    simulations: int = 1000,
    seed: int | None = None,
    fatigue_config: FatigueConfig | None = None,
) -> tuple[list[SeasonResult], dict[str, list[int]]]:
    if simulations < 1:
        raise ValueError("simulations must be at least 1")

    rng = random.Random(seed)
    results = {team.name: SeasonResult(team=team.name, simulations=simulations) for team in teams}
    point_distributions = {team.name: [] for team in teams}

    for _ in range(simulations):
        season_seed = rng.randrange(1_000_000_000)
        table = simulate_season_with_fatigue(
            teams, fixtures, seed=season_seed, fatigue_config=fatigue_config
        )

        for idx, row in enumerate(table):
            result = results[row.team]
            point_distributions[row.team].append(row.points)
            if idx == 0:
                result.titles += 1
            if idx < 4:
                result.top_four += 1
            if idx >= len(table) - 3:
                result.relegations += 1

    return (
        sorted(
            results.values(),
            key=lambda result: (
                result.title_probability,
                result.top_four_probability,
                -result.relegation_probability,
            ),
            reverse=True,
        ),
        point_distributions,
    )


def monte_carlo_summary(
    results: list[SeasonResult], point_distributions: dict[str, list[int]] | None = None
) -> dict[str, object]:
    return {
        "teams": [
            asdict(result)
            | {
                "title_probability": result.title_probability,
                "top_four_probability": result.top_four_probability,
                "relegation_probability": result.relegation_probability,
                "points_distribution": point_distributions.get(result.team, [])
                if point_distributions is not None
                else [],
            }
            for result in results
        ]
    }


def run_monte_carlo(
    ratings_path: str | Path | None,
    stats_path: str | Path,
    simulations: int = 1000,
    seed: int | None = None,
    fixtures_path: str | Path | None = None,
    results_path: str | Path | None = None,
    fatigue_config: FatigueConfig | None = None,
) -> dict[str, object]:
    stats = load_data(stats_path)
    teams = compute_ratings(stats)
    if ratings_path is not None and Path(ratings_path).exists():
        teams = load_team_ratings(ratings_path)

    fixtures = round_robin_fixtures(teams)
    if fixtures_path is not None and results_path is not None:
        fixtures = generate_remaining_fixtures(fixtures_path, results_path)
    rows = simulate_season_with_fatigue(teams, fixtures, seed=seed, fatigue_config=fatigue_config)
    summary = season_summary(rows)
    monte_carlo_results, point_distributions = simulate_many_seasons_with_points(
        teams, fixtures, simulations=simulations, seed=seed, fatigue_config=fatigue_config
    )
    odds = monte_carlo_summary(monte_carlo_results, point_distributions)
    return {"single_season": summary, "monte_carlo": odds, "teams": teams}
