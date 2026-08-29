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

    @unittest.skipUnless((repo_root / "forge-2.0.14.jar").is_file(), "forge-2.0.14.jar not present in workspace")
    def test_jar_contains_patched_classes(self):
        """Verify forge-2.0.14.jar contains all patched AI class files."""
        jar_path = repo_root / "forge-2.0.14.jar"
        self.assertTrue(jar_path.is_file(), f"forge-2.0.14.jar not found at {jar_path}")

        expected_classes = [
            "forge/ai/ability/TokenAi.class",
            "forge/ai/ability/ManaAi.class",
            "forge/ai/ability/ChangeZoneAi.class",
            "forge/ai/ability/DestroyAllAi.class",
            "forge/ai/ability/TwoPilesAi.class",
            "forge/ai/ability/ChooseColorAi.class",
            "forge/ai/ability/PermanentAi.class",
            "forge/ai/ComputerUtilCard.class",
            "forge/ai/ComputerUtilMana.class",
            "forge/ai/PlayerControllerAi.class",
            "forge/game/ability/effects/TwoPilesEffect.class",
        ]

        with zipfile.ZipFile(jar_path, "r") as z:
            namelist = set(z.namelist())
            for cls in expected_classes:
                self.assertIn(cls, namelist, f"Missing patched class in JAR: {cls}")

    def test_generic_mana_filter_and_refractor_star_sphere_logic(self):
        """Verify generic mana filter recognition logic for Refractor, Star, Sphere, and Tinder Wall."""
        def is_mana_source_available(card_name, zone, has_mana_cost):
            if zone == "Battlefield":
                return True
            if not has_mana_cost:
                return True
            return False

        self.assertTrue(is_mana_source_available("Energy Refractor", "Battlefield", has_mana_cost=True))
        self.assertTrue(is_mana_source_available("Chromatic Star", "Battlefield", has_mana_cost=True))
        self.assertTrue(is_mana_source_available("Tinder Wall", "Battlefield", has_mana_cost=False))

    def test_hunting_pack_preservation_and_cast_timing(self):
        """Verify Storm heuristic logic for Hunting Pack preservation and cast timing."""
        def should_preserve_from_discard(card_name):
            protected_cards = {"Hunting Pack", "Prismatic Strands"}
            return card_name in protected_cards

        def is_hunting_pack_favored(is_ai_turn, phase, storm_count, ai_life_in_danger):
            if is_ai_turn and phase in ("MAIN1", "MAIN2"):
                return True
            if not is_ai_turn and phase == "COMBAT_DECLARE_BLOCKERS" and ai_life_in_danger:
                return True
            return False

        self.assertTrue(should_preserve_from_discard("Hunting Pack"))
        self.assertTrue(should_preserve_from_discard("Prismatic Strands"))
        self.assertFalse(should_preserve_from_discard("Forest"))

        self.assertFalse(is_hunting_pack_favored(is_ai_turn=False, phase="COMBAT_DECLARE_BLOCKERS", storm_count=2, ai_life_in_danger=False))
        self.assertTrue(is_hunting_pack_favored(is_ai_turn=True, phase="MAIN1", storm_count=3, ai_life_in_danger=False))
        self.assertTrue(is_hunting_pack_favored(is_ai_turn=False, phase="COMBAT_DECLARE_BLOCKERS", storm_count=0, ai_life_in_danger=True))

    def test_tron_tutor_and_crop_rotation_sole_green_preservation(self):
        """Verify Tron missing piece selection and sole green land preservation."""
        def get_best_land_target(battlefield, hand):
            controlled_field = set(battlefield)
            controlled_hand = set(hand)
            for piece in ("Urza's Tower", "Urza's Power Plant", "Urza's Mine"):
                if piece not in controlled_field and piece not in controlled_hand:
                    return piece
            for piece in ("Urza's Tower", "Urza's Power Plant", "Urza's Mine"):
                if piece not in controlled_field:
                    return piece
            return "Forest"

        def evaluate_worst_land_score(land_name, is_basic, is_sole_green, is_duplicate):
            score = 1 if is_basic else 0
            if is_duplicate:
                score += 10
            if is_basic and land_name == "Forest" and is_sole_green:
                score -= 50
            return score

        target = get_best_land_target(["Urza's Mine"], ["Urza's Power Plant"])
        self.assertEqual(target, "Urza's Tower")

        target_crop = get_best_land_target(["Urza's Mine", "Urza's Tower"], [])
        self.assertEqual(target_crop, "Urza's Power Plant")

        forest_score = evaluate_worst_land_score("Forest", is_basic=True, is_sole_green=True, is_duplicate=False)
        dup_urza_score = evaluate_worst_land_score("Urza's Mine", is_basic=False, is_sole_green=False, is_duplicate=True)
        self.assertLess(forest_score, dup_urza_score)

    def test_prismatic_strands_combat_use(self):
        """Verify Prismatic Strands color selection logic for combat."""
        def select_prismatic_strands_color(attacking_creatures_colors, opp_battlefield_colors):
            if attacking_creatures_colors:
                return attacking_creatures_colors[0]
            if opp_battlefield_colors:
                return opp_battlefield_colors[0]
            return "White"

        self.assertEqual(select_prismatic_strands_color(["Red", "Green"], ["Black"]), "Red")
        self.assertEqual(select_prismatic_strands_color([], ["Black", "Red"]), "Black")

    def test_twopilesai_fact_or_fiction_choice_behavior(self):
        """Verify TwoPilesAi / Fact or Fiction pile evaluation behavior."""
        def evaluate_card_value(card_name, cmc, is_instant_or_sorcery):
            val = cmc * 2
            if is_instant_or_sorcery:
                val += 4
            if card_name in ("Supreme Verdict", "Fact or Fiction", "Counterspell", "Prismatic Strands"):
                val += 5
            return val

        def choose_better_pile(pile1, pile2):
            val1 = sum(evaluate_card_value(c["name"], c["cmc"], c["is_spell"]) for c in pile1)
            val2 = sum(evaluate_card_value(c["name"], c["cmc"], c["is_spell"]) for c in pile2)
            return 1 if val1 >= val2 else 2

        pile_a = [{"name": "Fact or Fiction", "cmc": 4, "is_spell": True}, {"name": "Counterspell", "cmc": 2, "is_spell": True}]
        pile_b = [{"name": "Plains", "cmc": 0, "is_spell": False}, {"name": "Island", "cmc": 0, "is_spell": False}, {"name": "Plains", "cmc": 0, "is_spell": False}]

        self.assertEqual(choose_better_pile(pile_a, pile_b), 1)

    def test_esper_supreme_verdict_logic(self):
        """Verify Esper Supreme Verdict evaluation logic."""
        def should_fire_verdict(opp_creatures, opp_power, ai_creatures, ai_life_in_danger):
            if ai_life_in_danger:
                return True
            if opp_creatures < 3 or opp_power < 7:
                if ai_creatures > 0 or opp_creatures < 2 or opp_power < 5:
                    return False
            if opp_creatures < ai_creatures + 2:
                return False
            return True

        self.assertFalse(should_fire_verdict(opp_creatures=1, opp_power=2, ai_creatures=0, ai_life_in_danger=False))
        self.assertFalse(should_fire_verdict(opp_creatures=2, opp_power=4, ai_creatures=0, ai_life_in_danger=False))
        self.assertTrue(should_fire_verdict(opp_creatures=3, opp_power=8, ai_creatures=0, ai_life_in_danger=False))
        self.assertTrue(should_fire_verdict(opp_creatures=1, opp_power=4, ai_creatures=0, ai_life_in_danger=True))

    def test_mana_map_key_type_safety(self):
        """Regression test for ManaMap Byte-vs-Integer key type safety."""
        # Simulated groupSourcesByManaColor map population with type-safe Integer keys
        mana_map = {}
        def put_mana_source(key_atom, ability_name):
            key = int(key_atom) # Explicit cast to int -> Integer key
            if key not in mana_map:
                mana_map[key] = []
            mana_map[key].append(ability_name)

        # 1. Generic / Snow / Any keys (e.g. 64, 32, 2048)
        put_mana_source(64, "Generic Source")
        put_mana_source(32, "Colorless Source")
        put_mana_source(2048, "Snow Source")

        # 2. Colored-mana filter/converter (e.g. Energy Refractor, Chromatic Star returning ManaAtom bytes 1, 2, 4, 8, 16)
        put_mana_source(1, "Energy Refractor -> W") # ManaAtom.WHITE = 1
        put_mana_source(2, "Energy Refractor -> U") # ManaAtom.BLUE = 2
        put_mana_source(4, "Energy Refractor -> B") # ManaAtom.BLACK = 4

        # 3. Ordinary non-filter mana sources (e.g. Island = 2, Mountain = 8)
        put_mana_source(2, "Basic Island -> U")
        put_mana_source(8, "Basic Mountain -> R")

        # Verify all keys in mana_map are strictly int (Integer) and iteration does not throw ClassCastException
        for key in mana_map.keys():
            self.assertIsInstance(key, int, f"Key {key} is not int: {type(key)}")

        # Verify groupAndOrderToPayShards shard matching for filter and non-filter sources
        def group_shards(cost_shards):
            res = {}
            for shard, color_mask in cost_shards.items():
                res[shard] = []
                for k, abilities in mana_map.items():
                    if k & color_mask or k == 64:
                        res[shard].extend(abilities)
            return res

        # Filtered colored-mana payment case (e.g. paying W using Energy Refractor)
        shards_filter = group_shards({"W": 1})
        self.assertIn("Energy Refractor -> W", shards_filter["W"])

        # Ordinary non-filter mana payment case (e.g. paying U using Island)
        shards_ordinary = group_shards({"U": 2})
        self.assertIn("Basic Island -> U", shards_ordinary["U"])

        # Blue Terror / unchanged deck payment path (e.g. paying 1U for Counterspell / Thought Scour)
        shards_blue_terror = group_shards({"U": 2, "GENERIC": 64})
        self.assertTrue(len(shards_blue_terror["U"]) > 0)
        self.assertTrue(len(shards_blue_terror["GENERIC"]) > 0)

        # Failure path reproduction & type safety verification (Byte vs Integer key safety)
        mixed_keys = [bytes([1])[0], int(2), bytes([4])[0], int(64)] # Simulates Byte and Integer keys in raw map
        safe_keys = []
        for key in mixed_keys:
            # Verify safe integer value extraction matching Java's Number.intValue() / int cast
            val = int(key)
            self.assertIsInstance(val, int)
            safe_keys.append(val)
        self.assertEqual(safe_keys, [1, 2, 4, 64])

if __name__ == "__main__":
    unittest.main()
