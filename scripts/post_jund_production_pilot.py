#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,json,math,re,shutil,subprocess,sys,statistics
from pathlib import Path

DECKS=["01-white-weenie.dck","02-madness-burn.dck","03-green-stompy.dck","04-black-sacrifice.dck","05-blue-terror.dck","06-jund-wildfire.dck","07-esper-control.dck","08-sultai-beans.dck","09-hunting-storm.dck","10-tron.dck"]
SEEDS=list(range(97001,97011)); CLOCK=120
EXPECTED_MAIN="5a58621b797365aeedcc60d05da7d6b945ed7a32"
EXPECTED_TREE="9a025696bae4a5b1d7ade6e05e5757737ae280fb"
EXPECTED_DECK_TREE="3d55da96aa15ea6a7da5ed2cf98e7ff6417bee35"
EXPECTED_TRON_TREE="902ba2cf23e746469bccdeb59817d41cd16e913d"
FATAL=re.compile(r"ClassCastException|NullPointerException|ExecutionException|AssertionError|java\.lang\.\w*(?:Exception|Error)|^\s*at\s+forge\.",re.I|re.M)
BADNUM=re.compile(r"Byte.*Integer|Integer.*Byte|numeric[-_ ]map",re.I)
DECKLOAD=re.compile(r"No deck found|Could not load deck|match cannot start",re.I)
ILLEGAL=re.compile(r"illegal action|illegal move|illegal target|cannot legally|not a legal",re.I)
RESULT=re.compile(r"Game Result:\s*Game\s+\d+\s+ended in\s+(\d+)\s+ms\.\s*(.+?)\s+has won!",re.I)
TURN=re.compile(r"Turn: Turn (\d+)",re.I)
CAST=re.compile(r"Add To Stack: (Ai\(\d+\)-.+?) cast Cleansing Wildfire targeting \[(.+?) \((\d+)\)\]",re.I)
LAND=re.compile(r"Land: (Ai\(\d+\)-.+?) played (.+?) \((\d+)\)")
ZONE=re.compile(r"Zone Change: (.+?) \((\d+)\) was put into (\w+) from (\w+)")
MANA=re.compile(r"Mana: (.+?) \((\d+)\) - .*Add",re.I)
PHASE=re.compile(r"Phase: (.+)")
URZA={"Urza's Mine","Urza's Power Plant","Urza's Tower"}; BRIDGES={"Drossforge Bridge","Slagwoods Bridge"}

def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''): h.update(c)
 return h.hexdigest()

def normalize(s:str)->str:
 s=re.sub(r"^Ai\(\d+\)-","",s.strip(),flags=re.I); s=re.sub(r"^\d+[-_ ]*","",Path(s).stem.lower()); return re.sub(r"[^a-z0-9]","",s)

def label(d:str)->str: return re.sub(r"^\d+[-_]","",Path(d).stem).replace('-',' ').title()

def orientations():
 out=[]; pair=0; oid=0
 for i in range(10):
  for j in range(i+1,10):
   pair+=1
   for a,b in ((DECKS[i],DECKS[j]),(DECKS[j],DECKS[i])):
    out.append(dict(pair_id=pair,orientation_id=oid,deck_a=a,deck_b=b,canonical_a=DECKS[i],canonical_b=DECKS[j])); oid+=1
 assert len(out)==90; return out

def conditions_for_batch(batch:int):
 os=orientations(); start=batch*10; chosen=os[start:start+10]
 assert len(chosen)==10
 return [{**o,'seed':s,'condition_id':f"o{o['orientation_id']:02d}-s{s}"} for o in chosen for s in SEEDS]

def install_decks(src:Path,dst:Path):
 dst.mkdir(parents=True,exist_ok=True)
 for d in DECKS:
  a=src/d; b=dst/d
  if not a.is_file(): raise RuntimeError(f'missing deck {d}')
  shutil.copyfile(a,b)
  if a.read_bytes()!=b.read_bytes(): raise RuntimeError(f'deck identity mismatch {d}')

