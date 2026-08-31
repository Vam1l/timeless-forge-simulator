#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import argparse,csv,hashlib,json,re,subprocess,sys
H='09-hunting-storm.dck'; C=[('white',H,'01-white-weenie.dck'),('white','01-white-weenie.dck',H),('blue',H,'05-blue-terror.dck'),('blue','05-blue-terror.dck',H),('jund',H,'06-jund-wildfire.dck'),('jund','06-jund-wildfire.dck',H)]; S=range(91001,91009)
WIN=re.compile(r'Game Result:\s*Game\s+\d+\s+ended in\s+(\d+)\s+ms\.\s*(.+?)\s+has won!',re.I); DRAW=re.compile(r'Game Result:.*?(?:draw|drawn)',re.I); START=re.compile(r'\b(?:Turn\s+1|Mulligan|Opening Hand|Game\s+1)\b',re.I); TURN=re.compile(r'\bTurn\s+(\d+)\b',re.I)
DECK=re.compile(r'No deck found|Could not load deck|match cannot start',re.I); FATAL=re.compile(r'ClassCastException|NullPointerException|ExecutionException|AssertionError|java\.lang\.\w*(?:Exception|Error)|^\s*at\s+forge\.',re.I|re.M); BYTE=re.compile(r'ClassCastException.*(?:Byte|Integer)|(?:Byte|Integer).*ClassCastException',re.I|re.S); ILLEGAL=re.compile(r'illegal action|illegal move|cannot legally|not a legal',re.I); TMO=re.compile(r'timed out|timeout',re.I); STALL=re.compile(r'\bstall(?:ed|ing)?\b|infinite loop',re.I)
CAST=re.compile(r'^Add To Stack: Ai\(\d+\)-Hunting Storm cast Hunting Pack\b.*$',re.I|re.M); STORM=re.compile(r'Resolve Stack: Storm .*Hunting Pack|Hunting Pack.*Storm',re.I); BEAST=re.compile(r'Resolve Stack: Hunting Pack .*creates a 4/4 green Beast creature token',re.I); FILT=re.compile(r'^Mana: Chromatic (Star|Sphere).*Sacrifice Chromatic \1: Add one mana of any color',re.I|re.M); DISC=re.compile(r'^Discard: Ai\(\d+\)-Hunting Storm discards Hunting Pack.*$',re.I|re.M); EXILE=re.compile(r'^(?!.*Add To Stack:).*Hunting Pack.*\bExile\b|\bExile\b.*Hunting Pack',re.I|re.M); GRAVE=re.compile(r'^(?!.*Add To Stack:).*Hunting Pack.*\bGraveyard\b|\bGraveyard\b.*Hunting Pack',re.I|re.M)
def sha(p):
 h=hashlib.sha256(); f=open(p,'rb')
 for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 f.close(); return h.hexdigest()
def norm(x): return re.sub('[^a-z0-9]','',Path(x).stem.lower())
def result(t):
 m=list(WIN.finditer(t))
 if m:return True,m[-1].group(2).strip(),False,int(m[-1].group(1))
 if DRAW.search(t):return True,'',True,None
 return False,'',False,None
def loop(t):
 c=Counter(x.strip() for x in t.splitlines() if len(x.strip())>20 and any(k in x.lower() for k in ('add to stack','resolve stack','mana:','priority'))); return any(v>=80 for v in c.values())
def issues(rc,t,to):
 parsed,_,_,_=result(t); b=[]
 if to:b+=['timeout']
 if rc:b+=[f'exit={rc}']
 if DECK.search(t):b+=['deck_load_failure']
 if BYTE.search(t):b+=['byte_integer_failure']
 if FATAL.search(t):b+=['exception_or_stack_trace']
 if ILLEGAL.search(t):b+=['illegal_action']
 if TMO.search(t):b+=['timeout']
 if STALL.search(t) or loop(t):b+=['stall_or_loop']
 if not (START.search(t) or parsed):b+=['game_not_started']
 if not parsed:b+=['unparsed_game']
 return list(dict.fromkeys(b))
