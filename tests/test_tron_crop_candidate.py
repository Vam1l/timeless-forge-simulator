from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATCHER = ROOT / "experimental/forge-ai/tron-crop-candidate/apply_candidate_overlay.py"
HELPER = ROOT / "experimental/forge-ai/tron-crop-candidate/TronCropRotationSelection.java"
MANA = ROOT / "experimental/forge-ai/forge-patches/forge/ai/ComputerUtilMana.java"


class TronCropCandidateTests(unittest.TestCase):
    def test_candidate_is_crop_rotation_specific(self):
        text = PATCHER.read_text()
        self.assertIn('"Crop Rotation".equals(source.getHostCard().getName())', text)
        self.assertNotIn("10-tron.dck", text)
        self.assertNotIn("95001", text)
        self.assertNotIn("White Weenie", text)

    def test_helper_keeps_nonassembly_fallback(self):
        text = HELPER.read_text()
        self.assertIn("if (missingAvailable.isEmpty())", text)
        self.assertRegex(text, r"if \(missingAvailable\.isEmpty\(\)\) \{\s*return null;")
        self.assertIn("battlefieldCounts.getOrDefault(name, 0) > 1", text)

    def test_historical_numeric_map_normalization_is_preserved(self):
        text = MANA.read_text()
        self.assertIn("instanceof Number", text)
        self.assertIn("((Number) key).intValue()", text)
        self.assertIn("ArrayListMultimap<Integer, SpellAbility>", text)
        # Candidate patch must not touch the historical mana source file.
        self.assertNotIn("TRON_CROP_CANDIDATE", text)

    def test_candidate_patch_only_targets_stock_computer_util_copy(self):
        text = PATCHER.read_text()
        self.assertIn("ComputerUtil.java", text)
        self.assertNotIn("forge-patches/forge/ai/ComputerUtilCard.java", text)
        self.assertNotIn("forge-patches/forge/ai/ComputerUtilMana.java", text)


if __name__ == "__main__":
    unittest.main()
