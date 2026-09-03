import os
from pathlib import Path

import numpy as np
import pandas as pd


def compute_opta_style_metrics(raw_universes_path, output_summary_path):
    """
    Parses the Monte Carlo simulation logs and exports Opta-style dashboard metrics.
    """
    raw_universes_path = Path(raw_universes_path)
    output_summary_path = Path(output_summary_path)

    if not os.path.exists(raw_universes_path):
        raise FileNotFoundError(
            f"Missing core raw simulation file: '{raw_universes_path}'. Run simulator first."
        )

    print("⏳ Parsing Monte Carlo simulation logs...")
    df_raw = pd.read_csv(raw_universes_path)

    required_columns = {
        "SimulationRunID",
        "Team",
        "Points",
        "FinalRank",
        "GF",
        "GA",
        "GD",
    }
    missing_columns = required_columns.difference(df_raw.columns)
    if missing_columns:
        raise ValueError(f"Raw simulation file is missing required columns: {sorted(missing_columns)}")

    aggregated_metrics = {}
    grouped = df_raw.groupby("Team")

    for team, group in grouped:
        xpts = group["Points"].mean()

        total_runs = len(group)
        title_count = np.sum(group["FinalRank"] == 1)
        ucl_count = np.sum(group["FinalRank"] <= 4)
        uel_count = np.sum((group["FinalRank"] == 5) | (group["FinalRank"] == 6))
        rel_count = np.sum(group["FinalRank"] >= 18)

        aggregated_metrics[team] = {
            "Team": team,
            "xPts": round(float(xpts), 2),
            "GF": int(round(float(group["GF"].mean()))),
            "GA": int(round(float(group["GA"].mean()))),
            "GD": int(round(float(group["GD"].mean()))),
            "TITLE": round((title_count / total_runs) * 100, 2),
            "UCL": round((ucl_count / total_runs) * 100, 2),
            "UEL": round((uel_count / total_runs) * 100, 2),
            "REL": round((rel_count / total_runs) * 100, 2),
            "points_distribution": group["Points"].astype(float).tolist(),
        }

    df_opta = pd.DataFrame.from_dict(aggregated_metrics, orient="index")
    df_opta = df_opta.sort_values(by="xPts", ascending=False).reset_index(drop=True)
    df_opta.insert(0, "XPOS", df_opta.index + 1)

    output_summary_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_output_path = output_summary_path.with_suffix(output_summary_path.suffix + ".tmp")
    df_opta.to_json(temporary_output_path, orient="records", indent=4)
    temporary_output_path.replace(output_summary_path)
    print(f"✅ Success! Opta-aligned summary saved to '{output_summary_path}'")


if __name__ == "__main__":
    compute_opta_style_metrics(
        raw_universes_path="data/all_simulated_universes_raw.csv",
        output_summary_path="data/season_summary.json",
    )
