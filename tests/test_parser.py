#!/usr/bin/env python3
"""
Unit tests for output parsing.
"""

import unittest
import sys
from pathlib import Path

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from timeless_forge.runner import parse_output

class TestParser(unittest.TestCase):
    
    def test_parse_standard_win(self):
        """Test parsing standard 'Winner: DeckName' output."""
        output = "\n".join([
            "Winner: deckA",
            "Winner: deckB",
            "Winner: deckA",
        ])
        wins_a, wins_b, draws, unparsed = parse_output(output, "deckA.dck", "deckB.dck", 3)
        self.assertEqual(wins_a, 2)
        self.assertEqual(wins_b, 1)
        self.assertEqual(draws, 0)
        self.assertEqual(unparsed, 0)
    
    def test_parse_with_draws(self):
        """Test parsing output with draws."""
        output = "\n".join([
            "Winner: deckA",
            "Game is a draw",
            "Winner: deckB",
        ])
        wins_a, wins_b, draws, unparsed = parse_output(output, "deckA.dck", "deckB.dck", 3)
        self.assertEqual(wins_a, 1)
        self.assertEqual(wins_b, 1)
        self.assertEqual(draws, 1)
        self.assertEqual(unparsed, 0)
    
    def test_parse_forge_output(self):
        """Test parsing Forge style 'Game Result: Game N ended in X ms. Ai(1)-Name has won!' output."""
        output = "\n".join([
            "Game Result: Game 1 ended in 123 ms. Ai(1)-White Weenie has won!",
            "Game Result: Game 2 ended in 456 ms. Ai(2)-Mono Blue Tempo has won!",
            "Game Result: Game 3 ended in 789 ms. Ai(1)-White Weenie has won!",
        ])
        wins_a, wins_b, draws, unparsed = parse_output(output, "01-white-weenie.dck", "02-mono-blue-tempo.dck", 3)
        self.assertEqual(wins_a, 2)
        self.assertEqual(wins_b, 1)
        self.assertEqual(draws, 0)
        self.assertEqual(unparsed, 0)

    def test_parse_with_unparsed(self):
        """Test tracking of unparsed games."""
        output = "\n".join([
            "Winner: deckA",
            "Some garbage output",
            "Winner: deckB",
        ])
        wins_a, wins_b, draws, unparsed = parse_output(output, "deckA.dck", "deckB.dck", 5)
        self.assertEqual(wins_a, 1)
        self.assertEqual(wins_b, 1)
        self.assertEqual(draws, 0)
        self.assertEqual(unparsed, 3)

if __name__ == '__main__':
    unittest.main()
