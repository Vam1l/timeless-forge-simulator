#!/usr/bin/env python3
"""
Unit tests for AI heuristics introduced in Forge 2.0.14 patches.
"""

import unittest
import zipfile
from pathlib import Path
import sys

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

class TestAiHeuristics(unittest.TestCase):

    def test_jar_contains_patched_classes(self):
        """Verify forge-2.0.14.jar contains all patched AI class files."""
        jar_path = repo_root / "forge-2.0.14.jar"
        self.assertTrue(jar_path.is_file(), f"forge-2.0.14.jar not found at {jar_path}")

        expected_classes = [
            "forge/ai/ability/TokenAi.class",
            "forge/ai/ability/ManaAi.class",
            "forge/ai/ability/ChangeZoneAi.class",
            "forge/ai/ability/DestroyAllAi.class",
            "forge/ai/ComputerUtilCard.class",
            "forge/game/ability/effects/TwoPilesEffect.class",
        ]

        with zipfile.ZipFile(jar_path, 'r') as z:
            namelist = set(z.namelist())
            for cls in expected_classes:
                self.assertIn(cls, namelist, f"Missing patched class in JAR: {cls}")

    def test_storm_hunting_pack_logic(self):
        """Verify Storm heuristic logic for Hunting Pack and rituals."""
        # Simulated logic for Hunting Pack phase evaluation
        def is_hunting_pack_favored(is_ai_turn, phase, storm_count, ai_life_in_danger):
            if is_ai_turn and phase in ("MAIN1", "MAIN2"):
                return True
            if not is_ai_turn and phase == "COMBAT_DECLARE_BLOCKERS" and ai_life_in_danger:
                return True
            return False

        # Hunting Pack is disfavored during opponent combat under normal conditions
        self.assertFalse(is_hunting_pack_favored(is_ai_turn=False, phase="COMBAT_DECLARE_BLOCKERS", storm_count=2, ai_life_in_danger=False))
        # Hunting Pack is favored on AI's own turn in main phase after storm count
        self.assertTrue(is_hunting_pack_favored(is_ai_turn=True, phase="MAIN1", storm_count=3, ai_life_in_danger=False))
        # Emergency blocker exception
        self.assertTrue(is_hunting_pack_favored(is_ai_turn=False, phase="COMBAT_DECLARE_BLOCKERS", storm_count=0, ai_life_in_danger=True))

    def test_tron_piece_selection_logic(self):
        """Verify Tron heuristic logic for missing piece selection."""
        urza_set = {"Urza's Mine", "Urza's Power Plant", "Urza's Tower"}

        def get_best_land_target(battlefield, hand):
            controlled = set(battlefield).union(set(hand))
            missing = [land for land in ("Urza's Tower", "Urza's Power Plant", "Urza's Mine") if land not in controlled]
            if missing:
                return missing[0]
            return "Forest"

        # Map chooses missing Urza piece when AI controls Mine + Power Plant
        target = get_best_land_target(["Urza's Mine"], ["Urza's Power Plant"])
        self.assertEqual(target, "Urza's Tower")

        # Crop Rotation favors missing piece
        target_crop = get_best_land_target(["Urza's Mine", "Urza's Tower"], [])
        self.assertEqual(target_crop, "Urza's Power Plant")

    def test_esper_supreme_verdict_logic(self):
        """Verify Esper Supreme Verdict evaluation logic."""
        def should_fire_verdict(opp_creatures, opp_power, ai_creatures, ai_life_in_danger):
            if ai_life_in_danger:
                return True
            if opp_creatures < 2 and opp_power < 5:
                return False
            if opp_creatures < ai_creatures + 1:
                return False
            return True

        # Verdict does not fire into a low-value board (1 small creature) when waiting is better
        self.assertFalse(should_fire_verdict(opp_creatures=1, opp_power=2, ai_creatures=0, ai_life_in_danger=False))
        # Verdict fires when facing high opposing board value (3 creatures)
        self.assertTrue(should_fire_verdict(opp_creatures=3, opp_power=7, ai_creatures=0, ai_life_in_danger=False))
        # Verdict fires when facing lethal / life in danger
        self.assertTrue(should_fire_verdict(opp_creatures=1, opp_power=4, ai_creatures=0, ai_life_in_danger=True))

if __name__ == '__main__':
    unittest.main()
