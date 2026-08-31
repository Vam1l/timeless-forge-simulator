#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,json,re,subprocess,sys,time
from pathlib import Path

GATE1=[("tron-white","10-tron.dck","01-white-weenie.dck",95001)]
GATE3=[("tron-white","10-tron.dck","01-white-weenie.dck",95001),("white-tron","01-white-weenie.dck","10-tron.dck",95002),("tron-blue","10-tron.dck","05-blue-terror.dck",95003),("blue-tron","05-blue-terror.dck","10-tron.dck",95004),("tron-jund","10-tron.dck","06-jund-wildfire.dck",95005),("jund-tron","06-jund-wildfire.dck","10-tron.dck",95006),("white-green","01-white-weenie.dck","03-green-stompy.dck",95301),("blue-black","05-blue-terror.dck","04-black-sacrifice.dck",95302)]
FATAL=re.compile(r"ClassCastException|NullPointerException|ExecutionException|AssertionError|java\.lang\.\w*(?:Exception|Error)|^\s*at\s+forge\.",re.I|re.M)
BAD=[re.compile(x,re.I) for x in [r"No deck found|Could not load deck|match cannot start",r"illegal action|illegal move|cannot legally|not a legal",r"timed out|timeout"]]
START=re.compile(r"\b(?:Turn\s+1|Mulligan|Opening Hand|Game\s+1)\b",re.I)
WIN=re.compile(r"Game Result:\s*Game\s+\d+\s+ended in \d+ ms\.\s*(.+?)\s+has won!",re.I)
DRAW=re.compile(r"Game Result:.*\b(?:draw|drawn)\b",re.I)
REAL=re.compile(r"\[TRON_CROP_REALPATH\]")
ACT=re.compile(r"\[TRON_CROP_DECISION\].*activated=true.*selected=([^\s]+(?:\s[^#\s]+)?(?:#[0-9]+)?)")
FETCH=re.compile(r"\[TRON_CROP_FETCH\].*selected=([^\s]+(?:\s[^#\s]+)?(?:#[0-9]+)?)")

def sha(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()
def result(t):
 m=WIN.findall(t);return m[-1].strip() if m else ("DRAW" if DRAW.search(t) else None)
def issues(rc,t):
 out=[]
 if rc:out.append(f"exit={rc}")
 if FATAL.search(t):out.append("exception_or_stack_trace")
 if re.search(r"Byte.*Integer|Integer.*Byte",t,re.I):out.append("byte_integer_failure")
 for r,n in zip(BAD,["deck_load_failure","illegal_action","timeout"]):
  if r.search(t):out.append(n)
 if not START.search(t) and result(t) is None:out.append("game_not_started")
 if result(t) is None:out.append("unparsed_result")
 return out
def run(jar,dd,a,b,s):
 cmd=["xvfb-run","-a","java","-jar",str(jar.resolve()),"sim","-d",a,b,"-D",str(dd.resolve()),"-n","1","-c","120","-s",str(s)]
 p=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=150);return p.returncode,p.stdout,cmd

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['gate1','gate3'],required=True);ap.add_argument('--recovered',type=Path,required=True);ap.add_argument('--candidate',type=Path,required=True);ap.add_argument('--deck-dir',type=Path,required=True);ap.add_argument('--source-decks',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--branch-sha',required=True);a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True);(a.output/'logs').mkdir(exist_ok=True)
 conds=GATE1 if a.mode=='gate1' else GATE3;rows=[];fails=[]
 for build,jar in [('recovered',a.recovered),('candidate',a.candidate)]:
  for c,d1,d2,s in conds:
   try:rc,t,cmd=run(jar,a.deck_dir,d1,d2,s)
   except subprocess.TimeoutExpired:fails.append({'build':build,'condition':c,'seed':s,'issues':['timeout']});break
   lp=a.output/'logs'/f'{build}-{c}-seed-{s}.log';lp.write_text(t);bad=issues(rc,t)
   if bad:fails.append({'build':build,'condition':c,'seed':s,'issues':bad,'log':str(lp)});break
   rows.append({'build':build,'condition':c,'deck_a':d1,'deck_b':d2,'seed':s,'winner':result(t),'log':str(lp),'realpath_events':len(REAL.findall(t)),'candidate_activations':len(re.findall(r'\[TRON_CROP_DECISION\].*activated=true',t)),'fetch_events':len(FETCH.findall(t)),'star':len(re.findall(r'Mana: Chromatic Star .*Add',t,re.I)),'sphere':len(re.findall(r'Mana: Chromatic Sphere .*Add',t,re.I)),'refractor':len(re.findall(r'Mana: Energy Refractor .*Add',t,re.I)),'payoffs':len(re.findall(r'cast (?:Mulldrifter|Fangren Marauder|Ulamog\'s Crusher|Rolling Thunder)',t,re.I))})
  if fails:break
 if a.mode=='gate1' and not fails:
  rt=(a.output/'logs'/'recovered-tron-white-seed-95001.log').read_text();ct=(a.output/'logs'/'candidate-tron-white-seed-95001.log').read_text()
  if not REAL.search(rt):fails.append({'issues':['missing_recovered_realpath_telemetry']})
  if not REAL.search(ct):fails.append({'issues':['missing_candidate_realpath_telemetry']})
  acts=re.findall(r'\[TRON_CROP_DECISION\].*activated=true.*selected=([^\n]+)',ct)
  if not acts:fails.append({'issues':['candidate_rule_not_invoked']})
  if acts and not any(('Forest' in x or ("Urza's" not in x and 'none' not in x)) for x in acts):fails.append({'issues':['no_expendable_land_selected']})
  fetches=re.findall(r'\[TRON_CROP_FETCH\].*selected=([^\s#]+(?:\s[^#\s]+)*)#',ct)
  if not fetches or not any(x in ["Urza's Tower","Urza's Power Plant"] for x in fetches):fails.append({'issues':['missing_distinct_piece_not_fetched']})
  # explicit same-piece selection/fetch pairing by ordered telemetry
  sels=re.findall(r'\[TRON_CROP_DECISION\].*activated=true.*selected=([^#\n]+)#',ct)
  if any(x in fetches for x in sels if x.startswith("Urza's")):fails.append({'issues':['same_piece_selection_persisted']})
 (a.output/'per-game.json').write_text(json.dumps(rows,indent=2)+'\n');(a.output/'runtime-failures.json').write_text(json.dumps(fails,indent=2)+'\n');(a.output/'build-identities.json').write_text(json.dumps({'branch_sha':a.branch_sha,'recovered_diag_sha256':sha(a.recovered),'candidate_sha256':sha(a.candidate)},indent=2)+'\n')
 if rows:
  with (a.output/'per-game.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
 (a.output/'gate-report.md').write_text(f'# Phase 4 {a.mode}\n\nGames completed: {len(rows)}/{2 if a.mode=="gate1" else 16}.\nFailures: {len(fails)}.\n')
 return 1 if fails else 0
if __name__=='__main__':sys.exit(main())
