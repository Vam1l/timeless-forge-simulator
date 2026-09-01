import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROD = ROOT / 'production/forge-ai/cleansing-wildfire'


class ProductionCleansingWildfireTests(unittest.TestCase):
    def test_policy_has_no_scenario_specific_state(self):
        text = (PROD / 'CleansingWildfireTargetingPolicy.java').read_text()
        for forbidden in ('06-jund-wildfire', '07-esper-control', '10-tron', '9700', 'seed', 'matchup'):
            self.assertNotIn(forbidden, text)

    def test_clean_integration_has_no_telemetry_or_measurement(self):
        text = (PROD / 'apply_destroy_ai.py').read_text()
        for forbidden in ('CWAI', 'CWMEASURE', 'System.identityHashCode', 'MagicStack', 'logCleansingWildfireTelemetry'):
            self.assertNotIn(forbidden, text)

    def test_exact_structure_and_targeting_rules_are_present(self):
        text = (PROD / 'apply_destroy_ai.py').read_text()
        for token in (
            'sa.getApi() != ApiType.Destroy',
            '!sa.usesTargeting()',
            '"Cleansing Wildfire".equals(sa.getHostCard().getName())',
            '"Land".equals(sa.getParamOrDefault("ValidTgts", ""))',
            'search.getApi() != ApiType.ChangeZone',
            '"Library".equals(search.getParamOrDefault("Origin", ""))',
            '"Battlefield".equals(search.getParamOrDefault("Destination", ""))',
            'contains("Land.Basic")',
            '"TargetedController".equals(search.getParamOrDefault("DefinedPlayer", ""))',
            'draw.getApi() == ApiType.Draw',
            'ai.getGame().getCardsIn(ZoneType.Battlefield)',
            'CardLists.filterControlledBy(legal, ai)',
            'c.hasKeyword(Keyword.INDESTRUCTIBLE)',
            '"Urza\'s Mine".equals(c.getName())',
            '"Urza\'s Power Plant".equals(c.getName())',
            '"Urza\'s Tower".equals(c.getName())',
            'ComputerUtilCard.getBestLandToRemoveAI(ai, urza, sa)',
            'ComputerUtilCard.getWorstLand(ownIndestructible)',
            'sa.getTargets().add(wildfireChoice)',
            'new AiAbilityDecision(100, AiPlayDecision.WillPlay)',
        ):
            self.assertIn(token, text)

    def test_stock_fallback_remains_original_opponent_target_construction(self):
        text = (PROD / 'apply_destroy_ai.py').read_text()
        self.assertIn('list = CardLists.getTargetableCards(ai.getOpponents().getCardsIn(ZoneType.Battlefield), sa);', text)
        self.assertIn('return null;', text)


if __name__ == '__main__':
    unittest.main()
