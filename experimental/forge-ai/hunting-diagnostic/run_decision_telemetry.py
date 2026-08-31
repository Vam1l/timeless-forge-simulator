#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re,subprocess
from pathlib import Path

CONDS=[('white','09-hunting-storm.dck','01-white-weenie.dck'),('white','01-white-weenie.dck','09-hunting-storm.dck'),('blue','09-hunting-storm.dck','05-blue-terror.dck'),('blue','05-blue-terror.dck','09-hunting-storm.dck'),('jund','09-hunting-storm.dck','06-jund-wildfire.dck'),('jund','06-jund-wildfire.dck','09-hunting-storm.dck')]
FATAL=re.compile(r'ClassCastException|NullPointerException|ExecutionException|AssertionError|java\.lang\.\w*(?:Exception|Error)|^\s*at\s+forge\.',re.I|re.M)
BAD=[('deck_load_failure',re.compile(r'No deck found|Could not load deck|match cannot start',re.I)),('illegal_action',re.compile(r'illegal action|illegal move|cannot legally|not a legal',re.I)),('timeout',re.compile(r'timed out|timeout',re.I))]
RESULT=re.compile(r'Game Result:\s*Game\s+\d+\s+ended in (\d+) ms\.\s*(.+?)\s+has won!',re.I)
DIAG=re.compile(r'^HUNTING_DIAG\|(.*)$',re.M)
CAST=re.compile(r'^Add To Stack: Ai\(\d+\)-Hunting Storm cast Hunting Pack\b.*$',re.M)
TRIGGER=re.compile(r'^Add To Stack: Ai\(\d+\)-Hunting Storm triggered Hunting Pack\b.*$',re.M)
TOKEN=re.compile(r'Resolve Stack: Hunting Pack .*creates a 4/4 green Beast creature token',re.I)

def parse_diag(t):
 out=[]
 for m in DIAG.finditer(t):
  d={}
  for p in m.group(1).split('|'):
   if '=' in p: k,v=p.split('=',1); d[k]=v
  out.append(d)
 return out

def original_casts(lines):
 n=0
 for i,l in enumerate(lines):
  if CAST.match(l) and any(TRIGGER.match(x) for x in lines[i+1:i+3]): n+=1
 return n

def classify_diag(d):
 states=[]
 for i,x in enumerate(d):
  if x.get('event')!='evaluate': continue
  turn,phase=x.get('turn'),x.get('phase')
  following=[y for y in d[i+1:] if y.get('turn')==turn and y.get('phase')==phase]
  ev=next((y for y in following if y.get('event')=='ai_evaluation'),None)
  cost=next((y for y in following if y.get('event')=='cost_check'),None)
  final=next((y for y in following if y.get('event')=='final_decision'),None)
  candidates=[y for y in d if y.get('turn')==turn and y.get('phase')==phase and y.get('event') in ('candidate_enter','candidate_result')]
  complete=bool(ev and ((ev.get('decision')!='WillPlay') or (cost and final)))
  states.append({'evaluate':x,'ai_evaluation':ev,'cost_check':cost,'final_decision':final,'candidate_events':candidates,'fully_observable':complete})
 return states

def run(jar,deckdir,a,b,seed):
 cmd=['xvfb-run','-a','java','-jar',str(jar),'sim','-d',a,b,'-D',str(deckdir),'-n','1','-c','120','-s',str(seed)]
 p=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 return p.returncode,p.stdout,' '.join(cmd)

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--jar',required=True,type=Path); ap.add_argument('--deck-dir',required=True,type=Path); ap.add_argument('--output',required=True,type=Path); ap.add_argument('--start-seed',type=int,default=93001)
 a=ap.parse_args(); a.output.mkdir(parents=True,exist_ok=True); deck=a.deck_dir.expanduser().resolve(); jar=a.jar.resolve()
 games=[]; observed=[]; runtime=None
 for i in range(24):
  opp,x,y=CONDS[i%6]; seed=a.start_seed+i
  rc,t,cmd=run(jar,deck,x,y,seed); log=a.output/f'{i+1:02d}-{opp}-{Path(x).stem}__vs__{Path(y).stem}-seed-{seed}.log'; log.write_text(t)
  issues=[]
  if rc: issues.append(f'exit={rc}')
  if FATAL.search(t): issues.append('exception_or_stack_trace')
  for name,rx in BAD:
   if rx.search(t): issues.append(name)
  rm=RESULT.search(t)
  if not rm: issues.append('unparsed_game')
  if issues:
   runtime={'seed':seed,'log':log.name,'issues':issues}; games.append({'seed':seed,'opponent':opp,'orientation':f'{x} vs {y}','classification':'runtime failure','issues':issues,'log':log.name,'command':cmd}); break
  d=parse_diag(t); states=classify_diag(d); complete=[s for s in states if s['fully_observable']]
  lines=t.splitlines(); orig=original_casts(lines); allcasts=len(CAST.findall(t)); copies=max(0,allcasts-orig); tokens=len(TOKEN.findall(t))
  row={'seed':seed,'opponent':opp,'orientation':f'{x} vs {y}','winner':rm.group(2),'duration_ms':int(rm.group(1)),'original_hunting_pack_casts':orig,'storm_copy_stack_events':copies,'beast_tokens':tokens,'decision_states':states,'fully_observable_states':len(complete),'log':log.name,'command':cmd}
  games.append(row)
  if complete:
   observed.append(row)
   if len(observed)>=3: break
 overall='runtime failure' if runtime else ('observable decision states captured' if len(observed)>=3 else 'insufficient telemetry')
 out={'scope':'patched-only Hunting Storm decision telemetry','max_games':24,'clock_seconds':120,'games_run':len(games),'fully_observable_games':len(observed),'overall':overall,'runtime_failure':runtime,'games':games}
 (a.output/'decision-results.json').write_text(json.dumps(out,indent=2)+'\n')
 md=['# Hunting Storm decision telemetry','',f'Overall: **{overall}**',f'Games run: **{len(games)} / 24**',f'Games with fully observable Hunting Pack decisions: **{len(observed)}**','','| Seed | Opponent | Orientation | Original casts | Storm-copy stack events | Beast tokens | Observable states |','|---:|---|---|---:|---:|---:|---:|']
 for g in games: md.append(f"| {g['seed']} | {g['opponent']} | {g['orientation']} | {g.get('original_hunting_pack_casts',0)} | {g.get('storm_copy_stack_events',0)} | {g.get('beast_tokens',0)} | {g.get('fully_observable_states',0)} |")
 md+=['','The original-cast counter requires an explicit Hunting Pack cast immediately followed by its Storm trigger; later copy stack events are counted separately.','', '## Reproduction',f'`python experimental/forge-ai/hunting-diagnostic/run_decision_telemetry.py --jar forge-hunting-decision-telemetry.jar --deck-dir $HOME/.forge/decks/constructed --output decision-results --start-seed {a.start_seed}`']
 (a.output/'report.md').write_text('\n'.join(md)+'\n')
 print(f'DECISION TELEMETRY COMPLETE: {overall}; games={len(games)} observable={len(observed)}')
 return 1 if runtime else 0
if __name__=='__main__': raise SystemExit(main())
