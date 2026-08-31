import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'experimental' / 'forge-ai' / 'hunting-diagnostic' / 'run_decision_telemetry.py'
spec = importlib.util.spec_from_file_location('decision_telemetry', MODULE)
dt = importlib.util.module_from_spec(spec); spec.loader.exec_module(dt)


class Run9CounterRegressionTests(unittest.TestCase):
    def test_storm_copies_are_not_original_casts(self):
        # Actual run-9 pattern: one real cast, Storm trigger, then two copy stack events.
        lines = [
            'Add To Stack: Ai(1)-Hunting Storm cast Hunting Pack',
            'Add To Stack: Ai(1)-Hunting Storm triggered Hunting Pack',
            'Resolve Stack: Storm (When you cast this spell, copy it for each other spell that was cast before it this turn.) [Card: Hunting Pack (22)]',
            'Add To Stack: Ai(1)-Hunting Storm cast Hunting Pack',
            'Add To Stack: Ai(1)-Hunting Storm cast Hunting Pack',
            'Resolve Stack: Hunting Pack (134) - Ai(1)-Hunting Storm creates a 4/4 green Beast creature token.',
            'Resolve Stack: Hunting Pack (135) - Ai(1)-Hunting Storm creates a 4/4 green Beast creature token.',
            'Resolve Stack: Hunting Pack (22) - Ai(1)-Hunting Storm creates a 4/4 green Beast creature token.',
        ]
        self.assertEqual(1, dt.original_casts(lines))
        all_cast_stack_events = sum(1 for line in lines if dt.CAST.match(line))
        self.assertEqual(3, all_cast_stack_events)
        self.assertEqual(2, all_cast_stack_events - dt.original_casts(lines))
        self.assertEqual(3, len(dt.TOKEN.findall('\n'.join(lines))))

    def test_glimpse_cleanup_is_not_original_cast(self):
        lines = [
            'Zone Change: Exile [Hunting Pack, Chromatic Sphere]',
            'Resolve Stack: Glimpse the Impossible moves Hunting Pack to Graveyard at the beginning of the next end step.',
        ]
        self.assertEqual(0, dt.original_casts(lines))

    def test_chromatic_activity_is_not_pack_cast(self):
        lines = [
            'Add To Stack: Ai(1)-Hunting Storm cast Chromatic Sphere',
            'Mana: Chromatic Sphere (9) - {1}, {T}, Sacrifice Chromatic Sphere: Add one mana of any color. Draw a card.',
        ]
        self.assertEqual(0, dt.original_casts(lines))


if __name__ == '__main__':
    unittest.main()