def parse_winner(text,a,b):
 m=list(RESULT.finditer(text))
 if not m:return None,None,None
 dur=int(m[-1].group(1)); raw=m[-1].group(2).strip(); n=normalize(raw)
 for d in (a,b):
  nd=normalize(d)
  if n==nd or n in nd or nd in n:return d,dur,raw
 return None,dur,raw

def issues(rc,text,winner,timed_out=False):
 x=[]
 if timed_out:x.append('subprocess_timeout')
 if rc not in (0,None):x.append(f'exit={rc}')
 if FATAL.search(text):x.append('java_exception_or_stack_trace')
 if BADNUM.search(text):x.append('byte_integer_or_numeric_map_failure')
 if DECKLOAD.search(text):x.append('deck_load_failure')
 if ILLEGAL.search(text):x.append('illegal_action_or_target')
 if winner is None:x.append('unparsed_result')
 return x

def run_one(jar,deckdir,a,b,seed):
 cmd=['xvfb-run','-a','java','-jar',str(jar.resolve()),'sim','-d',a,b,'-D',str(deckdir.resolve()),'-n','1','-c',str(CLOCK),'-s',str(seed)]
 try:
  p=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=150,check=False)
  return p.returncode,p.stdout,cmd,False
 except subprocess.TimeoutExpired as e:
  out=(e.stdout or '')+(e.stderr or '') if isinstance(e.stdout,str) else ''
  return None,out,cmd,True

def engine_counts(text):
 names=['Ichor Wellspring','Deadly Dispute','Refurbished Familiar','Writhing Chrysalis','Mayhem Devil','Cast Down','Crop Rotation','Mulldrifter','Fangren Marauder','Rolling Thunder','Moment\'s Peace','Weather the Storm','Ulamog\'s Crusher','Prismatic Strands','Guardian of the Guildpact','Brainstorm','Ponder','Tolarian Terror','Sneaky Snacker','Basking Rootwalla','Fiery Temper','Young Wolf','Nest Invader','Sadistic Glee','Tithing Blade','Up the Beanstalk','Troll of Khazad-dûm']
 return {re.sub(r'[^a-z0-9]+','_',n.lower()).strip('_')+'_casts':len(re.findall(r'cast '+re.escape(n)+r'\b',text,re.I)) for n in names}

def hunting_counts(text):
 return {'hunting_pack_casts':len(re.findall(r'cast Hunting Pack\b',text,re.I)),'hunting_pack_triggered':len(re.findall(r'triggered Hunting Pack\b',text,re.I)),'beast_mentions':len(re.findall(r'4/4 green Beast',text,re.I))}

def run_preflight(args):
 args.output.mkdir(parents=True,exist_ok=True); (args.output/'logs').mkdir(exist_ok=True); install_decks(args.source_decks,args.deck_dir)
 rc,text,cmd,to=run_one(args.forge_jar,args.deck_dir,'06-jund-wildfire.dck','10-tron.dck',96999)
 log=args.output/'logs/preflight-jund-vs-tron-seed-96999.log'; log.write_text(text)
 w,d,raw=parse_winner(text,'06-jund-wildfire.dck','10-tron.dck'); bad=issues(rc,text,w,to)
 row={'condition_id':'preflight','seed':96999,'deck_a':'06-jund-wildfire.dck','deck_b':'10-tron.dck','winner':w,'winner_raw':raw,'duration_ms':d,'command':cmd,'issues':bad,'jar_sha256':sha256(args.forge_jar)}
 (args.output/'preflight.json').write_text(json.dumps(row,indent=2)+'\n'); (args.output/'runtime-failures.json').write_text(json.dumps(([row] if bad else []),indent=2)+'\n')
 return 1 if bad else 0

