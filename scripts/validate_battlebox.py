#!/usr/bin/env python3
"""
Validate all decks in the battlebox are exactly 60 main-deck cards.
"""

import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from timeless_forge.deck import load_deck, validate_deck

def main():
    deck_dir = repo_root / "battlebox" / "decks"
    deck_files = sorted(deck_dir.glob("*.dck"))
    
    if not deck_files:
        print("ERROR: No .dck files found in battlebox/decks/")
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
    
    print(f"\nValidation complete: {total_decks} decks, {'all valid' if all_valid else 'ERRORS FOUND'}")
    return 0 if all_valid else 1

if __name__ == "__main__":
    sys.exit(main())
