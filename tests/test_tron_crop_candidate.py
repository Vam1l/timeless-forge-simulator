from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATCHER = ROOT / "experimental/forge-ai/tron-crop-candidate/apply_candidate_overlay.py"
FETCH = ROOT / "experimental/forge-ai/tron-crop-candidate/apply_fetch_telemetry.py"
HELPER = ROOT / "experimental/forge-ai/tron-crop-candidate/TronCropRotationSelection.java"
MANA = ROOT / "experimental/forge-ai/forge-patches/forge/ai/ComputerUtilMana.java"
RUNNER = ROOT / "experimental/forge-ai/tron-crop-candidate/run_phase4.py"

spec = importlib.util.spec_from_file_location("tron_phase4_runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class TronCropCandidateTests(unittest.TestCase):
    def test_real_integration_is_crop_rotation_specific(self):
        text = PATCHER.read_text()
        self.assertIn("chooseSacrificeType", text)
        self.assertIn('"Crop Rotation".equals(ability.getHostCard().getName())', text)
        self.assertIn("ability.getApi() != ApiType.ChangeZone", text)
        self.assertIn('"Library".equals(ability.getParamOrDefault("Origin", ""))', text)
        self.assertIn('"Battlefield".equals(ability.getParamOrDefault("Destination", ""))', text)
        self.assertIn('ability.getParamOrDefault("ChangeType", "").contains("Land")', text)
        # The patcher defensively names the old dead symbol so it can reject it if present;
        # it must not inject a method definition for that integration path.
        self.assertNotIn("private static Card chooseTronCropRotationAssemblySacrifice", text)
        self.assertNotIn("10-tron.dck", text)
        self.assertNotIn("95001", text)
        self.assertNotIn("White Weenie", text)

    def test_helper_keeps_nonassembly_and_duplicate_fallbacks(self):
        text = HELPER.read_text()
        self.assertIn("if (missingAvailable.isEmpty())", text)
        self.assertIn("return null;", text)
        self.assertIn("battlefieldCounts.getOrDefault(name, 0) > 1", text)

    def test_fetch_telemetry_is_observational_and_crop_guarded(self):
        text = FETCH.read_text()
        self.assertIn('"Crop Rotation".equals(sa.getHostCard().getName())', text)
        self.assertIn("logTronCropFetchTelemetry", text)
        self.assertIn('tronCropFetchPath = "battlefield_best_ai"', text)
        self.assertIn('tronCropFetchPath = "general_land_best"', text)
        self.assertIn('"missing_distinct_piece"', text)
        self.assertIn('c = ComputerUtilCard.getBestAI((Iterable<Card>)fetchList);', text)
        self.assertIn('c = ComputerUtilCard.getBestLandAI((Iterable<Card>)fetchList);', text)
        self.assertNotIn("TronCropRotationSelection", text)
        self.assertNotIn("allowedSacrificeNames", text)

    def test_fetch_parser_accepts_actual_early_battlefield_path(self):
        line = (
            "[TRON_CROP_FETCH] host=Crop Rotation hostId=31 api=ChangeZone "
            "path=battlefield_best_ai origin=[Library] destination=Battlefield "
            "legalCandidates=[Urza's Tower#13, Urza's Mine#34, Urza's Power Plant#27] "
            "controlledLands=[Urza's Mine#35] tronPresent=[Urza's Mine] "
            "tronMissing=[Urza's Power Plant, Urza's Tower] "
            "missingAvailable=[Urza's Power Plant, Urza's Tower] "
            "selected=Urza's Tower#13 classification=missing_distinct_piece"
        )
        parsed = runner.parse_fetch_line(line)
        self.assertEqual(parsed["path"], "battlefield_best_ai")
        self.assertEqual(parsed["selected"], "Urza's Tower#13")
        self.assertEqual(parsed["classification"], "missing_distinct_piece")

    def test_fetch_parser_accepts_preserved_gate1_initial_path_label(self):
        line = (
            "[TRON_CROP_FETCH] host=Crop Rotation hostId=31 api=ChangeZone "
            "path=initial origin=[Library] destination=Battlefield "
            "legalCandidates=[Forest#41, Urza's Tower#13, Urza's Mine#37, Urza's Power Plant#29] "
            "controlledLands=[Urza's Mine#35] tronPresent=[Urza's Mine] "
            "tronMissing=[Urza's Power Plant, Urza's Tower] "
            "missingAvailable=[Urza's Power Plant, Urza's Tower] "
            "selected=Urza's Tower#13 classification=missing_distinct_piece"
        )
        parsed = runner.parse_fetch_line(line)
        self.assertEqual(parsed["path"], "initial")
        self.assertEqual(parsed["selected"], "Urza's Tower#13")
        self.assertEqual(parsed["classification"], "missing_distinct_piece")
        self.assertIn("Urza's Mine#35", parsed["controlledLands"])

    def test_fetch_parser_accepts_fallback_land_path(self):
        line = (
            "[TRON_CROP_FETCH] host=Crop Rotation hostId=31 api=ChangeZone "
            "path=general_land_best origin=[Library] destination=Battlefield "
            "legalCandidates=[Forest#42] controlledLands=[Forest#44] "
            "tronPresent=[] tronMissing=[Urza's Mine, Urza's Power Plant, Urza's Tower] "
            "missingAvailable=[] selected=Forest#42 classification=fallback"
        )
        parsed = runner.parse_fetch_line(line)
        self.assertEqual(parsed["path"], "general_land_best")
        self.assertEqual(parsed["selected"], "Forest#42")
        self.assertEqual(parsed["classification"], "fallback")

    def test_storm_or_later_card_mentions_cannot_fake_fetch(self):
        text = "Mana: Urza's Tower (13) - {T}: Add {C}.\nResolve Stack: Crop Rotation"
        self.assertEqual(runner.crop_events(text)["fetches"], [])

    def test_historical_numeric_map_normalization_is_preserved(self):
        text = MANA.read_text()
        self.assertIn("instanceof Number", text)
        self.assertIn("((Number) key).intValue()", text)
        self.assertIn("ArrayListMultimap<Integer, SpellAbility>", text)
        self.assertNotIn("TRON_CROP_CANDIDATE", text)


if __name__ == "__main__":
    unittest.main()
