import pathlib, unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
PROD=ROOT/'production/forge-ai/tron'

class ProductionTronAiTests(unittest.TestCase):
    def test_scope_excludes_unrelated_ai(self):
        text='\n'.join(p.read_text() for p in PROD.glob('*') if p.suffix in {'.py','.java','.sh','.md'})
        self.assertNotIn('Hunting Pack', text)
        self.assertNotIn('Prismatic Strands', text)
        self.assertNotIn('Supreme Verdict', text)
        self.assertNotIn('Tinder Wall', text)
        self.assertNotIn('TRON_CROP_REALPATH', text)
        self.assertNotIn('TRON_CROP_FETCH', text)
    def test_real_entry_is_crop_specific(self):
        text=(PROD/'apply_computer_util.py').read_text()
        for token in ['chooseSacrificeType','"Crop Rotation".equals(ability.getHostCard().getName())','ability.getApi() != ApiType.ChangeZone','"Library".equals','"Battlefield".equals','type.contains("Land")','TronCropRotationSelection.allowedSacrificeNames']:
            self.assertIn(token,text)
        self.assertNotIn('chooseTronCropRotationAssemblySacrifice',text)
    def test_numeric_map_fix_is_number_based(self):
        text=(PROD/'apply_tron_support.py').read_text()
        self.assertIn('for (Object key : manaAbilityMap.keySet())',text)
        self.assertIn('key instanceof Number',text)
        self.assertIn('((Number) key).intValue()',text)
    def test_filter_setup_is_tron_relevant_only(self):
        text=(PROD/'apply_tron_support.py').read_text()
        self.assertIn('Chromatic Star',text); self.assertIn('Chromatic Sphere',text)
        self.assertIn('card.isArtifact()',text); self.assertNotIn('Tinder Wall',text)

if __name__=='__main__': unittest.main()
