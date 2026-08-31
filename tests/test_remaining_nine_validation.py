import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experimental" / "forge-ai" / "remaining-nine" / "run_validation.py"
spec = importlib.util.spec_from_file_location("remaining_nine_validation", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class RemainingNineValidationTests(unittest.TestCase):
    def test_exact_game_matrix(self):
        self.assertEqual(26, len(mod.CONDITIONS))
        self.assertEqual(6, sum(1 for c in mod.CONDITIONS if c[0] == "tron"))
        self.assertEqual(6, sum(1 for c in mod.CONDITIONS if c[0] == "esper"))
        self.assertEqual(14, sum(1 for c in mod.CONDITIONS if c[0] == "audit"))
        self.assertEqual(52, len(mod.CONDITIONS) * 2)

    def test_hunting_storm_is_absent(self):
        for condition in mod.CONDITIONS:
            self.assertFalse(any("09-hunting-storm" in str(value) for value in condition))
        self.assertNotIn("hunting", mod.DECKS)

    def test_filter_requires_explicit_mana_event(self):
        text = "\n".join([
            "Add To Stack: Ai(1)-Tron cast Chromatic Star",
            "Ai(1)-Tron sacrifices Chromatic Star to Deadly Dispute",
            "Mana: Ai(1)-Tron activates Chromatic Sphere — Sacrifice Chromatic Sphere: Add one mana of any color",
        ])
        events = mod.explicit_filter_activations(text)
        self.assertEqual(1, len(events))
        self.assertIn("Mana:", events[0])
        self.assertIn("Chromatic Sphere", events[0])

    def test_game_start_and_result_parsing(self):
        text = "Turn 1\nGame Result: Game 1 ended in 1234 ms. Ai(1)-White Weenie has won!\n"
        self.assertTrue(mod.game_started(text))
        self.assertEqual("Ai(1)-White Weenie", mod.winner(text))
        self.assertEqual(1234, mod.game_duration_ms(text))

    def test_runtime_failure_markers(self):
        text = "Turn 1\njava.lang.ClassCastException: Byte cannot be cast to Integer\n"
        issues = mod.runtime_issues(1, text)
        self.assertIn("byte_integer_or_numeric_map_failure", issues)
        self.assertIn("exception_or_stack_trace", issues)
        self.assertIn("unparsed_game", issues)

    def test_repeated_loop_detector_is_conservative(self):
        normal = "\n".join(f"Ai(1)-Deck cast Spell {i}" for i in range(25))
        loop = "\n".join(["Ai(1)-Deck activates Something"] * 20)
        self.assertFalse(mod.repeated_loop(normal))
        self.assertTrue(mod.repeated_loop(loop))


if __name__ == "__main__":
    unittest.main()
