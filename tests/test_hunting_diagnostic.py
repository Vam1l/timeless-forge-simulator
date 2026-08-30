import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / "experimental" / "forge-ai" / "hunting-diagnostic" / "run_hunting_diagnostic.py"
spec = importlib.util.spec_from_file_location("hunting_diagnostic", MODULE)
hd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hd)


class HuntingDiagnosticRegressionTests(unittest.TestCase):
    def test_exile_mention_is_not_cast_or_opportunity(self):
        text = "Zone Change: Exile [Hunting Pack, Chromatic Sphere]\nResolve Stack: Glimpse the Impossible moves Hunting Pack to Graveyard"
        status, opportunity, cast, payoff = hd.classify_game(text, [])
        self.assertFalse(opportunity)
        self.assertIsNone(cast)
        self.assertFalse(payoff)
        self.assertEqual("no reachable opportunity in game", status)

    def test_chromatic_sphere_activity_does_not_prove_pack_castable(self):
        text = "Add To Stack: Ai(1)-Hunting Storm cast Chromatic Sphere\nMana: Chromatic Sphere (1) - Sacrifice Chromatic Sphere: Add one mana of any color"
        status, opportunity, cast, payoff = hd.classify_game(text, [])
        self.assertFalse(opportunity)
        self.assertIsNone(cast)
        self.assertFalse(payoff)

    def test_no_exception_does_not_prove_byte_integer_path_or_pack_opportunity(self):
        text = "Game Result: Game 1 ended in 100 ms. Ai(1)-Hunting Storm has won!"
        status, opportunity, cast, payoff = hd.classify_game(text, [])
        self.assertFalse(opportunity)
        self.assertIsNone(cast)
        self.assertFalse(payoff)

    def test_pack_cast_requires_explicit_stack_event(self):
        text = "Hunting Pack is in Exile\nHunting Pack moves to Graveyard"
        self.assertIsNone(hd.PACK_CAST.search(text))
        text2 = "Add To Stack: Ai(1)-Hunting Storm cast Hunting Pack (42)."
        self.assertIsNotNone(hd.PACK_CAST.search(text2))

    def test_payoff_requires_storm_and_token_evidence(self):
        diag = [
            {"event": "cost_check", "decision": "payable"},
            {"event": "final_decision", "decision": "WillPlay"},
        ]
        cast_only = "Add To Stack: Ai(1)-Hunting Storm cast Hunting Pack (42)."
        status, opportunity, cast, payoff = hd.classify_game(cast_only, diag)
        self.assertTrue(opportunity)
        self.assertIsNotNone(cast)
        self.assertFalse(payoff)
        full = cast_only + "\nResolve Stack: Storm [Card: Hunting Pack]\nToken: create 2/2 green Bear Token"
        status, opportunity, cast, payoff = hd.classify_game(full, diag)
        self.assertTrue(opportunity)
        self.assertTrue(payoff)


if __name__ == "__main__":
    unittest.main()
