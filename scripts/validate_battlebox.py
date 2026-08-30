#!/usr/bin/env python3
"""
Validate all decks in the battlebox are exactly 60 main-deck cards.
"""

import json
import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from timeless_forge.deck import load_deck, validate_deck

def main():
    deck_dir = repo_root / "battlebox" / "decks"
    deck_files = sorted(deck_dir.glob("*.dck"))

    if len(deck_files) != 10:
        print(f"ERROR: Expected 10 .dck files, found {len(deck_files)}")
        return 1

    all_valid = True
    total_decks = 0

    for deck_file in deck_files:
        total_decks += 1
        deck = load_deck(deck_file)
        errors = validate_deck(deck)

        # Enforce exactly 60 cards for baseline
        if deck.main_count != 60:
            errors.append(f"main deck has {deck.main_count} cards; exactly 60 required for baseline")

        if errors:
            print(f"FAIL {deck_file.name}")
            for error in errors:
                print(f"  {error}")
            all_valid = False
        else:
            print(f"OK   {deck_file.name} ({deck.main_count} main, {deck.sideboard_count} sideboard)")

    config = json.loads((repo_root / "battlebox" / "roundrobin.json").read_text(encoding="utf-8"))
    matchups = config.get("matchups", [])
    expected_names = {path.name for path in deck_files}
    oriented_pairs = [(matchup.get("deck_a"), matchup.get("deck_b")) for matchup in matchups]
    unordered_pairs = {tuple(sorted(pair)) for pair in oriented_pairs}

    if len(oriented_pairs) != 90 or len(set(oriented_pairs)) != 90:
        print(f"FAIL roundrobin.json: expected 90 unique orientations, found {len(set(oriented_pairs))}")
        all_valid = False
    if len(unordered_pairs) != 45:
        print(f"FAIL roundrobin.json: expected 45 unordered matchups, found {len(unordered_pairs)}")
        all_valid = False
    if any(a not in expected_names or b not in expected_names or a == b for a, b in oriented_pairs):
        print("FAIL roundrobin.json: invalid, missing, or self-paired deck reference")
        all_valid = False

    print(
        f"\nValidation complete: {total_decks} decks, {len(oriented_pairs)} orientations, "
        f"{'all valid' if all_valid else 'ERRORS FOUND'}"
    )
    return 0 if all_valid else 1

if __name__ == "__main__":
    sys.exit(main())
