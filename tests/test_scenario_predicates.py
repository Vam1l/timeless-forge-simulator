import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "experimental" / "forge-ai" / "run_scenarios.py"
spec = importlib.util.spec_from_file_location("run_scenarios", MODULE_PATH)
rs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rs)

# Exact run #3 hunting-73002 evidence that caused the prior false positives.
GLIMPSE_END_STEP = '''Resolve Stack: At the beginning of the next end step, if any of those cards remain exiled, put them into your graveyard, then create a 0/1 colorless Eldrazi Spawn creature token for each card put into your graveyard this way. Those tokens have "Sacrifice this creature: Add {C}." ([Geothermal Crevice (29), Chromatic Sphere (10), Hunting Pack (21)]) [Phase: Ai(1)-Hunting Storm]'''
RUN3_73002 = "\n".join([
    "Add To Stack: Ai(1)-Hunting Storm cast Chromatic Star",
    "Resolve Stack: Chromatic Star",
    "Zone Change: Chromatic Star (6) was put into Graveyard from Battlefield.",
    "Add To Stack: Ai(1)-Hunting Storm cast Deadly Dispute",
    "Resolve Stack: When Bitter Reunion enters, you may discard a card. If you do, draw two cards.",
    "Add To Stack: Ai(1)-Hunting Storm cast Glimpse the Impossible",
    "Add To Stack: Ai(1)-Hunting Storm cast Chromatic Sphere",
    "Resolve Stack: Chromatic Sphere",
    GLIMPSE_END_STEP,
])

class ScenarioPredicateRegressionTests(unittest.TestCase):
    def test_glimpse_line_cannot_be_hunting_pack_cast_or_payoff(self):
        self.assertEqual("failed", rs.pack_recognition(RUN3_73002)[0])
        self.assertEqual("failed", rs.pack_payoff(RUN3_73002)[0])

    def test_glimpse_line_cannot_be_filter_activation(self):
        self.assertEqual("failed", rs.exact_filter_activation(RUN3_73002)[0])

    def test_bitter_reunion_without_named_discard_is_not_preservation(self):
        self.assertEqual("unobservable", rs.pack_preservation(RUN3_73002)[0])

    def test_completed_artifact_game_cannot_prove_byte_integer_path(self):
        self.assertEqual("unobservable", rs.byte_integer_path(RUN3_73002)[0])

    def test_exact_mana_event_is_filter_activation(self):
        text = "Mana: Chromatic Star (6) - {1}, {T}, Sacrifice Chromatic Star: Add one mana of any color."
        self.assertEqual("demonstrated", rs.exact_filter_activation(text)[0])

if __name__ == "__main__":
    unittest.main()
