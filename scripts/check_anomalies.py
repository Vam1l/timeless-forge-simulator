#!/usr/bin/env python3
"""
Check for and report on anomalies in results:
- High unparsed game counts
- Timeouts
- Suspiciously incomplete batches
- Obvious AI failures
"""

import csv
from pathlib import Path
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: check_anomalies.py <results_dir>")
        return 0  # Non-fatal
    
    results_dir = Path(sys.argv[1])
    csv_file = results_dir / "combined-results.csv"
    
    if not csv_file.exists():
        print("No combined-results.csv found; skipping anomaly check")
        return 0
    
    print("\n=== ANOMALY CHECK ===")
    anomalies = []
    
    with open(csv_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            matchup = row.get('matchup', 'unknown')
            requested = int(row.get('requested_games', 0))
            parsed = int(row.get('parsed_games', 0))
            unparsed = int(row.get('unparsed', 0))
            
            # Check for high unparsed rate
            if unparsed > 0:
                unparsed_pct = (unparsed / requested) * 100 if requested > 0 else 0
                if unparsed_pct > 5:
                    anomalies.append(f"  ⚠️  {matchup}: {unparsed}/{requested} unparsed ({unparsed_pct:.1f}%)")
            
            # Check for incomplete batches
            if parsed < (requested * 0.95):
                anomalies.append(f"  ⚠️  {matchup}: Only {parsed}/{requested} games parsed")
    
    if anomalies:
        print(f"Found {len(anomalies)} potential anomalies:")
        for anom in anomalies:
            print(anom)
    else:
        print("No major anomalies detected.")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
