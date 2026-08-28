#!/usr/bin/env python3
"""
Aggregate results from all batch directories into a single set of CSV and JSON files.
"""

import csv
import json
from pathlib import Path
import sys

def main():
    if len(sys.argv) < 3:
        print("Usage: aggregate_results.py <all_results_dir> <output_dir>")
        return 1
    
    all_results_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Aggregating results from {all_results_dir}")
    
    all_batch_results = []
    all_raw_logs = []
    
    # Find all summary.csv files across batch directories
    for csv_file in sorted(all_results_dir.rglob("summary.csv")):
        print(f"  Reading {csv_file}")
        with open(csv_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                all_batch_results.append(row)
    
    # Find all .log files
    for log_file in sorted(all_results_dir.rglob("*.log")):
        all_raw_logs.append(log_file)
    
    # Copy raw logs to output
    logs_dir = output_dir / "raw-logs"
    logs_dir.mkdir(exist_ok=True)
    for log_file in all_raw_logs:
        dest = logs_dir / log_file.name
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
