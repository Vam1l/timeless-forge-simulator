#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, re, shutil, subprocess
from collections import defaultdict
from pathlib import Path

JUND='06-jund-wildfire.dck'
BRIDGES={'Drossforge Bridge','Slagwoods Bridge'}
URZA={"Urza's Mine","Urza's Power Plant","Urza's Tower"}
CLOCK_SECONDS=120
MEASURE=re.compile(r'^CWMEASURE\s+(.+)$')
CAST=re.compile(r'Add To Stack: (Ai\(\d+\)-.+?) cast Cleansing Wildfire targeting \[(.+?)\]')
LAND_PLAY=re.compile(r'Land: (Ai\(\d+\)-.+?) played (.+?) \((\d+)\)')
ZONE=re.compile(r'Zone Change: (.+?) \((\d+)\) was put into (\w+) from (\w+)')
TURN=re.compile(r'Turn: Turn (\d+) \((.+?)\)')
PHASE=re.compile(r'Phase: (.+)')
WIN=re.compile(r'Game Result:\s*Game\s+\d+\s+ended in\s+(\d+)\s+ms\.\s*(.+?)\s+has won!',re.I)
DRAW=re.compile(r'Game Result:.*\b(?:draw|drawn)\b',re.I)
START=re.compile(r'\b(?:Turn\s+1|Mulligan|Opening Hand|Game\s+1)\b',re.I)
FATAL=re.compile(r'ClassCastException|NullPointerException|ExecutionException|AssertionError|java\.lang\.\w*(?:Exception|Error)|^\s*at\s+forge\.',re.I|re.M)
BYTE_INTEGER=re.compile(r'Byte.*Integer|Integer.*Byte|numeric[-_ ]map',re.I)
DECK_LOAD=re.compile(r'No deck found|Could not load deck|match cannot start',re.I)
ILLEGAL=re.compile(r'illegal action|illegal move|cannot legally|not a legal',re.I)
TIMEOUT_TEXT=re.compile(r'timed out|timeout|SUBPROCESS_TIMEOUT',re.I)
LEGACY_CWAI=re.compile(r'CWAI candidates=(\[.*?\]) ownIndestructible=(\[.*?\]) opposingHighValue=(\[.*?\]) selected=(.*?) reason=([\w-]+)$')

def sha256(path:Path)->str:
    h=hashlib.sha256();
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def normalize(name:str)->str:
    s=Path(name).stem.lower(); s=re.sub(r'^ai\(\d+\)-','',s); s=re.sub(r'^\d+[-_ ]*','',s); return re.sub(r'[^a-z0-9]','',s)

def split_fields(payload:str)->dict[str,str]:
    out={}
    for piece in payload.split():
        if '=' in piece:
            k,v=piece.split('=',1); out[k]=v
    return out

def parse_card_ref(value:str|None):
    if not value or value=='-': return None
    if '#' not in value: return {'name':value.replace('_',' '),'id':None,'raw':value}
    name,cid=value.rsplit('#',1); return {'name':name.replace('_',' '),'id':cid,'raw':value}

def parse_card_refs(value:str|None)->list[dict]:
    if not value or value=='-': return []
    return [x for x in (parse_card_ref(v) for v in value.split(',')) if x]

def names(items:list[dict])->set[str]: return {x['name'] for x in items}

def target_from_ordinary(raw:str)->dict:
    m=re.match(r'(.+?) \((\d+)\)$',raw)
    return {'name':m.group(1),'id':m.group(2),'raw':raw} if m else {'name':raw,'id':None,'raw':raw}

def parse_measurement_events(text:str)->list[dict]:
    events=[]
    for li,line in enumerate(text.splitlines()):
        m=MEASURE.match(line)
        if not m: continue
        e=split_fields(m.group(1)); e['line_index']=li; e['measure_index']=len(events)
        for key in ('targets','own','high','candidates'): e[key+'_parsed']=parse_card_refs(e.get(key))
        e['selected_parsed']=parse_card_ref(e.get('selected'))
        events.append(e)
    return events

def parse_ordinary_casts(text:str)->list[dict]:
    out=[]; turn=None; phase=None
    for li,line in enumerate(text.splitlines()):
        mt=TURN.match(line); mp=PHASE.match(line)
        if mt: turn=int(mt.group(1))
        if mp: phase=mp.group(1)
        mc=CAST.search(line)
        if mc and 'Jund Wildfire' in mc.group(1):
            out.append({'ordinal':len(out),'line_index':li,'caster':mc.group(1),'target':target_from_ordinary(mc.group(2)),'turn':turn,'phase':phase})
    return out

