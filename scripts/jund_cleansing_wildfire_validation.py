#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, json, math, re, shutil, subprocess, sys
from collections import defaultdict
from pathlib import Path

JUND = "06-jund-wildfire.dck"
MATCHUPS = ["10-tron.dck", "07-esper-control.dck", "08-sultai-beans.dck", "01-white-weenie.dck"]
SEEDS = list(range(97001, 97007))
BRIDGES = {"Drossforge Bridge", "Slagwoods Bridge"}
URZA = {"Urza's Mine", "Urza's Power Plant", "Urza's Tower"}
CLOCK_SECONDS = 120

FATAL = re.compile(r"ClassCastException|NullPointerException|ExecutionException|AssertionError|java\.lang\.\w*(?:Exception|Error)|^\s*at\s+forge\.", re.I|re.M)
BYTE_INTEGER = re.compile(r"Byte.*Integer|Integer.*Byte|numeric[-_ ]map", re.I)
DECK_LOAD = re.compile(r"No deck found|Could not load deck|match cannot start", re.I)
ILLEGAL = re.compile(r"illegal action|illegal move|cannot legally|not a legal", re.I)
START = re.compile(r"\b(?:Turn\s+1|Mulligan|Opening Hand|Game\s+1)\b", re.I)
WIN = re.compile(r"Game Result:\s*Game\s+\d+\s+ended in\s+(\d+)\s+ms\.\s*(.+?)\s+has won!", re.I)
DRAW = re.compile(r"Game Result:.*\b(?:draw|drawn)\b", re.I)
CAST = re.compile(r"Add To Stack: (Ai\(\d+\)-.+?) cast Cleansing Wildfire targeting \[(.+?)\]")
LAND_PLAY = re.compile(r"Land: (Ai\(\d+\)-.+?) played (.+?) \((\d+)\)")
ZONE = re.compile(r"Zone Change: (.+?) \((\d+)\) was put into (\w+) from (\w+)")
TURN = re.compile(r"Turn: Turn (\d+) \((.+?)\)")
PHASE = re.compile(r"Phase: (.+)")
CWAI = re.compile(r"CWAI candidates=(\[.*?\]) ownIndestructible=(\[.*?\]) opposingHighValue=(\[.*?\]) selected=(.*?) reason=([\w-]+)$")


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20), b''): h.update(b)
    return h.hexdigest()


def normalize(name: str) -> str:
    s=Path(name).stem.lower(); s=re.sub(r'^ai\(\d+\)-','',s); s=re.sub(r'^\d+[-_ ]*','',s)
    return re.sub(r'[^a-z0-9]','',s)


def parse_result(text: str, a: str, b: str):
    m=WIN.findall(text)
    if m:
        dur, raw=m[-1]; n=normalize(raw); na,nb=normalize(a),normalize(b)
        if n==na or na in n or n in na: return a,int(dur),raw
        if n==nb or nb in n or n in nb: return b,int(dur),raw
        return None,int(dur),raw
    if DRAW.search(text): return 'DRAW',None,'DRAW'
    return None,None,None


def issues(rc: int, text: str, winner):
    out=[]
    if rc: out.append(f'exit={rc}')
    if FATAL.search(text): out.append('exception_or_stack_trace')
    if BYTE_INTEGER.search(text): out.append('byte_integer_or_numeric_map_failure')
    if DECK_LOAD.search(text): out.append('deck_load_failure')
    if ILLEGAL.search(text): out.append('illegal_action')
    if winner is None: out.append('unparsed_result')
    if not START.search(text) and winner is None: out.append('game_not_started')
    return out


def install_decks(source: Path, dest: Path):
    dest.mkdir(parents=True, exist_ok=True)
    for p in sorted(source.glob('*.dck')):
        q=dest/p.name; shutil.copyfile(p,q)
        if p.read_bytes()!=q.read_bytes(): raise RuntimeError('deck byte mismatch: '+p.name)


def run_one(jar: Path, deck_dir: Path, a: str, b: str, seed: int):
    cmd=['xvfb-run','-a','java','-jar',str(jar.resolve()),'sim','-d',a,b,'-D',str(deck_dir.resolve()),'-n','1','-c',str(CLOCK_SECONDS),'-s',str(seed)]
    try:
        p=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=150,check=False)
        return p.returncode,p.stdout,cmd
    except subprocess.TimeoutExpired as e:
        return 124,(e.stdout or '')+'\nSUBPROCESS_TIMEOUT\n',cmd


def split_cards(s: str):
    if s=='[]': return []
    body=s[1:-1].strip()
    return [x.strip() for x in body.split(',')] if body else []


