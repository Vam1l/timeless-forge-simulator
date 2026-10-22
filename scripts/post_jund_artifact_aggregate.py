#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,importlib.util,json,statistics,sys
from pathlib import Path

EXPECTED_MAIN='5a58621b797365aeedcc60d05da7d6b945ed7a32'
EXPECTED_TREE='9a025696bae4a5b1d7ade6e05e5757737ae280fb'
EXPECTED_DECK_TREE='3d55da96aa15ea6a7da5ed2cf98e7ff6417bee35'
EXPECTED_TRON_TREE='902ba2cf23e746469bccdeb59817d41cd16e913d'
EXPECTED_JAR='342da36f07d8445fa193dc39408e1e35ec7a9ec04a71b6e82f9258adb3876826'
SEEDS=list(range(97001,97011))
CLOCK=120
BATCHES=range(9)
PREFIX='post-jund-pilot-batch-'

HERE=Path(__file__).resolve()
BASE=HERE.with_name('post_jund_production_pilot.py')
spec=importlib.util.spec_from_file_location('pj_base',BASE)
pj=importlib.util.module_from_spec(spec); spec.loader.exec_module(pj)

def expected_ids_for_batch(batch:int)->set[str]:
    return {c['condition_id'] for c in pj.conditions_for_batch(batch)}

def _load_json(path:Path):
    if not path.is_file(): raise RuntimeError(f'missing required file: {path}')
    return json.loads(path.read_text())

def verify_batch(root:Path,batch:int)->tuple[list[dict],dict,dict]:
    d=root/f'{PREFIX}{batch}'
    if not d.is_dir(): raise RuntimeError(f'missing batch directory: {d}')
    sibling_nums=[]
    for x in root.iterdir():
        if x.is_dir() and x.name.startswith(PREFIX):
            suffix=x.name[len(PREFIX):]
            if not suffix.isdigit(): raise RuntimeError(f'unexpected batch directory: {x.name}')
            sibling_nums.append(int(suffix))
    unexpected=sorted(set(sibling_nums)-set(BATCHES))
    if unexpected: raise RuntimeError(f'unexpected batch numbers: {unexpected}')
    if sibling_nums.count(batch)!=1: raise RuntimeError(f'batch directory multiplicity for {batch}: {sibling_nums.count(batch)}')
    rows=_load_json(d/'per-game.json'); manifest=_load_json(d/'batch-manifest.json')
    failures=_load_json(d/'runtime-failures.json'); identity=_load_json(d/'identity.json')
    logs=sorted((d/'logs').glob('*.log')) if (d/'logs').is_dir() else []
    if not isinstance(rows,list) or len(rows)!=100: raise RuntimeError(f'batch {batch}: per-game rows={len(rows) if isinstance(rows,list) else "not-list"}')
    if not isinstance(manifest,list) or len(manifest)!=100: raise RuntimeError(f'batch {batch}: manifest entries={len(manifest) if isinstance(manifest,list) else "not-list"}')
    if failures!=[]: raise RuntimeError(f'batch {batch}: runtime failures nonempty ({len(failures) if isinstance(failures,list) else "invalid"})')
    if len(logs)!=100: raise RuntimeError(f'batch {batch}: logs={len(logs)}')
    expected=expected_ids_for_batch(batch)
    row_ids=[r.get('condition_id') for r in rows]; man_ids=[m.get('condition_id') for m in manifest]
    if len(set(row_ids))!=100: raise RuntimeError(f'batch {batch}: duplicate row condition IDs')
    if len(set(man_ids))!=100: raise RuntimeError(f'batch {batch}: duplicate manifest condition IDs')
    if set(row_ids)!=expected: raise RuntimeError(f'batch {batch}: row condition mismatch missing={sorted(expected-set(row_ids))} extra={sorted(set(row_ids)-expected)}')
    expected_rows={c['condition_id']:c for c in pj.conditions_for_batch(batch)}
    for r in rows:
        e=expected_rows[r['condition_id']]
        for k in ('pair_id','orientation_id','deck_a','deck_b','canonical_a','canonical_b','seed'):
            if r.get(k)!=e[k]: raise RuntimeError(f'batch {batch}: condition metadata mismatch {r["condition_id"]} field={k}')
    if set(man_ids)!=expected: raise RuntimeError(f'batch {batch}: manifest condition mismatch')
    by_manifest={m['condition_id']:m for m in manifest}
    for r in rows:
        cid=r['condition_id']; m=by_manifest[cid]
        log_name=Path(m['log']).name
        lp=d/'logs'/log_name
        if not lp.is_file(): raise RuntimeError(f'batch {batch}: missing log for {cid}: {log_name}')
        if pj.sha256(lp)!=m.get('log_sha256'): raise RuntimeError(f'batch {batch}: log digest mismatch for {cid}')
        cmd=m.get('command')
        if not isinstance(cmd,list): raise RuntimeError(f'batch {batch}: manifest command not list for {cid}')
        required=['-n','1','-c','120','-s',str(r['seed'])]
        joined=' '.join(cmd)
        if any(x not in joined for x in required): raise RuntimeError(f'batch {batch}: command mismatch for {cid}')
        if r.get('winner') in (None,'','UNPARSED'): raise RuntimeError(f'batch {batch}: unparsed result for {cid}')
    expected_identity={'production_main':EXPECTED_MAIN,'production_tree':EXPECTED_TREE,'deck_tree':EXPECTED_DECK_TREE,'tron_tree':EXPECTED_TRON_TREE,'jar_sha256':EXPECTED_JAR,'batch':batch,'seeds':SEEDS,'clock':CLOCK}
    if identity!=expected_identity: raise RuntimeError(f'batch {batch}: identity mismatch expected={expected_identity} actual={identity}')
    report={'batch':batch,'rows':100,'unique_conditions':100,'manifest_entries':100,'logs':100,'runtime_failures':0,'identity_ok':True,'pass':True}
    return rows,identity,report