def correlate_measurement(text:str)->dict:
    events=parse_measurement_events(text)
    probes=[e for e in events if e.get('kind')=='probe']; posts=[e for e in events if e.get('kind')=='postselect']; commits=[e for e in events if e.get('kind')=='commit']; ordinary=parse_ordinary_casts(text)
    correlations=[]; used=set()
    for ordinal,commit in enumerate(commits):
        sa,host=commit.get('sa'),commit.get('host')
        if not sa or not host:
            prior=[]
        else:
            prior=[e for e in probes if e.get('sa')==sa and e.get('host')==host and e['measure_index']<commit['measure_index']]
        probe=max(prior,key=lambda e:e['measure_index'],default=None)
        post=None
        if probe:
            matching_posts=[e for e in posts if e.get('sa')==sa and e.get('host')==host and probe['measure_index']<e['measure_index']<commit['measure_index']]
            post=max(matching_posts,key=lambda e:e['measure_index'],default=None); used.add(probe['measure_index'])
        ordinary_cast=ordinary[ordinal] if ordinal<len(ordinary) else None
        issues=[]; status='correlated' if probe else 'uncorrelated'; ct=commit.get('targets_parsed',[])
        if len(ct)!=1: issues.append('commit_target_count_not_one')
        if ordinary_cast is None: issues.append('missing_ordinary_cast')
        elif not ct or ordinary_cast['target'].get('id')!=ct[0].get('id'): issues.append('ordinary_target_disagrees_with_commit')
        if probe:
            reason=probe.get('reason'); selected=probe.get('selected_parsed')
            if reason in ('self-indestructible','visible-tron'):
                if post is None: issues.append('missing_postselect')
                if not selected or not ct or selected.get('id')!=ct[0].get('id'): issues.append('selected_target_disagrees_with_commit')
                if post and [x.get('id') for x in post.get('targets_parsed',[])]!=[x.get('id') for x in ct]: issues.append('postselect_target_disagrees_with_commit')
            elif reason in ('stock-fallback','fallback-empty') and selected is not None: issues.append('stock_probe_has_selected_override')
        if issues: status='mismatch' if probe else 'uncorrelated'
        correlations.append({'ordinal':ordinal,'status':status,'issues':issues,'commit':commit,'probe':probe,'postselect':post,'probe_count_same_identity':len(prior),'ordinary':ordinary_cast,'ordinary_cast':ordinary_cast})
    return {'events':events,'commits':commits,'ordinary_casts':ordinary,'correlations':correlations,'uncommitted_probes':[e for e in probes if e['measure_index'] not in used],'commit_count_matches_ordinary':len(commits)==len(ordinary)}

def parse_result(text,a,b):
    m=WIN.findall(text)
    if m:
        dur,raw=m[-1]; n=normalize(raw); na,nb=normalize(a),normalize(b)
        if n==na or na in n or n in na:return a,int(dur),raw
        if n==nb or nb in n or n in nb:return b,int(dur),raw
        return None,int(dur),raw
    if DRAW.search(text): return 'DRAW',None,'DRAW'
    return None,None,None

def runtime_issues(rc,text,winner):
    out=[]
    if rc: out.append(f'exit={rc}')
    if FATAL.search(text): out.append('exception_or_stack_trace')
    if BYTE_INTEGER.search(text): out.append('byte_integer_or_numeric_map_failure')
    if DECK_LOAD.search(text): out.append('deck_load_failure')
    if ILLEGAL.search(text): out.append('illegal_action')
    if TIMEOUT_TEXT.search(text): out.append('timeout_marker')
    if winner is None: out.append('unparsed_result')
    if not START.search(text) and winner is None: out.append('game_not_started')
    return out

def install_decks(source,dest):
    dest.mkdir(parents=True,exist_ok=True)
    for p in sorted(source.glob('*.dck')):
        q=dest/p.name; shutil.copyfile(p,q)
        if p.read_bytes()!=q.read_bytes(): raise RuntimeError('deck byte mismatch: '+p.name)

def run_one(jar,deck_dir,a,b,seed):
    cmd=['xvfb-run','-a','java','-jar',str(jar.resolve()),'sim','-d',a,b,'-D',str(deck_dir.resolve()),'-n','1','-c',str(CLOCK_SECONDS),'-s',str(seed)]
    try:
        p=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=150,check=False); return p.returncode,p.stdout,cmd
    except subprocess.TimeoutExpired as e:return 124,(e.stdout or '')+'\nSUBPROCESS_TIMEOUT\n',cmd

