from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATCHER = ROOT / "experimental/forge-ai/tron-crop-candidate/apply_candidate_overlay.py"
FETCH = ROOT / "experimental/forge-ai/tron-crop-candidate/apply_fetch_telemetry.py"
HELPER = ROOT / "experimental/forge-ai/tron-crop-candidate/TronCropRotationSelection.java"
MANA = ROOT / "experimental/forge-ai/forge-patches/forge/ai/ComputerUtilMana.java"


class TronCropCandidateTests(unittest.TestCase):
    def test_real_integration_is_crop_rotation_specific(self):
        text = PATCHER.read_text()
        self.assertIn("chooseSacrificeType", text)
        self.assertIn('"Crop Rotation".equals(ability.getHostCard().getName())', text)
        self.assertIn("ability.getApi() != ApiType.ChangeZone", text)
        self.assertIn('"Library".equals(ability.getParamOrDefault("Origin", ""))', text)
        self.assertIn('"Battlefield".equals(ability.getParamOrDefault("Destination", ""))', text)
        self.assertIn('ability.getParamOrDefault("ChangeType", "").contains("Land")', text)
        self.assertNotIn("chooseTronCropRotationAssemblySacrifice", text)
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
        self.assertIn("TRON_CROP_FETCH", text)
        self.assertNotIn("return c", text)

    def test_historical_numeric_map_normalization_is_preserved(self):
        text = MANA.read_text()
        self.assertIn("instanceof Number", text)
        self.assertIn("((Number) key).intValue()", text)
        self.assertIn("ArrayListMultimap<Integer, SpellAbility>", text)
        self.assertNotIn("TRON_CROP_CANDIDATE", text)


if __name__ == "__main__":
    unittest.main()
