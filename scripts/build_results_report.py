#!/usr/bin/env python3
"""
Aggregate results from 9 matrix jobs into final report.
"""

import csv
import json
from datetime import datetime
from pathlib import Path
import sys

def load_batch_results(results_dir):
    """Load all batch results from intermediate artifacts."""
    results = []
    for csv_file in sorted(results_dir.glob("*.csv")):
        with open(csv_file) as f:
            reader = csv.DictReader(f)
            results.extend(list(reader))
    return results

def build_deck_stats(batch_results):
    """Calculate aggregate stats for each deck."""
    stats = {}
    
    for result in batch_results:
        deck_a = result['deck_a']
        deck_b = result['deck_b']
        wins_a = int(result['wins_a'])
        wins_b = int(result['wins_b'])
        draws = int(result.get('draws', 0))
        unparsed = int(result.get('unparsed', 0))
        
        # Initialize deck if not seen
        for deck in [deck_a, deck_b]:
            if deck not in stats:
                stats[deck] = {
                    'games': 0,
                    'wins': 0,
                    'losses': 0,
                    'draws': 0,
                    'unparsed': 0,
                    'matchups': []
                }
        
        # Update deck_a stats
        stats[deck_a]['games'] += wins_a + wins_b + draws
        stats[deck_a]['wins'] += wins_a
        stats[deck_a]['losses'] += wins_b
        stats[deck_a]['draws'] += draws
        stats[deck_a]['unparsed'] += unparsed
        stats[deck_a]['matchups'].append({
            'opponent': deck_b,
            'wins': wins_a,
            'losses': wins_b,
            'draws': draws,
            'win_rate': wins_a / (wins_a + wins_b) if (wins_a + wins_b) > 0 else 0
        })
        
        # Update deck_b stats (reverse)
        stats[deck_b]['games'] += wins_a + wins_b + draws
        stats[deck_b]['wins'] += wins_b
        stats[deck_b]['losses'] += wins_a
        stats[deck_b]['draws'] += draws
        stats[deck_b]['unparsed'] += unparsed
        stats[deck_b]['matchups'].append({
            'opponent': deck_a,
            'wins': wins_b,
            'losses': wins_a,
            'draws': draws,
            'win_rate': wins_b / (wins_a + wins_b) if (wins_a + wins_b) > 0 else 0
        })
    
    return stats

def build_matchup_matrix(batch_results, deck_order):
    """Build 10x10 matchup matrix."""
    matrix = {}
    for result in batch_results:
        key = (result['deck_a'], result['deck_b'])
        wins_a = int(result['wins_a'])
        wins_b = int(result['wins_b'])
        win_rate = wins_a / (wins_a + wins_b) if (wins_a + wins_b) > 0 else 0.5
        matrix[key] = win_rate
    
    return matrix

def main():
    if len(sys.argv) < 2:
        print("Usage: build_results_report.py <results_dir>")
        return 1
    
    results_dir = Path(sys.argv[1])
    output_dir = results_dir
    
    print(f"Loading batch results from {results_dir}...")
    batch_results = load_batch_results(results_dir)
    
    if not batch_results:
        print("ERROR: No batch results found")
        return 1
    
    print(f"Loaded {len(batch_results)} batch results")
    
    # Build aggregates
    stats = build_deck_stats(batch_results)
    deck_order = sorted(stats.keys())
    matrix = build_matchup_matrix(batch_results, deck_order)
    
    # Write deck stats CSV
    with open(output_dir / "deck-stats.csv", "w") as f:
        writer = csv.DictWriter(f, fieldnames=['deck', 'games', 'wins', 'losses', 'draws', 'unparsed', 'win_rate'])
        writer.writeheader()
        for deck in deck_order:
            s = stats[deck]
            games = s['games']
            win_rate = s['wins'] / games if games > 0 else 0
            writer.writerow({
                'deck': deck,
                'games': games,
                'wins': s['wins'],
                'losses': s['losses'],
                'draws': s['draws'],
                'unparsed': s['unparsed'],
                'win_rate': f"{win_rate:.1%}"
            })
    
    # Write Markdown report
    with open(output_dir / "report.md", "w") as f:
        f.write("# Peasant+ 10-Deck Forge Round-Robin Baseline v1.0\n\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n\n")
        
        f.write("## Overall Deck Win Rates\n\n")
        f.write("| Deck | Games | Wins | Losses | Draws | Unparsed | Win Rate |\n")
        f.write("|------|-------|------|--------|-------|----------|----------|\n")
        for deck in deck_order:
            s = stats[deck]
            games = s['games']
            win_rate = s['wins'] / games if games > 0 else 0
            flag = " ⚠️" if not (0.45 <= win_rate <= 0.55) else ""
            f.write(f"| {deck} | {games} | {s['wins']} | {s['losses']} | {s['draws']} | {s['unparsed']} | {win_rate:.1%}{flag} |\n")
        
        f.write("\n## Balance Flags\n\n")
        flagged_decks = [d for d in deck_order if d in stats and not (0.45 <= stats[d]['wins'] / stats[d]['games'] <= 0.55)]
        if flagged_decks:
            f.write("Decks outside 45–55% win rate:\n")
            for deck in flagged_decks:
                s = stats[deck]
                win_rate = s['wins'] / s['games'] if s['games'] > 0 else 0
                f.write(f"  - {deck}: {win_rate:.1%}\n")
        else:
            f.write("No decks flagged outside 45–55% win rate.\n")
        
        f.write("\n## Matchup Matrix\n\n")
        f.write("| | " + " | ".join(deck_order) + " |\n")
        f.write("|" + "|" * (len(deck_order) + 1) + "\n")
        for row_deck in deck_order:
            f.write(f"| {row_deck} |")
            for col_deck in deck_order:
                if row_deck == col_deck:
                    f.write(" – |")
                else:
                    wr = matrix.get((row_deck, col_deck), 0.5)
                    flag = " ⚠️" if not (0.35 <= wr <= 0.65) else ""
                    f.write(f" {wr:.1%}{flag} |")
            f.write("\n")
        
        f.write("\n## Notes\n\n")
        f.write("- Forge AI results are more reliable for straightforward aggro/midrange play.\n")
        f.write("- Esper Control, Sultai Beans, Hunting Storm, and other decision-intensive decks are more sensitive to Forge AI quality.\n")
        f.write("- ⚠️ indicates decks outside 45–55% overall or matchups beyond 65–35.\n")
    
    print(f"Report written to {output_dir / 'report.md'}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
