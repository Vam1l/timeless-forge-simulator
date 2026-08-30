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
        self.assertFalse(opportunity); self.assertIsNone(cast); self.assertFalse(payoff)

    def test_chromatic_sphere_activity_does_not_prove_pack_castable(self):
        text = "Add To Stack: Ai(1)-Hunting Storm cast Chromatic Sphere\nMana: Chromatic Sphere (1) - Sacrifice Chromatic Sphere: Add one mana of any color"
        status, opportunity, cast, payoff = hd.classify_game(text, [])
        self.assertFalse(opportunity); self.assertIsNone(cast); self.assertFalse(payoff)

    def test_no_exception_does_not_prove_opportunity(self):
        text = "Game Result: Game 1 ended in 100 ms. Ai(1)-Hunting Storm has won!"
        status, opportunity, cast, payoff = hd.classify_game(text, [])
        self.assertFalse(opportunity); self.assertIsNone(cast); self.assertFalse(payoff)

    def test_pack_cast_requires_explicit_stack_event_and_accepts_either_seat(self):
        self.assertIsNone(hd.PACK_CAST.search("Hunting Pack is in Exile\nHunting Pack moves to Graveyard"))
        self.assertIsNotNone(hd.PACK_CAST.search("Add To Stack: Ai(1)-Hunting Storm cast Hunting Pack (42)."))
        self.assertIsNotNone(hd.PACK_CAST.search("Add To Stack: Ai(2)-Hunting Storm cast Hunting Pack"))

    def test_payoff_requires_storm_and_beast_resolution(self):
        diag=[{"event":"evaluate","turn":"12","phase":"MAIN1","active_player":"Ai(2)-Hunting Storm","hunting_pack_zone":"Ai(2)-Hunting Storm's Exile","mana_cost_payable":"true"},{"event":"ai_evaluation","turn":"12","phase":"MAIN1","decision":"WillPlay"},{"event":"cost_check","turn":"12","phase":"MAIN1","decision":"payable"},{"event":"final_decision","turn":"12","phase":"MAIN1","decision":"WillPlay"}]
        cast_only="Add To Stack: Ai(2)-Hunting Storm cast Hunting Pack"
        status, opportunity, cast, payoff=hd.classify_game(cast_only,diag)
        self.assertTrue(opportunity); self.assertEqual("repair demonstrated",status); self.assertFalse(payoff)
        full=cast_only+"\nResolve Stack: Storm [Card: Hunting Pack]\nResolve Stack: Hunting Pack (151) - Ai(2)-Hunting Storm creates a 4/4 green Beast creature token."
        status, opportunity, cast, payoff=hd.classify_game(full,diag)
        self.assertTrue(payoff)

    def test_decline_of_qualified_own_main_opportunity_is_failure(self):
        diag=[{"event":"evaluate","turn":"7","phase":"MAIN1","active_player":"Ai(1)-Hunting Storm","hunting_pack_zone":"Ai(1)-Hunting Storm's Hand","mana_cost_payable":"true"},{"event":"ai_evaluation","turn":"7","phase":"MAIN1","decision":"CantPlayAi"}]
        status, opportunity, cast, payoff=hd.classify_game("",diag)
        self.assertTrue(opportunity); self.assertEqual("repair failed",status)


if __name__ == "__main__": unittest.main()
