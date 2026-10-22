import importlib.util,hashlib,json,pathlib,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]

def load(path,name):
 s=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

class ArtifactLayoutTests(unittest.TestCase):
 def setUp(self):
  self.pj=load(ROOT/'scripts'/'post_jund_production_pilot.py','pj_test')
  self.agg=load(ROOT/'scripts'/'post_jund_artifact_aggregate.py','agg_test')
 def make_corpus(self,root):
  for b in range(9):
   d=root/f'post-jund-pilot-batch-{b}'; (d/'logs').mkdir(parents=True)
   rows=[]; mans=[]
   for c in self.pj.conditions_for_batch(b):
    lp=d/'logs'/f"{c['condition_id']}.log"; lp.write_text('preserved verbose log\n')
    cmd=['xvfb-run','-a','java','-jar','forge-production.jar','sim','-d',c['deck_a'],c['deck_b'],'-D','decks','-n','1','-c','120','-s',str(c['seed'])]
    rows.append({**c,'winner':c['deck_a'],'loser':c['deck_b'],'turns':10,'duration_ms':1000,'command':' '.join(cmd),'log':f'pilot-batch-{b}/logs/{lp.name}'})
    mans.append({'condition_id':c['condition_id'],'log':f'pilot-batch-{b}/logs/{lp.name}','log_sha256':hashlib.sha256(lp.read_bytes()).hexdigest(),'command':cmd})
   (d/'per-game.json').write_text(json.dumps(rows)); (d/'batch-manifest.json').write_text(json.dumps(mans)); (d/'runtime-failures.json').write_text('[]')
   ident={'production_main':self.agg.EXPECTED_MAIN,'production_tree':self.agg.EXPECTED_TREE,'deck_tree':self.agg.EXPECTED_DECK_TREE,'tron_tree':self.agg.EXPECTED_TRON_TREE,'jar_sha256':self.agg.EXPECTED_JAR,'batch':b,'seeds':self.agg.SEEDS,'clock':self.agg.CLOCK}
   (d/'identity.json').write_text(json.dumps(ident))
 def test_real_download_layout_accepts_all_nine(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td); self.make_corpus(root); rows,reports,ids=self.agg.verify_all(root)
   self.assertEqual(900,len(rows)); self.assertEqual(9,len(reports)); self.assertTrue(all(r['pass'] for r in reports))
 def test_missing_batch_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td); self.make_corpus(root)
   import shutil; shutil.rmtree(root/'post-jund-pilot-batch-8')
   with self.assertRaisesRegex(RuntimeError,'batch directory set mismatch'): self.agg.verify_all(root)
 def test_unexpected_batch_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td); self.make_corpus(root); (root/'post-jund-pilot-batch-9').mkdir()
   with self.assertRaisesRegex(RuntimeError,'batch directory set mismatch'): self.agg.verify_all(root)
 def test_duplicate_condition_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td); self.make_corpus(root); p=root/'post-jund-pilot-batch-0/per-game.json'; rows=json.loads(p.read_text()); rows[1]['condition_id']=rows[0]['condition_id']; p.write_text(json.dumps(rows))
   with self.assertRaisesRegex(RuntimeError,'duplicate row condition IDs'): self.agg.verify_all(root)
 def test_nonempty_failure_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td); self.make_corpus(root); (root/'post-jund-pilot-batch-0/runtime-failures.json').write_text('[{"x":1}]')
   with self.assertRaisesRegex(RuntimeError,'runtime failures nonempty'): self.agg.verify_all(root)
 def test_identity_mismatch_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td); self.make_corpus(root); p=root/'post-jund-pilot-batch-4/identity.json'; x=json.loads(p.read_text()); x['jar_sha256']='bad'; p.write_text(json.dumps(x))
   with self.assertRaisesRegex(RuntimeError,'identity mismatch'): self.agg.verify_all(root)
 def test_log_count_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td); self.make_corpus(root); next((root/'post-jund-pilot-batch-2/logs').glob('*.log')).unlink()
   with self.assertRaisesRegex(RuntimeError,'logs=99'): self.agg.verify_all(root)
if __name__=='__main__':unittest.main()
