"""Automated live data ingestion entry point for GitHub Actions."""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ingest_epl_data import (  # noqa: E402
    MATCH_RESULTS_PATH,
    STANDINGS_PATH,
    scrape_epl_data,
)


DEFAULT_URL = "https://native-stats.org/competition/PL/"


def run_automated_harvester() -> None:
    """Fetch live Premier League data and write the project's data files."""
    os.makedirs(ROOT / "data", exist_ok=True)
    source_url = os.getenv("EPL_SOURCE_URL", DEFAULT_URL)

    print(f"Scraping live results data stream from {source_url}...")
    scrape_epl_data(source_url)

    for output_path in (STANDINGS_PATH, MATCH_RESULTS_PATH):
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError(f"Ingestion produced an empty output: {output_path}")

    print("Harvester step complete.")


if __name__ == "__main__":
    run_automated_harvester()
