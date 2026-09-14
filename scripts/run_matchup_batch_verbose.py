#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))
from timeless_forge.runner import ForgeEngine, run_experiment

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--matchup-indices',type=int,nargs='+',required=True)
    p.add_argument('--forge-jar',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--config',type=Path,required=True)
    a=p.parse_args()
    with open(a.config) as f: cfg=json.load(f)
    idx=set(a.matchup_indices)
    cfg['matchups']=[m for i,m in enumerate(cfg['matchups']) if i in idx]
    raw=Path(cfg.get('deck_dir','.'))
    if (repo_root/raw).exists(): cfg['deck_dir']=str((repo_root/raw).resolve())
    elif (a.config.parent/raw).exists(): cfg['deck_dir']=str((a.config.parent/raw).resolve())
    cfg['output_dir']=str(a.output)
    tmp=a.output.parent/f'batch-config-{a.output.name}.json'
    tmp.parent.mkdir(parents=True,exist_ok=True)
    tmp.write_text(json.dumps(cfg,indent=2))
    engine=ForgeEngine(a.forge_jar, quiet=False)
    run_experiment(tmp,engine)
    return 0
if __name__=='__main__': raise SystemExit(main())
