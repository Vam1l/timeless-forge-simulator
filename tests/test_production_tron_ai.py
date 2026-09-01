import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROD = ROOT / 'production/forge-ai/tron'

PROHIBITED = (
    'Hunting Pack',
    'Prismatic Strands',
    'Supreme Verdict',
    'Tinder Wall',
    'TRON_CROP_REALPATH',
    'TRON_CROP_FETCH',
)

BEHAVIOR_INPUTS = (
    PROD / 'TronCropRotationSelection.java',
    PROD / 'apply_computer_util.py',
    PROD / 'apply_tron_support.py',
    PROD / 'build_tron_repair.sh',
)


def prohibited_literals(paths):
    found = []
    for path in paths:
        text = pathlib.Path(path).read_text()
        for literal in PROHIBITED:
            if literal in text:
                found.append((str(path), literal))
    return found


class ProductionTronAiTests(unittest.TestCase):
    def test_scope_excludes_unrelated_ai_from_behavior_inputs(self):
        self.assertEqual([], prohibited_literals(BEHAVIOR_INPUTS))

    def test_generated_gameplay_java_literal_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            generated = pathlib.Path(td) / 'GeneratedGameplay.java'
            generated.write_text('class GeneratedGameplay { String x = "Tinder Wall"; }\n')
            self.assertEqual([(str(generated), 'Tinder Wall')], prohibited_literals([generated]))

    def test_readme_may_name_excluded_cards(self):
        readme = PROD / 'README.md'
        self.assertIn('Prismatic Strands', readme.read_text())
        self.assertNotIn(readme, BEHAVIOR_INPUTS)
        self.assertEqual([], prohibited_literals(BEHAVIOR_INPUTS))

    def test_test_fixture_may_name_excluded_cards(self):
        self.assertIn('Tinder Wall', pathlib.Path(__file__).read_text())
        self.assertNotIn(pathlib.Path(__file__), BEHAVIOR_INPUTS)
        self.assertEqual([], prohibited_literals(BEHAVIOR_INPUTS))

    def test_real_entry_is_crop_specific(self):
        text = (PROD / 'apply_computer_util.py').read_text()
        for token in [
            'chooseSacrificeType',
            '"Crop Rotation".equals(ability.getHostCard().getName())',
            'ability.getApi() != ApiType.ChangeZone',
            '"Library".equals',
            '"Battlefield".equals',
            'type.contains("Land")',
            'TronCropRotationSelection.allowedSacrificeNames',
            'ComputerUtilCard.getWorstLand(allowedCards)',
        ]:
            self.assertIn(token, text)
        self.assertNotIn('chooseTronCropRotationAssemblySacrifice', text)

    def test_numeric_map_fix_is_number_based(self):
        text = (PROD / 'apply_tron_support.py').read_text()
        self.assertIn('for (Object key : manaAbilityMap.keySet())', text)
        self.assertIn('key instanceof Number', text)
        self.assertIn('((Number) key).intValue()', text)

    def test_filter_setup_is_tron_relevant_only(self):
        text = (PROD / 'apply_tron_support.py').read_text()
        self.assertIn('Chromatic Star', text)
        self.assertIn('Chromatic Sphere', text)
        self.assertIn('card.isArtifact()', text)
        self.assertIn('!card.getManaAbilities().isEmpty()', text)
        self.assertNotIn('Tinder Wall', text)


if __name__ == '__main__':
    unittest.main()