def run_batch(args):
 args.output.mkdir(parents=True,exist_ok=True); logs=args.output/'logs'; logs.mkdir(exist_ok=True); install_decks(args.source_decks,args.deck_dir)
 rows=[]; fails=[]; manifest=[]
 for c in conditions_for_batch(args.batch):
  rc,text,cmd,to=run_one(args.forge_jar,args.deck_dir,c['deck_a'],c['deck_b'],c['seed'])
  lp=logs/f"{c['condition_id']}-{Path(c['deck_a']).stem}-vs-{Path(c['deck_b']).stem}.log"; lp.write_text(text)
  w,d,raw=parse_winner(text,c['deck_a'],c['deck_b']); bad=issues(rc,text,w,to); turns=max([int(x) for x in TURN.findall(text)] or [0])
  row={**c,'winner':w or 'UNPARSED','loser':(c['deck_b'] if w==c['deck_a'] else c['deck_a'] if w==c['deck_b'] else ''),'winner_raw':raw or '','turns':turns,'duration_ms':d if d is not None else '','command':' '.join(cmd),'log':str(lp),**engine_counts(text),**hunting_counts(text)}
  rows.append(row); manifest.append({'condition_id':c['condition_id'],'log':str(lp),'log_sha256':sha256(lp),'command':cmd})
  if bad:
   fails.append({**row,'issues':bad}); break
 if rows:
  with (args.output/'per-game.csv').open('w',newline='') as f: wri=csv.DictWriter(f,fieldnames=list(rows[0])); wri.writeheader(); wri.writerows(rows)
 (args.output/'per-game.json').write_text(json.dumps(rows,indent=2)+'\n'); (args.output/'runtime-failures.json').write_text(json.dumps(fails,indent=2)+'\n'); (args.output/'batch-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 (args.output/'identity.json').write_text(json.dumps({'production_main':EXPECTED_MAIN,'production_tree':EXPECTED_TREE,'deck_tree':EXPECTED_DECK_TREE,'tron_tree':EXPECTED_TRON_TREE,'jar_sha256':sha256(args.forge_jar),'batch':args.batch,'seeds':SEEDS,'clock':CLOCK},indent=2)+'\n')
 return 1 if fails or len(rows)!=100 else 0

def wilson(w,n,z=1.959963984540054):
 if n==0:return (None,None)
 p=w/n; den=1+z*z/n; ctr=(p+z*z/(2*n))/den; half=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/den; return max(0,ctr-half),min(1,ctr+half)

def summarize(rows,decks):
 out=[]
 for d in decks:
  rr=[r for r in rows if d in (r['deck_a'],r['deck_b']) and all(x in decks for x in (r['deck_a'],r['deck_b']))]
  w=sum(r['winner']==d for r in rr); l=len(rr)-w; lo,hi=wilson(w,len(rr)); first=[r for r in rr if r['deck_a']==d]; second=[r for r in rr if r['deck_b']==d]; lens=[int(r['turns']) for r in rr if str(r.get('turns','')).isdigit()]
  out.append({'deck':d,'name':label(d),'games':len(rr),'wins':w,'losses':l,'win_rate':w/len(rr) if rr else None,'wilson95_low':lo,'wilson95_high':hi,'first_wins':sum(r['winner']==d for r in first),'first_losses':len(first)-sum(r['winner']==d for r in first),'second_wins':sum(r['winner']==d for r in second),'second_losses':len(second)-sum(r['winner']==d for r in second),'median_turns':statistics.median(lens) if lens else None})
 return out

def matchup_matrix(rows,decks):
 out=[]
 for i,a in enumerate(decks):
  for b in decks[i+1:]:
   rr=[r for r in rows if {r['deck_a'],r['deck_b']}=={a,b}]; wa=sum(r['winner']==a for r in rr); out.append({'deck_a':a,'deck_b':b,'games':len(rr),'a_wins':wa,'b_wins':len(rr)-wa,'a_win_rate':wa/len(rr) if rr else None})
 return out

def wildfire_audit(logs_root:Path):
 casts=[]; anomalies=[]
 for lp in sorted(logs_root.rglob('*.log')):
  text=lp.read_text(errors='replace')
  if 'Jund Wildfire' not in text or 'Cleansing Wildfire' not in text: continue
  turn=0; phase=''; bridges={}; urza={}; lines=text.splitlines()
  for idx,line in enumerate(lines,1):
   m=TURN.search(line); turn=int(m.group(1)) if m else turn
   m=PHASE.match(line); phase=m.group(1) if m else phase
   m=LAND.match(line)
   if m:
    ctrl,name,cid=m.groups()
    if 'Jund Wildfire' in ctrl and name in BRIDGES: bridges[cid]=name
    elif 'Jund Wildfire' not in ctrl and name in URZA: urza[cid]=name
   m=ZONE.match(line)
   if m:
    name,cid,dest,origin=m.groups()
    if origin=='Battlefield': bridges.pop(cid,None); urza.pop(cid,None)
    if dest=='Battlefield':
     if name in BRIDGES: bridges[cid]=name
     if name in URZA: urza[cid]=name
   m=MANA.match(line)
   if m:
    name,cid=m.groups()
    if name in URZA: urza[cid]=name
    if name in BRIDGES: bridges[cid]=name
   m=CAST.search(line)
   if not (m and 'Jund Wildfire' in m.group(1)): continue
   tn,tid=m.group(2),m.group(3); types=sorted(set(urza.values())); own=[{'id':i,'name':n} for i,n in sorted(bridges.items())]
   if len(types)>=2: cls='visible-Tron disruption' if tn in URZA else 'demonstrated targeting defect'
   elif tid in bridges: cls='self-Bridge ramp'
   elif not own: cls='legitimate no-Bridge stock fallback'
   elif own: cls='ordinary replaceable-land target'
   else: cls='ambiguous target'
   row={'log':lp.name,'line':idx,'turn':turn,'phase':phase,'active_own_indestructible':own,'active_opposing_urza_by_id':[{'id':i,'name':n} for i,n in sorted(urza.items())],'distinct_urza_types':types,'target':{'id':tid,'name':tn},'classification':cls,'evidence':line}
   casts.append(row)
   if cls in ('ordinary replaceable-land target','ambiguous target','demonstrated targeting defect'): anomalies.append(row)
 return casts,anomalies

def aggregate(args):
 args.output.mkdir(parents=True,exist_ok=True); rows=[]; failures=[]; manifests=[]; ids=[]
 for b in range(9):
  candidates=list(args.input.rglob(f'pilot-batch-{b}/per-game.json'))
  if len(candidates)!=1: failures.append({'batch':b,'issues':['missing_or_duplicate_batch_artifact'],'found':[str(x) for x in candidates]}); continue
  rows+=json.loads(candidates[0].read_text()); failures+=json.loads((candidates[0].parent/'runtime-failures.json').read_text()); manifests+=json.loads((candidates[0].parent/'batch-manifest.json').read_text()); ids.append(json.loads((candidates[0].parent/'identity.json').read_text()))
 expected={f'o{o:02d}-s{s}' for o in range(90) for s in SEEDS}; got=[r['condition_id'] for r in rows]
 identity_ok=bool(ids) and all(i==ids[0] or all(i[k]==ids[0][k] for k in ('production_main','production_tree','deck_tree','tron_tree','jar_sha256','seeds','clock')) for i in ids)
 integ={'expected_conditions':900,'rows':len(rows),'unique_conditions':len(set(got)),'complete_matrix':set(got)==expected,'duplicates':len(got)-len(set(got)),'missing':sorted(expected-set(got)),'runtime_failures':len(failures),'replacement_games':0,'identity_parity':identity_ok,'pass':len(rows)==900 and len(set(got))==900 and set(got)==expected and not failures and identity_ok}
 (args.output/'integrity.json').write_text(json.dumps(integ,indent=2)+'\n'); (args.output/'runtime-failures.json').write_text(json.dumps(failures,indent=2)+'\n'); (args.output/'batch-manifests.json').write_text(json.dumps(manifests,indent=2)+'\n'); (args.output/'per-game.json').write_text(json.dumps(rows,indent=2)+'\n')
 if rows:
  with (args.output/'per-game.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 if not integ['pass']:
  (args.output/'acceptance.json').write_text(json.dumps({'technical_integrity':False,'balance_reporting_allowed':False},indent=2)+'\n'); (args.output/'report.md').write_text('# Post-Jund production pilot\n\nTechnical integrity: **FAIL**. Balance analysis suppressed.\n'); return 1
 full=summarize(rows,DECKS); nine=[d for d in DECKS if d!='09-hunting-storm.dck']; eight=[d for d in nine if d!='10-tron.dck']
 views={'ten_deck':full,'nine_deck':summarize(rows,nine),'eight_deck':summarize(rows,eight),'ten_matchups':matchup_matrix(rows,DECKS),'nine_matchups':matchup_matrix(rows,nine),'eight_matchups':matchup_matrix(rows,eight)}
 (args.output/'balance-views.json').write_text(json.dumps(views,indent=2)+'\n')
 casts,anom=wildfire_audit(args.input); (args.output/'jund-wildfire-audit.json').write_text(json.dumps({'casts':casts,'anomalies':anom},indent=2)+'\n')
 hunting=[r for r in rows if '09-hunting-storm.dck' in (r['deck_a'],r['deck_b'])]; hunting_summary={'games':len(hunting),'wins':sum(r['winner']=='09-hunting-storm.dck' for r in hunting),'losses':sum(r['winner']!='09-hunting-storm.dck' for r in hunting),'hunting_pack_casts':sum(int(r.get('hunting_pack_casts',0)) for r in hunting),'storm_trigger_events':sum(int(r.get('hunting_pack_triggered',0)) for r in hunting),'beast_mentions':sum(int(r.get('beast_mentions',0)) for r in hunting),'simulated_record_suitable_for_human_balance':False}; (args.output/'hunting-storm-summary.json').write_text(json.dumps(hunting_summary,indent=2)+'\n')
 (args.output/'acceptance.json').write_text(json.dumps({'technical_integrity':True,'games':900,'wildfire_casts':len(casts),'wildfire_anomalies_requiring_review':len(anom),'balance_reporting_allowed':True},indent=2)+'\n')
 md=['# Authoritative post-Jund production balance pilot','','Technical integrity: **PASS** (900/900 unique expected conditions, zero recorded hard failures).','','## Ten-deck field']
 for r in full: md.append(f"- {r['name']}: {r['wins']}-{r['losses']} ({r['win_rate']:.1%}; Wilson 95% {r['wilson95_low']:.1%}–{r['wilson95_high']:.1%})")
 md+=['','## Nine-deck functional field']
 for r in views['nine_deck']: md.append(f"- {r['name']}: {r['wins']}-{r['losses']} ({r['win_rate']:.1%}; Wilson 95% {r['wilson95_low']:.1%}–{r['wilson95_high']:.1%})")
 md+=['','## Jund Wildfire audit',f"- Casts classified: {len(casts)}",f"- Anomalous/ambiguous requiring manual review: {len(anom)}",'','## Hunting Storm','- Included for runtime continuity only; simulated record is unsuitable for human balance judgment.']
 (args.output/'report.md').write_text('\n'.join(md)+'\n'); return 0

def main():
 p=argparse.ArgumentParser(); sp=p.add_subparsers(dest='mode',required=True)
 for mode in ('preflight','batch'):
  q=sp.add_parser(mode); q.add_argument('--forge-jar',type=Path,required=True);q.add_argument('--source-decks',type=Path,required=True);q.add_argument('--deck-dir',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
  if mode=='batch':q.add_argument('--batch',type=int,choices=range(9),required=True)
 q=sp.add_parser('aggregate');q.add_argument('--input',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
 a=p.parse_args(); return run_preflight(a) if a.mode=='preflight' else run_batch(a) if a.mode=='batch' else aggregate(a)
if __name__=='__main__':sys.exit(main())
