import pathlib
import unittest

from scripts.production_cleansing_wildfire_chronology import parse_preflight_log, analyze_preserved_logs

ROOT = pathlib.Path(__file__).resolve().parents[1]


def game(lines):
    return "\n".join(lines + ["Game Result: Game 1 ended in 100 ms. Ai(1)-Jund Wildfire has won!"])


class ProductionCleansingWildfireChronologyTests(unittest.TestCase):
    def test_mana_activation_affirmatively_observes_crop_rotation_mine(self):
        text = game([
            "Turn: Turn 2 (Ai(2)-Tron)",
            "Mana: Urza's Mine (95) - {T}: Add {C}.",
            "Turn: Turn 4 (Ai(2)-Tron)",
            "Land: Ai(2)-Tron played Urza's Power Plant (86)",
            "Turn: Turn 5 (Ai(1)-Jund Wildfire)",
            "Phase: Ai(1)-Jund Wildfire's Main phase, precombat",
            "Add To Stack: Ai(1)-Jund Wildfire cast Cleansing Wildfire targeting [Urza's Mine (95)]",
        ])
        r = parse_preflight_log(text, "Tron")["casts"][0]
        self.assertEqual(r["distinct_opposing_urza_types"], ["Urza's Mine", "Urza's Power Plant"])
        self.assertEqual(r["classification"], "visible-Tron disruption")
        mine = next(x for x in r["active_opposing_urza"] if x["id"] == "95")
        self.assertEqual(mine["entry_evidence"]["kind"], "mana-activation")

    def test_mine_exit_removes_it_from_distinct_types(self):
        text = game([
            "Mana: Urza's Mine (95) - {T}: Add {C}.",
            "Land: Ai(2)-Tron played Urza's Power Plant (86)",
            "Zone Change: Urza's Mine (95) was put into Graveyard from Battlefield.",
            "Land: Ai(1)-Jund Wildfire played Slagwoods Bridge (26)",
            "Turn: Turn 5 (Ai(1)-Jund Wildfire)",
            "Phase: Ai(1)-Jund Wildfire's Main phase, precombat",
            "Add To Stack: Ai(1)-Jund Wildfire cast Cleansing Wildfire targeting [Slagwoods Bridge (26)]",
        ])
        r = parse_preflight_log(text, "Tron")["casts"][0]
        self.assertEqual(r["distinct_opposing_urza_types"], ["Urza's Power Plant"])
        self.assertEqual(r["classification"], "self-Bridge ramp")

    def test_duplicate_power_plants_are_one_type(self):
        text = game([
            "Land: Ai(2)-Tron played Urza's Power Plant (86)",
            "Mana: Urza's Power Plant (88) - {T}: Add {C}.",
            "Land: Ai(1)-Jund Wildfire played Slagwoods Bridge (26)",
            "Add To Stack: Ai(1)-Jund Wildfire cast Cleansing Wildfire targeting [Slagwoods Bridge (26)]",
        ])
        r = parse_preflight_log(text, "Tron")["casts"][0]
        self.assertEqual(len(r["active_opposing_urza"]), 2)
        self.assertEqual(r["distinct_opposing_urza_types"], ["Urza's Power Plant"])

    def test_same_name_different_ids_are_tracked_separately(self):
        text = game([
            "Land: Ai(2)-Tron played Urza's Mine (95)",
            "Land: Ai(2)-Tron played Urza's Mine (97)",
            "Zone Change: Urza's Mine (95) was put into Graveyard from Battlefield.",
            "Land: Ai(1)-Jund Wildfire played Slagwoods Bridge (26)",
            "Add To Stack: Ai(1)-Jund Wildfire cast Cleansing Wildfire targeting [Slagwoods Bridge (26)]",
        ])
        r = parse_preflight_log(text, "Tron")["casts"][0]
        self.assertEqual([x["id"] for x in r["active_opposing_urza"]], ["97"])

    def test_no_retroactive_inference_before_first_mana_observation(self):
        text = game([
            "Land: Ai(2)-Tron played Urza's Power Plant (86)",
            "Land: Ai(1)-Jund Wildfire played Slagwoods Bridge (26)",
            "Add To Stack: Ai(1)-Jund Wildfire cast Cleansing Wildfire targeting [Slagwoods Bridge (26)]",
            "Mana: Urza's Mine (95) - {T}: Add {C}.",
        ])
        r = parse_preflight_log(text, "Tron")["casts"][0]
        self.assertEqual(r["distinct_opposing_urza_types"], ["Urza's Power Plant"])
        self.assertEqual(r["classification"], "self-Bridge ramp")

    def test_exact_preserved_tron_seed_97001_sequence(self):
        text = game([
            "Turn: Turn 2 (Ai(2)-Tron)",
            "Mana: Urza's Mine (95) - {T}: Add {C}. If you control an Urza's Power-Plant and an Urza's Tower, add {C}{C} instead.",
            "Turn: Turn 4 (Ai(2)-Tron)",
            "Land: Ai(2)-Tron played Urza's Power Plant (86)",
            "Turn: Turn 5 (Ai(1)-Jund Wildfire)",
            "Phase: Ai(1)-Jund Wildfire's Main phase, precombat",
            "Land: Ai(1)-Jund Wildfire played Slagwoods Bridge (26)",
            "Land: Ai(1)-Jund Wildfire played Slagwoods Bridge (27)",
            "Add To Stack: Ai(1)-Jund Wildfire cast Cleansing Wildfire targeting [Urza's Mine (95)]",
            "Zone Change: Urza's Mine (95) was put into Graveyard from Battlefield.",
            "Land: Ai(2)-Tron played Urza's Mine (97)",
            "Land: Ai(2)-Tron played Urza's Tower (72)",
            "Land: Ai(2)-Tron played Urza's Power Plant (88)",
            "Turn: Turn 11 (Ai(1)-Jund Wildfire)",
            "Land: Ai(1)-Jund Wildfire played Slagwoods Bridge (24)",
            "Add To Stack: Ai(1)-Jund Wildfire cast Cleansing Wildfire targeting [Urza's Tower (72)]",
            "Zone Change: Urza's Tower (72) was put into Graveyard from Battlefield.",
            "Add To Stack: Ai(1)-Jund Wildfire cast Cleansing Wildfire targeting [Urza's Power Plant (86)]",
        ])
        rows = parse_preflight_log(text, "Tron")["casts"]
        self.assertEqual([r["committed_target"]["name"] for r in rows], ["Urza's Mine", "Urza's Tower", "Urza's Power Plant"])
        self.assertTrue(all(r["classification"] == "visible-Tron disruption" for r in rows))

    def test_exact_preserved_esper_seed_97004_sequence(self):
        text = game([
            "Turn: Turn 2 (Ai(2)-Esper Control)",
            "Land: Ai(2)-Esper Control played Ash Barrens (88)",
            "Turn: Turn 3 (Ai(1)-Jund Wildfire)",
            "Phase: Ai(1)-Jund Wildfire's Main phase, postcombat",
            "Add To Stack: Ai(1)-Jund Wildfire cast Cleansing Wildfire targeting [Ash Barrens (88)]",
            "Zone Change: Ash Barrens (88) was put into Graveyard from Battlefield.",
            "Turn: Turn 9 (Ai(1)-Jund Wildfire)",
            "Land: Ai(1)-Jund Wildfire played Slagwoods Bridge (26)",
            "Turn: Turn 11 (Ai(1)-Jund Wildfire)",
            "Phase: Ai(1)-Jund Wildfire's Main phase, precombat",
            "Add To Stack: Ai(1)-Jund Wildfire cast Cleansing Wildfire targeting [Slagwoods Bridge (26)]",
            "Mana: Slagwoods Bridge (26) - {T}: Add {R} or {G}.",
            "Add To Stack: Ai(1)-Jund Wildfire cast Cleansing Wildfire targeting [Slagwoods Bridge (26)]",
        ])
        rows = parse_preflight_log(text, "Esper")["casts"]
        self.assertEqual([r["classification"] for r in rows], ["stock fallback", "self-Bridge ramp", "self-Bridge ramp"])

    def test_preserved_artifact_logs_classify_all_six_casts(self):
        root = pathlib.Path("/mnt/data/prod12_art/preflight/logs")
        if not root.exists():
            self.skipTest("preserved artifact logs not mounted")
        report = analyze_preserved_logs(
            (root / "jund-vs-esper-seed-97004.log").read_text(),
            (root / "jund-vs-tron-seed-97001.log").read_text(),
        )
        self.assertEqual(len(report["wildfire_casts"]), 6)
        self.assertTrue(report["pass"])
        self.assertEqual(report["new_games_executed"], 0)


if __name__ == "__main__":
    unittest.main()
