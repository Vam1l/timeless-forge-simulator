#!/usr/bin/env python3
"""
Unit tests for deck validation.
"""

import unittest
from pathlib import Path
import sys
import tempfile

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from timeless_forge.deck import load_deck, validate_deck, Deck, write_deck

class TestDeckValidation(unittest.TestCase):

    def test_validate_60_card_main(self):
        """Test that a valid 60-card deck passes validation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dck', delete=False) as f:
            f.write("[Main]\n")
            for i in range(60):
                f.write(f"1 Card{i}\n")
            f.flush()
            deck = load_deck(f.name)
            errors = validate_deck(deck)
            self.assertEqual(len(errors), 0, f"Valid 60-card deck should not have errors: {errors}")
            Path(f.name).unlink()

    def test_reject_too_few_cards(self):
        """Test that a deck with fewer than 60 cards is rejected."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dck', delete=False) as f:
            f.write("[Main]\n")
            for i in range(50):
                f.write(f"1 Card{i}\n")
            f.flush()
            deck = load_deck(f.name)
            errors = validate_deck(deck)
            self.assertTrue(any('60' in e for e in errors), f"Expected '60' in errors: {errors}")
            Path(f.name).unlink()

    def test_reject_sideboard_too_large(self):
        """Test that a sideboard larger than 15 is rejected."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dck', delete=False) as f:
            f.write("[Main]\n")
            for i in range(60):
                f.write(f"1 Card{i}\n")
            f.write("[Sideboard]\n")
            for i in range(16):
                f.write(f"1 SBCard{i}\n")
            f.flush()
            deck = load_deck(f.name)
            errors = validate_deck(deck)
            self.assertTrue(any('sideboard' in e.lower() for e in errors), f"Expected sideboard error: {errors}")
            Path(f.name).unlink()

if __name__ == '__main__':
    unittest.main()