def events(t):
 f=FILT.findall(t); cast=len(CAST.findall(t)); d=len(DISC.findall(t)); e=len(EXILE.findall(t)); g=len(GRAVE.findall(t)); beasts=len(BEAST.findall(t))
 return {'pack_casts':cast,'storm_resolutions':len(STORM.findall(t)),'beast_tokens':beasts,'star_mana_activations':sum(x.lower()=='star' for x in f),'sphere_mana_activations':sum(x.lower()=='sphere' for x in f),'pack_discards':d,'pack_exiles':e,'pack_graveyard':g,'pack_lost_without_cast':int(cast==0 and d+e+g>0)}
def run(jar,dd,a,b,s):
 common=['sim','-d',a,b,'-D',str(dd),'-n','1','-c','120','-s',str(s)]; cmd=['xvfb-run','-a','java','-jar',str(jar),*common]
 try:
  p=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=150); return p.returncode,p.stdout,' '.join(cmd),common,False
 except subprocess.TimeoutExpired as e:
  x=e.stdout or ''; x=x.decode('utf8','replace') if isinstance(x,bytes) else x; return 124,x,' '.join(cmd),common,True
def outcome(w,draw):
 if draw:return 'draw'
 n=norm(w); h=norm(H); return 'win' if n and (h in n or n in h) else 'loss'
