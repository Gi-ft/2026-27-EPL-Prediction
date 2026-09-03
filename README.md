# EPL 2026/2027 Season Simulator

This project simulates an English Premier League season using a simple Monte Carlo model.

## What it does

- Simulates individual matches from team attack/defense ratings
- Runs a full 38-match season for each club
- Repeats the season many times to estimate title, top-four, and relegation odds
- Exports results as JSON and prints a summary table

## Ratings source

The starter ratings are now generated from Statbunker's latest completed Premier League season data. The raw source stats live in `data/team_stats_2025_26.csv`, and `scripts/build_ratings.py` regenerates `data/team_ratings.csv`.

The default promoted-team replacements in the ratings workflow are:

- Coventry City
- Ipswich Town
- Hull City

`scripts/build_ratings.py` applies Championship-to-Premier-League translation factors of `0.70` for expected goals for and `0.15` for expected goals against when imputing those teams.

## Data ingestion

`scripts/ingest_epl_data.py` scrapes live standings and recent match results from the Native Stats Premier League page and exports them to:

- `data/epl_2526_results.csv`
- `data/epl_match_results.csv`

The GitHub Actions workflow in `.github/workflows/pipeline_sync.yml` runs this ingestion automatically every night and can also be started manually with `workflow_dispatch`. Each run rebuilds team ratings, regenerates the Monte Carlo outputs, and commits changed data artifacts back to the repository.

## Remaining fixtures

If you want to simulate only matches that have not been played yet, use the master schedule together with the real results file. The simulator exposes a `generate_remaining_fixtures(fixtures_file_path, results_file_path)` helper for that workflow.

Example usage:

```python
from pathlib import Path
from epl_sim.simulator import generate_remaining_fixtures, run_monte_carlo

fixtures = generate_remaining_fixtures(
    Path("data/master_fixtures.csv"),
    Path("data/epl_match_results.csv"),
)
```

## Next steps

1. Replace the default team ratings with real 2026/2027 inputs
2. Add injuries, transfers, and form
3. Add charts and a simple dashboard

## Visuals

Generate charts from `season_summary.json` with:

```python
python scripts/generate_visuals.py
```

This writes static and interactive assets to `output_plots/`:

- `epl_probability_heatmap.png`
- `points_snapshot.html`

## Streamlit Dashboard

Launch the interactive dashboard from the project root:

```powershell
.\run_streamlit.bat
```

If you prefer to run it manually from an active virtual environment:

```powershell
streamlit run app.py
```

The dashboard reads directly from `season_summary.json` and mirrors the same league table, odds, and points
distribution snapshots used by the static HTML exports.
