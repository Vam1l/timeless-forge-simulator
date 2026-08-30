#!/usr/bin/env python3
"""
Check for and report on anomalies and Stage 2 validation gates in results:
- exactly 45 unique unordered matchups
- exactly 90 orientation runs
- exactly 200 games per orientation
- exactly 400 accounted games per unordered matchup
- exactly 18,000 total accounted games
- 0 unparsed games
- flag global Deck-A or Deck-B win rate outside 47.5–52.5%
- flag deck overall WR outside 45–55%
- flag individual matchup outside 35–65%
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

    print("\n=== STAGE 2 ANOMALY & VALIDATION GATE CHECK ===")
    anomalies = []
    orientation_runs = 0
    total_accounted = 0
    total_unparsed = 0
    total_wins_a = 0
    total_wins_b = 0
    unordered_games = {}
    deck_stats = {}

    with open(csv_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            orientation_runs += 1
            deck_a = row.get("deck_a", "")
            deck_b = row.get("deck_b", "")
            requested = int(row.get("games", row.get("requested_games", 200)))
            wins_a = int(row.get("wins_a", 0))
            wins_b = int(row.get("wins_b", 0))
            draws = int(row.get("draws", 0))
            unparsed = int(row.get("unparsed", 0))

            total_wins_a += wins_a
            total_wins_b += wins_b
            accounted = wins_a + wins_b + draws
            total_accounted += accounted
            total_unparsed += unparsed

            # Track deck stats
            for d, w, l in [(deck_a, wins_a, wins_b), (deck_b, wins_b, wins_a)]:
                if d not in deck_stats:
                    deck_stats[d] = {"wins": 0, "games": 0}
                deck_stats[d]["wins"] += w
                deck_stats[d]["games"] += w + l + draws

            # Track unordered pair games
            pair_key = tuple(sorted([deck_a, deck_b]))
            if pair_key not in unordered_games:
                unordered_games[pair_key] = {"wins_x": 0, "wins_y": 0, "draws": 0, "unparsed": 0, "total": 0}
            rec = unordered_games[pair_key]
            rec["total"] += accounted
            rec["draws"] += draws
            rec["unparsed"] += unparsed
            if deck_a == pair_key[0]:
                rec["wins_x"] += wins_a
                rec["wins_y"] += wins_b
            else:
                rec["wins_x"] += wins_b
                rec["wins_y"] += wins_a

            if unparsed > 0:
                anomalies.append(f"  ⚠️  {deck_a} vs {deck_b}: {unparsed} unparsed games")
            if accounted != 200:
                anomalies.append(f"  ⚠️  {deck_a} vs {deck_b}: {accounted}/200 games accounted")

    # Gates check
    if orientation_runs != 90:
        anomalies.append(f"  ⚠️  Gate failure: Expected 90 orientation runs, found {orientation_runs}")
    if len(unordered_games) != 45:
        anomalies.append(f"  ⚠️  Gate failure: Expected 45 unique unordered matchups, found {len(unordered_games)}")
    if total_accounted != 18000:
        anomalies.append(f"  ⚠️  Gate failure: Expected 18,000 total games, found {total_accounted}")
    if total_unparsed > 0:
        anomalies.append(f"  ⚠️  Gate failure: Expected 0 unparsed games, found {total_unparsed}")

    for pair, rec in unordered_games.items():
        if rec["total"] != 400:
            anomalies.append(f"  ⚠️  Gate failure: Matchup {pair[0]} vs {pair[1]} has {rec['total']}/400 games")
        tot = rec["wins_x"] + rec["wins_y"]
        if tot > 0:
            wr_x = rec["wins_x"] / tot
            if not (0.35 <= wr_x <= 0.65):
                anomalies.append(f"  ⚠️  Matchup WR flag: {pair[0]} vs {pair[1]} = {wr_x:.1%}")

    # Global seat bias
    decisive = total_wins_a + total_wins_b
    if decisive > 0:
        win_rate_a = total_wins_a / decisive
        if not (0.475 <= win_rate_a <= 0.525):
            anomalies.append(f"  ⚠️  Global Seat Bias flag: Deck A win rate = {win_rate_a:.1%} (outside 47.5-52.5%)")

    # Deck win rates
    for d, s in deck_stats.items():
        if s["games"] > 0:
            wr = s["wins"] / s["games"]
            if not (0.45 <= wr <= 0.55):
                anomalies.append(f"  ⚠️  Deck WR flag: {d} overall win rate = {wr:.1%} (outside 45-55%)")

    if anomalies:
        print(f"Found {len(anomalies)} validation warnings/flags:")
        for anom in anomalies:
            print(anom)
    else:
        print("All Stage 2 validation gates passed! Exactly 90 orientations, 45 matchups, 18,000 games, 0 unparsed.")

    return 0

if __name__ == '__main__':
    sys.exit(main())
