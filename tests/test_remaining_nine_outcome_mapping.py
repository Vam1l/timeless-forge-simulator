import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experimental" / "forge-ai" / "remaining-nine" / "run_validation_entry.py"
spec = importlib.util.spec_from_file_location("remaining_nine_entry", SCRIPT)
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)


class RemainingNineOutcomeMappingTests(unittest.TestCase):
    def test_display_name_winner_maps_to_target(self):
        self.assertEqual("win", entry.result_for_target("tron", "10-tron.dck", "01-white-weenie.dck", "Ai(1)-Tron"))
        self.assertEqual("loss", entry.result_for_target("tron", "10-tron.dck", "01-white-weenie.dck", "Ai(2)-White Weenie"))
        self.assertEqual("win", entry.result_for_target("esper", "07-esper-control.dck", "05-blue-terror.dck", "Ai(1)-Esper Control"))

    def test_explicit_draw_is_parsed(self):
        text = "Turn 1\nGame Result: Game 1 ended in 1234 ms. The game was a draw.\n"
        self.assertEqual("DRAW", entry.parsed_winner(text))
        self.assertEqual("draw", entry.result_for_target("white", "01-white-weenie.dck", "06-jund-wildfire.dck", "DRAW"))

    def test_unknown_winner_stays_unparsed(self):
        self.assertEqual("unparsed", entry.result_for_target("white", "01-white-weenie.dck", "06-jund-wildfire.dck", "Ai(1)-Unknown Deck"))


if __name__ == "__main__":
    unittest.main()
