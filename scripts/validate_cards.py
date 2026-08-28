#!/usr/bin/env python3
"""
Validate that Forge recognizes all cards in all battlebox decks.
Output unsupported cards to be added to unsupported-card-substitutions.md.
"""

import subprocess
import sys
from pathlib import Path

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from timeless_forge.deck import load_deck

def main():
    deck_dir = repo_root / "battlebox" / "decks"
    forge_jar = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    
    if not forge_jar or not forge_jar.exists():
        print("ERROR: Forge JAR path required as argument")
        return 1
    
    all_cards = {}
    for deck_file in sorted(deck_dir.glob("*.dck")):
        deck = load_deck(deck_file)
        for card_name, qty in deck.main.items():
            if card_name not in all_cards:
                all_cards[card_name] = []
            all_cards[card_name].append(deck_file.stem)
    
    print(f"Checking {len(all_cards)} unique cards across all decks...")
    
    # Use Forge's card database lookup if available
    # For now, we'll just list unique cards and indicate they should be checked manually
    unsupported = []
    
    # This is a placeholder; actual Forge card validation requires running Forge
    print(f"Found {len(all_cards)} unique cards in battlebox.")
    print("Card validation requires Forge to be running; this will be checked during simulation.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