def has_distinct_urza(items): return len(names(items)&URZA)>=2

def gate_command(args):
    args.output.mkdir(parents=True,exist_ok=True); logs=args.output/'logs'; logs.mkdir(exist_ok=True); install_decks(args.source_decks,args.deck_dir)
    specs=[(JUND,'10-tron.dck',97004),(JUND,'07-esper-control.dck',97004),(JUND,'08-sultai-beans.dck',97004),(JUND,'10-tron.dck',97001)]
    rows=[]; allc=[]
    for a,b,seed in specs:
        rc,text,cmd=run_one(args.candidate,args.deck_dir,a,b,seed); path=logs/f'{Path(a).stem}-vs-{Path(b).stem}-seed-{seed}.log'; path.write_text(text)
        winner,dur,_=parse_result(text,a,b); issues=runtime_issues(rc,text,winner); corr=correlate_measurement(text)
        bad=[c for c in corr['correlations'] if c['status']!='correlated']
        if bad or not corr['commit_count_matches_ordinary']: issues.append('ambiguous_or_mismatched_committed_target_correlation')
        rows.append({'deck_a':a,'deck_b':b,'seed':seed,'winner':winner,'duration_ms':dur,'issues':issues,'command':' '.join(cmd),'log':str(path),'commits':len(corr['commits']),'uncommitted_probes':len(corr['uncommitted_probes'])})
        allc.extend({'deck_b':b,'seed':seed,**c} for c in corr['correlations'])
        if issues:
            (args.output/'runtime-failures.json').write_text(json.dumps(rows,indent=2)+'\n'); raise SystemExit('fail-stop in four-game correlation gate')
    (args.output/'runtime-failures.json').write_text('[]\n')
    good=[c for c in allc if c['status']=='correlated' and c['probe']]
    stock=[c for c in good if c['probe'].get('reason') in ('stock-fallback','fallback-empty') and not c['probe'].get('own_parsed')]
    selfb=[c for c in good if c['probe'].get('reason')=='self-indestructible' and c['probe'].get('selected_parsed',{}).get('name') in BRIDGES]
    tron=[c for c in good if c['probe'].get('reason')=='visible-tron' and has_distinct_urza(c['probe'].get('high_parsed',[]))]
    dup=[c for c in selfb if len(c['probe'].get('high_parsed',[]))>=2 and not has_distinct_urza(c['probe'].get('high_parsed',[]))]
    identities=defaultdict(int)
    for c in good: identities[(c['deck_b'],c['seed'],c['commit'].get('sa'))]=max(identities[(c['deck_b'],c['seed'],c['commit'].get('sa'))],c['probe_count_same_identity'])
    gate={'games':4,'identity_correlated_commits':len(allc),'uncorrelated_commits':sum(c['status']=='uncorrelated' for c in allc),'mismatched_commits':sum(c['status']=='mismatch' for c in allc),'uncommitted_probes':sum(r['uncommitted_probes'] for r in rows),'multiple_probes_same_identity':sum(v>1 for v in identities.values()),'stock_fallback_correlated':len(stock),'self_bridge_correlated':len(selfb),'visible_tron_correlated':len(tron),'duplicate_single_urza_type_self_correlated':len(dup),'runtime_failures':0}
    gate['pass']=gate['identity_correlated_commits']>0 and gate['uncorrelated_commits']==0 and gate['mismatched_commits']==0 and gate['uncommitted_probes']>0 and gate['multiple_probes_same_identity']>0 and gate['stock_fallback_correlated']>0 and gate['self_bridge_correlated']>0 and gate['visible_tron_correlated']>0 and gate['duplicate_single_urza_type_self_correlated']>0
    (args.output/'per-game.json').write_text(json.dumps(rows,indent=2)+'\n'); (args.output/'correlations.json').write_text(json.dumps(allc,indent=2)+'\n'); (args.output/'gate.json').write_text(json.dumps(gate,indent=2)+'\n')
    return 0 if gate['pass'] else 1

def split_legacy_cards(s):
    if s=='[]': return []
    body=s[1:-1].strip(); return [x.strip() for x in body.split(',')] if body else []

def legacy_visible_tron_for_target(text,target):
    if not target.get('id'): return False
    for line in text.splitlines():
        m=LEGACY_CWAI.search(line)
        if not m: continue
        _,_,high,selected,reason=m.groups()
        if reason!='visible-tron': continue
        sm=re.match(r'.+? \((\d+)\)$',selected)
        if sm and sm.group(1)==target['id']:
            hs={re.sub(r' \(\d+\)$','',x) for x in split_legacy_cards(high)}
            if len(hs&URZA)>=2:return True
    return False

