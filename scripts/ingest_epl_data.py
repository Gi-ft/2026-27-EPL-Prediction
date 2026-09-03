from __future__ import annotations

from pathlib import Path
import re

import pandas as pd
import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
STANDINGS_PATH = DATA_DIR / "epl_2526_results.csv"
MATCH_RESULTS_PATH = DATA_DIR / "epl_match_results.csv"


def _safe_int(value: str) -> int:
    return int(re.sub(r"[^\d-]", "", value))


def scrape_epl_data(url: str) -> None:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    standings_data: list[dict[str, object]] = []
    table = None
    for candidate in soup.find_all("table"):
        rows = candidate.find_all("tr")
        if len(rows) < 2:
            continue
        for row in rows[1:]:
            cols = row.find_all(["td", "th"])
            if len(cols) < 6:
                continue
            text_values = [cell.get_text(" ", strip=True) for cell in cols]
            if not text_values[1].strip():
                continue
            if re.search(r"\d", text_values[2]) and re.search(r"\d", text_values[3]):
                table = candidate
                break
        if table is not None:
            break

    if table is None:
        raise ValueError("Could not find a standings table on the page.")

    for row in table.find_all("tr")[1:]:
        cols = row.find_all(["td", "th"])
        if len(cols) < 6:
            continue

        text_values = [cell.get_text(" ", strip=True) for cell in cols]
        if not text_values[1].strip():
            continue

        team_name = text_values[1]
        matches = _safe_int(text_values[2])
        points = _safe_int(text_values[3])
        goals_raw = text_values[5]
        if ":" not in goals_raw:
            continue

        gf, ga = map(int, goals_raw.split(":", 1))
        standings_data.append(
            {
                "Team": team_name,
                "Matches": matches,
                "Points": points,
                "GF": gf,
                "GA": ga,
            }
        )

    match_results: list[dict[str, object]] = []
    for row in soup.find_all("div"):
        classes = row.get("class", [])
        if not any("match" in str(cls).lower() for cls in classes):
            continue

        home = row.find(class_=re.compile("home", re.I))
        away = row.find(class_=re.compile("away", re.I))
        score = row.find(class_=re.compile("score", re.I))
        if not (home and away and score):
            continue

        score_text = score.get_text(" ", strip=True)
        if ":" not in score_text:
            continue

        home_score, away_score = [part.strip() for part in score_text.split(":", 1)]
        if not (home_score.isdigit() and away_score.isdigit()):
            continue

        match_results.append(
            {
                "HomeTeam": home.get_text(" ", strip=True),
                "AwayTeam": away.get_text(" ", strip=True),
                "HomeGoals": int(home_score),
                "AwayGoals": int(away_score),
            }
        )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(standings_data).to_csv(STANDINGS_PATH, index=False)
    pd.DataFrame(match_results).to_csv(MATCH_RESULTS_PATH, index=False)

    print(f"Wrote {STANDINGS_PATH}")
    print(f"Wrote {MATCH_RESULTS_PATH}")


if __name__ == "__main__":
    scrape_epl_data("https://native-stats.org/competition/PL/")