def analyze_casts(text: str, build: str, opponent: str, seed: int):
    lines=text.splitlines(); battlefield={}; turn=None; phase=None; telemetry=None; out=[]
    for i,line in enumerate(lines):
        mt=TURN.match(line)
        if mt: turn=int(mt.group(1))
        mp=PHASE.match(line)
        if mp: phase=mp.group(1)
        ml=LAND_PLAY.match(line)
        if ml:
            controller,name,cid=ml.groups(); battlefield[cid]={'name':name,'controller':controller}
        mz=ZONE.match(line)
        if mz:
            name,cid,dest,origin=mz.groups()
            if origin=='Battlefield': battlefield.pop(cid,None)
            if dest=='Battlefield': battlefield[cid]={'name':name,'controller':'unknown'}
        mc=CWAI.search(line)
        if mc:
            telemetry={'candidates':split_cards(mc.group(1)),'own_indestructible':split_cards(mc.group(2)),
                       'opposing_high_value':split_cards(mc.group(3)),'selected':mc.group(4),'reason':mc.group(5)}
        m=CAST.search(line)
        if not m: continue
        caster,target=m.groups(); target_name=re.sub(r' \(\d+\)$','',target)
        visible=[f"{v['name']} ({cid})" for cid,v in battlefield.items()]
        own_bridge=[x for x in visible if any(b in x for b in BRIDGES) and 'Jund Wildfire' in next((v['controller'] for cid,v in battlefield.items() if f"{v['name']} ({cid})"==x),'')]
        destroyed=False; retained=True; searcher='unobservable'; resulting=[]
        for later in lines[i+1:min(len(lines),i+12)]:
            zm=ZONE.match(later)
            if zm:
                n,cid,dest,origin=zm.groups()
                if re.sub(r' \(\d+\)$','',target)==n and origin=='Battlefield' and dest=='Graveyard': destroyed=True; retained=False
                if origin=='Library' and dest=='Battlefield': searcher='targeted controller (observed library->battlefield)'
            if later.startswith('Phase:') or later.startswith('Turn:'): break
        if target_name in BRIDGES and not destroyed: cls='self-ramp/card advantage'
        elif target_name in URZA: cls='correct Tron disruption'
        elif telemetry and telemetry.get('reason')=='visible-tron': cls='correct Tron disruption'
        elif target_name not in BRIDGES and target_name not in URZA: cls='replaceable-land targeting'
        else: cls='unobservable'
        out.append({'build':build,'opponent':opponent,'seed':seed,'turn':turn,'phase':phase,'caster':caster,
                    'visible_legal_targets':telemetry['candidates'] if telemetry else visible,
                    'own_indestructible_bridge_available':bool(telemetry['own_indestructible']) if telemetry else bool(own_bridge),
                    'own_indestructible':telemetry['own_indestructible'] if telemetry else own_bridge,
                    'opposing_high_value':telemetry['opposing_high_value'] if telemetry else [],
                    'selected_target':target,'selected_reason':telemetry['reason'] if telemetry else 'stock',
                    'target_retained':retained,'target_destroyed':destroyed,'basic_search':searcher,
                    'resulting_land_color_state':'ordinary log does not expose optional-search chosen card reliably',
                    'classification':cls})
        telemetry=None
    return out


def engine_counts(text: str):
    pats={
      'ichor_wellspring_casts':r'cast Ichor Wellspring\b','deadly_dispute_casts':r'cast Deadly Dispute\b',
      'refurbished_familiar_casts':r'cast Refurbished Familiar\b','writhing_chrysalis_casts':r'cast Writhing Chrysalis\b',
      'eldrazi_spawn_sacrifices':r'Eldrazi Spawn Token .*put into Graveyard from Battlefield',
      'mayhem_devil_casts':r'cast Mayhem Devil\b','cast_down_casts':r'cast Cast Down\b',
      'jund_land_plays':r'Land: Ai\(\d+\)-Jund Wildfire played ',
      'jund_wins':r'Jund Wildfire has won!'}
    return {k:len(re.findall(v,text,re.I)) for k,v in pats.items()}


def wilson(w,n,z=1.959963984540054):
    if not n:return (None,None)
    p=w/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/d
    return max(0,c-h),min(1,c+h)


