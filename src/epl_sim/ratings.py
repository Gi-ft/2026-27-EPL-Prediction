from __future__ import annotations

import csv
from pathlib import Path

from .models import TeamRating


def load_team_ratings(path: str | Path) -> list[TeamRating]:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Ratings file not found: {source}")

    with source.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"name", "attack", "defense", "home_advantage"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError("Ratings CSV must contain name, attack, defense, home_advantage columns")

        ratings: list[TeamRating] = []
        for row in reader:
            ratings.append(
                TeamRating(
                    name=row["name"].strip(),
                    attack=float(row["attack"]),
                    defense=float(row["defense"]),
                    home_advantage=float(row["home_advantage"]),
                )
            )

    if len(ratings) < 2:
        raise ValueError("Ratings file must contain at least two teams")

    names = [team.name for team in ratings]
    if len(names) != len(set(names)):
        raise ValueError("Ratings file contains duplicate team names")

    return ratings

