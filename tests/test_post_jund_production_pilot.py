import importlib.util,pathlib,unittest
P=pathlib.Path(__file__).resolve().parents[1]/'scripts'/'post_jund_production_pilot.py'
spec=importlib.util.spec_from_file_location('pj',P); pj=importlib.util.module_from_spec(spec); spec.loader.exec_module(pj)
class T(unittest.TestCase):
 def test_matrix(self):
  self.assertEqual(90,len(pj.orientations())); self.assertEqual(100,len(pj.conditions_for_batch(0))); self.assertEqual(900,len({c['condition_id'] for b in range(9) for c in pj.conditions_for_batch(b)}))
 def test_required_seeds(self):self.assertEqual(list(range(97001,97011)),pj.SEEDS)
 def test_batch_partition(self):
  ids=[{c['condition_id'] for c in pj.conditions_for_batch(b)} for b in range(9)]
  self.assertTrue(all(len(x)==100 for x in ids)); self.assertEqual(900,len(set().union(*ids)))
 def test_wilson(self):
  lo,hi=pj.wilson(90,180); self.assertLess(lo,.5); self.assertGreater(hi,.5)
if __name__=='__main__':unittest.main()