def main():
 p=argparse.ArgumentParser(); p.add_argument('--stock',type=Path,required=True);p.add_argument('--patched',type=Path,required=True);p.add_argument('--deck-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--branch-sha',required=True);p.add_argument('--recovered-ai-sha',required=True);a=p.parse_args(); o=a.output;o.mkdir(parents=True,exist_ok=True);dd=a.deck_dir.expanduser().resolve();stock=a.stock.resolve();patched=a.patched.resolve(); failures=[];rows=[];pairs=[]
 ids={'branch_sha':a.branch_sha,'recovered_ai_sha':a.recovered_ai_sha,'forge_version':'2.0.14','stock_jar_sha256':sha(stock),'patched_jar_sha256':sha(patched),'seeds':list(S),'clock_seconds':120};(o/'build-identities.json').write_text(json.dumps(ids,indent=2)+'\n')
 miss=[x for x in {H,'01-white-weenie.dck','05-blue-terror.dck','06-jund-wildfire.dck'} if not(dd/x).is_file()]
 if miss: failures=[{'stage':'deck_preflight','issues':['deck_load_failure'],'missing':miss}];(o/'exceptions-timeouts-unparsed.json').write_text(json.dumps(failures,indent=2)+'\n');return 1
 for ci,(opp,x,y) in enumerate(C,1):
  orient=f'{Path(x).stem}__vs__{Path(y).stem}'
  for seed in S:
   pair=[]; ref=None
   for build,jar in [('stock',stock),('patched',patched)]:
    rc,t,cmd,common,to=run(jar,dd,x,y,seed); ld=o/'logs'/build;ld.mkdir(parents=True,exist_ok=True);log=ld/f'{ci:02d}-{opp}-{orient}-seed-{seed}.log';log.write_text(t)
    if ref is None:ref=common
    elif common!=ref:failures.append({'stage':'settings','condition':ci,'seed':seed,'issues':['settings_mismatch']})
    bad=issues(rc,t,to);parsed,w,draw,dur=result(t);ev=events(t); turns=max([int(z) for z in TURN.findall(t)]or[0]);r={'build':build,'condition':ci,'opponent':opp,'orientation':orient,'seed':seed,'deck_a':x,'deck_b':y,'parsed':parsed,'winner':w,'draw':draw,'hunting_result':outcome(w,draw)if parsed else'unparsed','duration_ms':dur or'','turns_completed':turns,'log':str(log.relative_to(o)),'command':cmd,**ev};rows.append(r);pair.append(r)
    if bad or failures:
     if bad:failures.append({'stage':'game','build':build,'condition':ci,'seed':seed,'log':r['log'],'issues':bad})
     (o/'per-game.json').write_text(json.dumps(rows,indent=2)+'\n');(o/'exceptions-timeouts-unparsed.json').write_text(json.dumps(failures,indent=2)+'\n');return 1
   pairs.append(pair)
 fields=list(rows[0]); f=open(o/'per-game.csv','w',newline='');w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows);f.close();(o/'per-game.json').write_text(json.dumps(rows,indent=2)+'\n');(o/'exceptions-timeouts-unparsed.json').write_text('[]\n')
 evf=['pack_casts','storm_resolutions','beast_tokens','star_mana_activations','sphere_mana_activations','pack_discards','pack_exiles','pack_graveyard','pack_lost_without_cast']; counters=[]
 for build in ('stock','patched'):
  br=[r for r in rows if r['build']==build];z={'build':build,'games':len(br)};z.update({e:sum(r[e] for r in br)for e in evf});counters.append(z)
 (o/'behavioral-event-counters.json').write_text(json.dumps(counters,indent=2)+'\n');f=open(o/'behavioral-event-counters.csv','w',newline='');w=csv.DictWriter(f,fieldnames=list(counters[0]));w.writeheader();w.writerows(counters);f.close()
 summ=[]
 for build in ('stock','patched'):
  for ci,(opp,x,y) in enumerate(C,1):
   q=[r for r in rows if r['build']==build and r['condition']==ci];c=Counter(r['hunting_result']for r in q);summ.append({'build':build,'opponent':opp,'orientation':q[0]['orientation'],'games':8,'wins':c['win'],'losses':c['loss'],'draws':c['draw']})
 (o/'stock-vs-patched-summary.json').write_text(json.dumps(summ,indent=2)+'\n')
 review=[]
 for s,pa in pairs:
  div=any(s[k]!=pa[k]for k in ['hunting_result',*evf]); mandatory=s['seed']in list(S)[:2]or s['pack_casts']or pa['pack_casts']or div
  if mandatory:review.append({'condition':s['condition'],'opponent':s['opponent'],'orientation':s['orientation'],'seed':s['seed'],'stock_log':s['log'],'patched_log':pa['log'],'stock_result':s['hunting_result'],'patched_result':pa['hunting_result'],'stock_events':{k:s[k]for k in evf},'patched_events':{k:pa[k]for k in evf},'behavioral_divergence':div})
 (o/'review-index.json').write_text(json.dumps(review,indent=2)+'\n');md=['# Matched-seed review index','',f'{len(review)} matched pairs require review (first two seeds/condition + all casts + all divergences).','']+[f"- condition {r['condition']} {r['opponent']} {r['orientation']} seed {r['seed']}: `{r['stock_log']}` / `{r['patched_log']}`"for r in review];(o/'matched-log-review.md').write_text('\n'.join(md)+'\n')
 totals={}
 for build in ('stock','patched'):
  q=[r for r in rows if r['build']==build];c=Counter(r['hunting_result']for r in q);e=next(z for z in counters if z['build']==build);totals[build]={'w':c['win'],'l':c['loss'],'d':c['draw'],'rate':c['win']/48,**e}
 md=['# Hunting Storm focused matched-seed A/B','','Directional validation only; 48 games/build, 96 total. No statistical-significance claim.','','| Build | W | L | D | Win rate | Pack casts | Storm | Beast tokens | Star mana | Sphere mana |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
 for b in ('stock','patched'):
  z=totals[b];md.append(f"| {b} | {z['w']} | {z['l']} | {z['d']} | {z['rate']:.1%} | {z['pack_casts']} | {z['storm_resolutions']} | {z['beast_tokens']} | {z['star_mana_activations']} | {z['sphere_mana_activations']} |")
 md+=['','## Runtime safety','All 96 games parsed without hard-stop failures.','','Non-casts are observational only; they are not AI failures unless a log independently proves a legally executable opportunity was declined.','','## Reproduction',f'`python experimental/forge-ai/hunting-focused-ab.py --stock forge-stock.jar --patched forge-patched.jar --deck-dir $HOME/.forge/decks/constructed --output hunting-focused-ab-results --branch-sha {a.branch_sha} --recovered-ai-sha {a.recovered_ai_sha}`'];(o/'report.md').write_text('\n'.join(md)+'\n');return 0
if __name__=='__main__':sys.exit(main())
