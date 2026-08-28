#!/usr/bin/env python3
"""
Aggregate results from all batch directories into a single set of CSV and JSON files.
"""

import csv
import json
from pathlib import Path
import sys

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from timeless_forge.runner import parse_output


def main():
    if len(sys.argv) < 3:
        print("Usage: aggregate_results.py <all_results_dir> <output_dir>")
        return 1

    all_results_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Aggregating results from {all_results_dir}")

    # Map log file name to log path
    log_map = {}
    for log_file in sorted(all_results_dir.rglob("*.log")):
        log_map[log_file.name] = log_file

    all_batch_results = []
    all_raw_logs = []

    # Find all summary.csv files across batch directories
    for csv_file in sorted(all_results_dir.rglob("summary.csv")):
        print(f"  Reading {csv_file}")
        with open(csv_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Check if re-parsing raw log is necessary
                requested = int(row.get("requested_games", row.get("games", 400)))
                wins_a = int(row.get("wins_a", 0))
                wins_b = int(row.get("wins_b", 0))
                draws = int(row.get("draws", 0))
                unparsed = int(row.get("unparsed", 0))

                log_name = Path(row.get("raw_log", "")).name
                log_path = csv_file.parent / log_name if log_name else None
                if log_path and not log_path.exists() and log_name in log_map:
                    log_path = log_map[log_name]

                if (unparsed > 0 or (requested > 0 and wins_a + wins_b + draws == 0)) and log_path and log_path.exists():
                    log_text = log_path.read_text()
                    ra, rb, rd, ru = parse_output(log_text, row["deck_a"], row["deck_b"], requested)
                    row["wins_a"] = str(ra)
                    row["wins_b"] = str(rb)
                    row["draws"] = str(rd)
                    row["unparsed"] = str(ru)
                    row["parsed_games"] = str(ra + rb + rd)
                    if ra + rb > 0:
                        row["win_rate_a"] = f"{(ra / (ra + rb)):.4f}"
                    print(f"    Reparsed {row.get('matchup')}: wins_a={ra}, wins_b={rb}, draws={rd}, unparsed={ru}")

                all_batch_results.append(row)

    # Find all .log files
    for log_file in sorted(all_results_dir.rglob("*.log")):
        all_raw_logs.append(log_file)

    # Copy raw logs to output, preserving batch directory structure to avoid collisions
    logs_dir = output_dir / "raw-logs"
    logs_dir.mkdir(exist_ok=True)
    for log_file in all_raw_logs:
        rel_parent = log_file.parent.name
        batch_log_dir = logs_dir / rel_parent
        batch_log_dir.mkdir(exist_ok=True)
        dest = batch_log_dir / log_file.name
        dest.write_text(log_file.read_text())
    
    # Write aggregated CSV
    if all_batch_results:
        csv_path = output_dir / "combined-results.csv"
        fieldnames = list(all_batch_results[0].keys())
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_batch_results)
        print(f"\nWrote {len(all_batch_results)} results to {csv_path}")
        
        # Write aggregated JSON
        json_path = output_dir / "combined-results.json"
        with open(json_path, 'w') as f:
            json.dump(all_batch_results, f, indent=2)
        print(f"Wrote results to {json_path}")
    else:
        print("WARNING: No batch results found")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