def verify_all(root:Path):
    if not root.is_dir(): raise RuntimeError(f'input directory missing: {root}')
    present=[]
    for x in root.iterdir():
        if x.is_dir() and x.name.startswith(PREFIX):
            suffix=x.name[len(PREFIX):]
            if not suffix.isdigit(): raise RuntimeError(f'unexpected batch directory: {x.name}')
            present.append(int(suffix))
    if sorted(present)!=list(BATCHES): raise RuntimeError(f'batch directory set mismatch: {sorted(present)}')
    rows=[]; reports=[]; identities=[]
    for b in BATCHES:
        rr,ii,rp=verify_batch(root,b); rows.extend(rr); identities.append(ii); reports.append(rp)
    ids=[r['condition_id'] for r in rows]
    expected={f'o{o:02d}-s{s}' for o in range(90) for s in SEEDS}
    if len(rows)!=900 or len(set(ids))!=900 or set(ids)!=expected:
        raise RuntimeError(f'global condition integrity failure rows={len(rows)} unique={len(set(ids))} missing={len(expected-set(ids))} extra={len(set(ids)-expected)}')
    if set(int(r['pair_id']) for r in rows)!=set(range(1,46)): raise RuntimeError('matchup coverage mismatch')
    if set(int(r['orientation_id']) for r in rows)!=set(range(90)): raise RuntimeError('orientation coverage mismatch')
    if set(int(r['seed']) for r in rows)!=set(SEEDS): raise RuntimeError('seed coverage mismatch')
    parity_keys=('production_main','production_tree','deck_tree','tron_tree','jar_sha256','seeds','clock')
    if any(any(x[k]!=identities[0][k] for k in parity_keys) for x in identities[1:]): raise RuntimeError('cross-batch identity parity failure')
    normalized=set()
    for r in rows:
        parts=r['command'].split(); parts=[('JAR' if i>0 and parts[i-1]=='-jar' else 'DECKDIR' if i>0 and parts[i-1]=='-D' else 'SEED' if i>0 and parts[i-1]=='-s' else 'A' if i>0 and parts[i-1]=='-d' else 'B' if i>1 and parts[i-2]=='-d' else x) for i,x in enumerate(parts)]
        normalized.add(tuple(parts))
    if len(normalized)!=1: raise RuntimeError(f'non-JAR simulator settings mismatch variants={len(normalized)}')
    return rows,reports,identities

def summarize_game_lengths(rows,decks):
    out={}
    for d in decks:
        vals=[int(r['turns']) for r in rows if d in (r['deck_a'],r['deck_b']) and all(x in decks for x in (r['deck_a'],r['deck_b']))]
        vals.sort()
        out[d]={'games':len(vals),'min_turns':min(vals),'median_turns':statistics.median(vals),'p90_turns':vals[round((len(vals)-1)*.9)],'max_turns':max(vals)}
    return out

