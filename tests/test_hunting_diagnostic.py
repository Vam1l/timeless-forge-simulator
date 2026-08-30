import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / "experimental" / "forge-ai" / "hunting-diagnostic" / "run_hunting_diagnostic.py"
spec = importlib.util.spec_from_file_location("hunting_diagnostic", MODULE)
hd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hd)


def qualified_diag(decision="WillPlay"):
    return [
        {"event":"evaluate","turn":"12","phase":"MAIN1","active_player":"Ai(2)-Hunting Storm","hunting_pack_zone":"Ai(2)-Hunting Storm's Hand","visible_to_ai":"true","priority_window":"true","zone_playable":"true","timing_legal":"true","legal_after_stack":"true","restrictions_legal":"true","engine_legal":"true","payable_cost":"Cost: 5 G G","mana_cost_payable":"true","two_green_requirement":"2","two_green_satisfied":"true"},
        {"event":"ai_evaluation","turn":"12","phase":"MAIN1","decision":decision},
        {"event":"cost_check","turn":"12","phase":"MAIN1","decision":"payable"},
        {"event":"final_decision","turn":"12","phase":"MAIN1","decision":"WillPlay"},
    ]


class HuntingDiagnosticRegressionTests(unittest.TestCase):
    def test_glimpse_exile_list_is_not_opportunity_or_cast(self):
        text="Zone Change: Exile [Hunting Pack, Chromatic Sphere]\nResolve Stack: Glimpse the Impossible moves Hunting Pack to Graveyard"
        status,opp,cast,payoff,_,_=hd.classify_game(text,[])
        self.assertFalse(opp); self.assertIsNone(cast); self.assertFalse(payoff)

    def test_exile_to_graveyard_is_not_payoff(self):
        text="Hunting Pack is in Exile\nResolve Stack: Glimpse the Impossible moves Hunting Pack to Graveyard"
        self.assertIsNone(hd.PACK_CAST.search(text)); self.assertIsNone(hd.PACK_TOKEN.search(text))

    def test_casting_chromatic_artifact_is_not_filter_activation(self):
        self.assertIsNone(hd.FILTER_MANA.search("Add To Stack: Ai(1)-Hunting Storm cast Chromatic Sphere"))
        self.assertIsNone(hd.FILTER_MANA.search("Add To Stack: Ai(1)-Hunting Storm cast Chromatic Star"))

    def test_deadly_dispute_sacrifice_is_not_filter_activation(self):
        text="Sacrifice: Ai(1)-Hunting Storm sacrifices Chromatic Star to cast Deadly Dispute"
        self.assertIsNone(hd.FILTER_MANA.search(text))

    def test_filter_requires_explicit_mana_ability(self):
        text="Mana: Chromatic Sphere (1) - T, Sacrifice Chromatic Sphere: Add one mana of any color"
        self.assertIsNotNone(hd.FILTER_MANA.search(text))

    def test_no_class_cast_exception_does_not_prove_numeric_path_or_opportunity(self):
        text="Game Result: Game 1 ended in 100 ms. Ai(1)-Hunting Storm has won!"
        status,opp,cast,payoff,_,_=hd.classify_game(text,[])
        self.assertFalse(opp); self.assertIsNone(cast); self.assertFalse(payoff)

    def test_pack_cast_requires_explicit_stack_event_either_seat(self):
        self.assertIsNone(hd.PACK_CAST.search("Hunting Pack moves to Graveyard"))
        self.assertIsNotNone(hd.PACK_CAST.search("Add To Stack: Ai(1)-Hunting Storm cast Hunting Pack (42)."))
        self.assertIsNotNone(hd.PACK_CAST.search("Add To Stack: Ai(2)-Hunting Storm cast Hunting Pack"))

    def test_payoff_requires_storm_and_beast_resolution(self):
        diag=qualified_diag()
        cast="Add To Stack: Ai(2)-Hunting Storm cast Hunting Pack"
        status,opp,_,payoff,_,_=hd.classify_game(cast,diag)
        self.assertTrue(opp); self.assertEqual("repair demonstrated",status); self.assertFalse(payoff)
        full=cast+"\nResolve Stack: Storm [Card: Hunting Pack]\nResolve Stack: Hunting Pack (151) - Ai(2)-Hunting Storm creates a 4/4 green Beast creature token."
        status,opp,_,payoff,_,_=hd.classify_game(full,diag)
        self.assertTrue(payoff)

    def test_missing_any_legality_predicate_disqualifies_opportunity(self):
        for key in ("priority_window","zone_playable","timing_legal","restrictions_legal","engine_legal","mana_cost_payable","two_green_satisfied"):
            diag=qualified_diag(); diag[0][key]="false"
            self.assertEqual([],hd.legal_opportunities(diag),key)

    def test_ai_rejection_of_fully_qualified_state_is_failure(self):
        diag=qualified_diag("CantPlayAi")
        status,opp,cast,payoff,rejection,_=hd.classify_game("",diag)
        self.assertTrue(opp); self.assertEqual("repair failed",status); self.assertEqual("CantPlayAi",rejection)


if __name__ == "__main__": unittest.main()