def run_games(args, phase: str):
    out=args.output; out.mkdir(parents=True,exist_ok=True); (out/'logs').mkdir(exist_ok=True)
    install_decks(args.source_decks,args.deck_dir)
    rows=[]; casts=[]; engines=defaultdict(lambda:defaultdict(int))
    if phase=='gate':
        specs=[('candidate',args.candidate,JUND,'07-esper-control.dck',97001),
               ('candidate',args.candidate,JUND,'08-sultai-beans.dck',97001),
               ('candidate',args.candidate,JUND,'10-tron.dck',97001),
               ('candidate',args.candidate,JUND,'01-white-weenie.dck',97003)]
    else:
        specs=[]
        for build,jar in [('production',args.production),('candidate',args.candidate)]:
            for opp in MATCHUPS:
                for a,b in ((JUND,opp),(opp,JUND)):
                    for seed in SEEDS: specs.append((build,jar,a,b,seed))
        assert len(specs)==96
    for build,jar,a,b,seed in specs:
        rc,text,cmd=run_one(jar,args.deck_dir,a,b,seed)
        log=out/'logs'/f'{build}-{Path(a).stem}-vs-{Path(b).stem}-seed-{seed}.log'; log.write_text(text)
        winner,dur,raw=parse_result(text,a,b); bad=issues(rc,text,winner)
        row={'build':build,'deck_a':a,'deck_b':b,'opponent':b if a==JUND else a,'seed':seed,'winner':winner or 'UNPARSED',
             'duration_ms':dur,'jar_sha256':sha256(jar),'log':str(log),'issues':bad,'command':' '.join(cmd)}
        rows.append(row)
        casts.extend(analyze_casts(text,build,row['opponent'],seed))
        ec=engine_counts(text)
        for k,v in ec.items(): engines[build][k]+=v
        if bad:
            (out/'runtime-failures.json').write_text(json.dumps([row],indent=2)+'\n')
            raise SystemExit('fail-stop: '+','.join(bad))
    (out/'runtime-failures.json').write_text('[]\n')
    (out/'per-game.json').write_text(json.dumps(rows,indent=2)+'\n')
    (out/'wildfire-casts.json').write_text(json.dumps(casts,indent=2)+'\n')
    (out/'engine-counts.json').write_text(json.dumps(engines,indent=2)+'\n')
    if casts:
        with (out/'wildfire-casts.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(casts[0].keys())); w.writeheader(); w.writerows(casts)
    if phase=='gate':
        self_lines=[c for c in casts if c['build']=='candidate' and c['classification']=='self-ramp/card advantage']
        tron=[c for c in casts if c['build']=='candidate' and c['classification']=='correct Tron disruption']
        illegal=[r for r in rows if r['issues']]
        gate={'self_bridge_lines':len(self_lines),'tron_disruption_lines':len(tron),'failures':len(illegal),
              'pass':bool(self_lines) and bool(tron) and not illegal}
        (out/'gate.json').write_text(json.dumps(gate,indent=2)+'\n')
        if not gate['pass']: raise SystemExit('deterministic behavioral gate failed')
    else:
        stats={}
        for build in ('production','candidate'):
            br=[r for r in rows if r['build']==build]; w=sum(r['winner']==JUND for r in br); d=sum(r['winner']=='DRAW' for r in br); n=len(br)-d; lo,hi=wilson(w,n)
            stats[build]={'games':len(br),'wins':w,'draws':d,'decisive':n,'win_rate':w/n if n else None,'wilson95_low':lo,'wilson95_high':hi}
        (out/'win-rates.json').write_text(json.dumps(stats,indent=2)+'\n')
        bad_replace=[c for c in casts if c['build']=='candidate' and c['own_indestructible_bridge_available'] and c['classification']=='replaceable-land targeting']
        acceptance={
          'real_hook_executes':any(c['build']=='candidate' and c['selected_reason']!='stock' for c in casts),
          'non_tron_self_bridge':any(c['build']=='candidate' and c['classification']=='self-ramp/card advantage' and c['opponent']!='10-tron.dck' for c in casts),
          'tron_disruption_preserved':any(c['build']=='candidate' and c['classification']=='correct Tron disruption' for c in casts),
          'no_repeated_replaceable_with_bridge':len(bad_replace)==0,
          'ordinary_fallback_observed':any(c['build']=='candidate' and c['selected_reason'] in ('stock','stock-fallback') for c in casts),
          'all_games_complete_parse':len(rows)==96 and all(not r['issues'] and r['winner']!='UNPARSED' for r in rows),
          'runtime_numeric_illegal_clean':all(not r['issues'] for r in rows),
        }
        acceptance['technically_validated']=all(acceptance.values())
        (out/'acceptance.json').write_text(json.dumps(acceptance,indent=2)+'\n')
    return 0


def main():
    p=argparse.ArgumentParser(); sp=p.add_subparsers(dest='cmd',required=True)
    for name in ('gate','matched'):
        q=sp.add_parser(name); q.add_argument('--production',type=Path,required=True); q.add_argument('--candidate',type=Path,required=True)
        q.add_argument('--source-decks',type=Path,required=True); q.add_argument('--deck-dir',type=Path,required=True); q.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); sys.exit(run_games(a,a.cmd))

if __name__=='__main__': main()