def aggregate(root:Path,out:Path):
    out.mkdir(parents=True,exist_ok=True)
    rows,reports,identities=verify_all(root)
    with (out/'per-game.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    (out/'per-game.json').write_text(json.dumps(rows,indent=2)+'\n')
    (out/'batch-verification.json').write_text(json.dumps(reports,indent=2)+'\n')
    full=pj.summarize(rows,pj.DECKS); nine=[d for d in pj.DECKS if d!='09-hunting-storm.dck']; eight=[d for d in nine if d!='10-tron.dck']
    views={'ten_deck':full,'nine_deck':pj.summarize(rows,nine),'eight_deck':pj.summarize(rows,eight),'ten_matchups':pj.matchup_matrix(rows,pj.DECKS),'nine_matchups':pj.matchup_matrix(rows,nine),'eight_matchups':pj.matchup_matrix(rows,eight),'game_lengths':{'ten':summarize_game_lengths(rows,pj.DECKS),'nine':summarize_game_lengths(rows,nine),'eight':summarize_game_lengths(rows,eight)}}
    (out/'balance-views.json').write_text(json.dumps(views,indent=2)+'\n')
    casts,anom=pj.wildfire_audit(root)
    (out/'jund-wildfire-audit.json').write_text(json.dumps({'casts':casts,'anomalies':anom},indent=2)+'\n')
    hunting=[r for r in rows if '09-hunting-storm.dck' in (r['deck_a'],r['deck_b'])]
    hs={'games':len(hunting),'wins':sum(r['winner']=='09-hunting-storm.dck' for r in hunting),'losses':sum(r['winner']!='09-hunting-storm.dck' for r in hunting),'hunting_pack_casts':sum(int(r.get('hunting_pack_casts',0)) for r in hunting),'storm_trigger_events':sum(int(r.get('hunting_pack_triggered',0)) for r in hunting),'beast_mentions':sum(int(r.get('beast_mentions',0)) for r in hunting),'simulated_record_suitable_for_human_balance':False}
    (out/'hunting-storm-summary.json').write_text(json.dumps(hs,indent=2)+'\n')
    jund=[r for r in rows if '06-jund-wildfire.dck' in (r['deck_a'],r['deck_b'])]
    engine_keys=[k for k in rows[0] if k.endswith('_casts')]
    jund_engine={'games':len(jund),**{k:sum(int(r.get(k,0)) for r in jund) for k in engine_keys}}
    (out/'jund-engine-summary.json').write_text(json.dumps(jund_engine,indent=2)+'\n')
    first=sum(r['winner']==r['deck_a'] for r in rows); second=sum(r['winner']==r['deck_b'] for r in rows)
    seat={'overall':{'first_wins':first,'second_wins':second,'first_win_rate':first/900},'per_deck':[{k:r[k] for k in ('deck','name','first_wins','first_losses','second_wins','second_losses')} for r in full]}
    (out/'seat-analysis.json').write_text(json.dumps(seat,indent=2)+'\n')
    turns=sorted(int(r['turns']) for r in rows); durations=sorted(int(r['duration_ms']) for r in rows)
    q=lambda xs,p: xs[round((len(xs)-1)*p)]
    lengths={'turns':{'min':min(turns),'p10':q(turns,.1),'median':statistics.median(turns),'p90':q(turns,.9),'p95':q(turns,.95),'max':max(turns)},'duration_ms':{'min':min(durations),'p10':q(durations,.1),'median':statistics.median(durations),'p90':q(durations,.9),'p95':q(durations,.95),'max':max(durations)}}
    (out/'game-length-distribution.json').write_text(json.dumps(lengths,indent=2)+'\n')
    integrity={'expected_conditions':900,'rows':900,'unique_conditions':900,'matchups':45,'orientations':90,'seeds':SEEDS,'runtime_failures':0,'replacement_games':0,'retried_games':0,'parse_failures':0,'identity_parity':True,'new_preflight_games_executed':0,'new_pilot_games_executed':0,'existing_batch_games_reused':900,'pass':True}
    (out/'integrity.json').write_text(json.dumps(integrity,indent=2)+'\n')
    (out/'acceptance.json').write_text(json.dumps({'technical_integrity':True,'balance_reporting_allowed':True,**{k:integrity[k] for k in ('new_preflight_games_executed','new_pilot_games_executed','existing_batch_games_reused')}},indent=2)+'\n')
    md=['# Artifact-only post-Jund aggregation','', '**Technical integrity: PASS** — 900/900 preserved conditions verified; zero new gameplay.','', '## Ten-deck field']
    for r in full: md.append(f"- {r['name']}: {r['wins']}-{r['losses']} ({r['win_rate']:.1%}; Wilson 95% {r['wilson95_low']:.1%}–{r['wilson95_high']:.1%})")
    md+=['','## Nine-deck AI-functional field']
    for r in views['nine_deck']: md.append(f"- {r['name']}: {r['wins']}-{r['losses']} ({r['win_rate']:.1%}; Wilson 95% {r['wilson95_low']:.1%}–{r['wilson95_high']:.1%})")
    md+=['','## Eight-deck sensitivity field']
    for r in views['eight_deck']: md.append(f"- {r['name']}: {r['wins']}-{r['losses']} ({r['win_rate']:.1%}; Wilson 95% {r['wilson95_low']:.1%}–{r['wilson95_high']:.1%})")
    md+=['','## Jund Wildfire audit',f"- Casts classified: {len(casts)}",f"- Anomalous/ambiguous classifications: {len(anom)}",'','## Hunting Storm','- Included for automated continuity/runtime only; its simulated record is not human-balance evidence.','', '## Execution provenance','- new_preflight_games_executed: 0','- new_pilot_games_executed: 0','- existing_batch_games_reused: 900']
    (out/'report.md').write_text('\n'.join(md)+'\n')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    try: aggregate(a.input,a.output)
    except Exception as e:
        a.output.mkdir(parents=True,exist_ok=True); (a.output/'continuation-failure.json').write_text(json.dumps({'error':str(e),'new_preflight_games_executed':0,'new_pilot_games_executed':0,'existing_batch_games_reused':0},indent=2)+'\n'); raise
    return 0
if __name__=='__main__': sys.exit(main())