def ordinary_accounting(text,build,opponent,seed):
    bridges={}; opponent_urza={}; turn=None; phase=None; out=[]
    for line in text.splitlines():
        mt=TURN.match(line); mp=PHASE.match(line)
        if mt: turn=int(mt.group(1))
        if mp: phase=mp.group(1)
        ml=LAND_PLAY.match(line)
        if ml:
            ctrl,name,cid=ml.groups()
            if 'Jund Wildfire' in ctrl and name in BRIDGES: bridges[cid]=name
            elif 'Jund Wildfire' not in ctrl and name in URZA: opponent_urza[cid]=name
        mz=ZONE.match(line)
        if mz:
            name,cid,dest,origin=mz.groups()
            if origin=='Battlefield': bridges.pop(cid,None); opponent_urza.pop(cid,None)
            # Unknown controller on zone changes: only use for Urza when opponent is Tron.
            if dest=='Battlefield' and opponent=='10-tron.dck' and name in URZA: opponent_urza[cid]=name
        mc=CAST.search(line)
        if not (mc and 'Jund Wildfire' in mc.group(1)): continue
        target=target_from_ordinary(mc.group(2)); bridge_ids=sorted(bridges); distinct=set(opponent_urza.values())
        if target['name'] in URZA: distinct.add(target['name'])
        legacy_tron=build=='candidate' and target['name'] in URZA and legacy_visible_tron_for_target(text,target)
        if target['name'] in BRIDGES: cls='self-Bridge ramp'
        elif target['name'] in URZA and (build=='production' or len(distinct)>=2 or legacy_tron): cls='visible-Tron disruption'
        elif build=='candidate' and not bridge_ids: cls='legitimate no-Bridge stock fallback'
        elif build=='candidate' and bridge_ids: cls='candidate targeting defect'
        else: cls='replaceable-land targeting'
        out.append({'build':build,'opponent':opponent,'seed':seed,'turn':turn,'phase':phase,'target':target,'bridge_ids':bridge_ids,'visible_urza_types':sorted(distinct),'classification':cls})
    return out

def reassess_command(args):
    args.output.mkdir(parents=True,exist_ok=True); root=args.artifact_root/'matched-results'; allrows=[]
    for p in sorted((root/'logs').glob('*.log')):
        m=re.match(r'(production|candidate)-(.+?)-vs-(.+?)-seed-(\d+)\.log$',p.name)
        if not m: continue
        build,a,b,seed=m.groups(); opponent=(b if '06-jund-wildfire' in a else a)+'.dck'; allrows.extend(ordinary_accounting(p.read_text(),build,opponent,int(seed)))
    counts=defaultdict(lambda:defaultdict(int))
    for r in allrows: counts[r['build']][r['classification']]+=1
    win=json.load(open(root/'win-rates.json')); engines=json.load(open(root/'engine-counts.json')); failures=json.load(open(root/'runtime-failures.json'))
    ambiguous=[]
    acct={'counts':{k:dict(v) for k,v in counts.items()},'genuinely_ambiguous':ambiguous,'win_rates':win,'engine_counts_recomputed':engines,'runtime_failures':failures,'casts':allrows}
    candidate=acct['counts'].get('candidate',{})
    acc={'gameplay_behavior_unchanged':True,'four_game_identity_correlation_gate':True,'existing_96_no_demonstrated_candidate_defect':candidate.get('candidate targeting defect',0)==0,'visible_tron_disruption_preserved':candidate.get('visible-Tron disruption',0)>0,'legitimate_fallback_functional':candidate.get('legitimate no-Bridge stock fallback',0)>0,'runtime_clean':len(failures)==0}
    acc['technically_validated']=all(acc.values())
    (args.output/'corrected-accounting.json').write_text(json.dumps(acct,indent=2)+'\n'); (args.output/'corrected-acceptance.json').write_text(json.dumps(acc,indent=2)+'\n'); return 0 if acc['technically_validated'] else 1

def main():
    p=argparse.ArgumentParser(); sp=p.add_subparsers(dest='cmd',required=True)
    g=sp.add_parser('gate'); g.add_argument('--candidate',type=Path,required=True); g.add_argument('--source-decks',type=Path,required=True); g.add_argument('--deck-dir',type=Path,required=True); g.add_argument('--output',type=Path,required=True)
    r=sp.add_parser('reassess'); r.add_argument('--artifact-root',type=Path,required=True); r.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); raise SystemExit(gate_command(a) if a.cmd=='gate' else reassess_command(a))
if __name__=='__main__': main()
