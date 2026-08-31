#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,json,re,subprocess,sys
from pathlib import Path

GATE1=[("tron-white","10-tron.dck","01-white-weenie.dck",95001)]
GATE3=[("tron-white","10-tron.dck","01-white-weenie.dck",95001),("white-tron","01-white-weenie.dck","10-tron.dck",95002),("tron-blue","10-tron.dck","05-blue-terror.dck",95003),("blue-tron","05-blue-terror.dck","10-tron.dck",95004),("tron-jund","10-tron.dck","06-jund-wildfire.dck",95005),("jund-tron","06-jund-wildfire.dck","10-tron.dck",95006),("white-green","01-white-weenie.dck","03-green-stompy.dck",95301),("blue-black","05-blue-terror.dck","04-black-sacrifice.dck",95302)]
FATAL=re.compile(r"ClassCastException|NullPointerException|ExecutionException|AssertionError|java\.lang\.\w*(?:Exception|Error)|^\s*at\s+forge\.",re.I|re.M)
BAD=[re.compile(x,re.I) for x in [r"No deck found|Could not load deck|match cannot start",r"illegal action|illegal move|cannot legally|not a legal",r"timed out|timeout"]]
START=re.compile(r"\b(?:Turn\s+1|Mulligan|Opening Hand|Game\s+1)\b",re.I)
WIN=re.compile(r"Game Result:\s*Game\s+\d+\s+ended in \d+ ms\.\s*(.+?)\s+has won!",re.I)
DRAW=re.compile(r"Game Result:.*\b(?:draw|drawn)\b",re.I)
REAL_LINE=re.compile(r"^\[TRON_CROP_REALPATH\].*$",re.M)
DECISION_LINE=re.compile(r"^\[TRON_CROP_DECISION\].*$",re.M)
FETCH_LINE=re.compile(r"^\[TRON_CROP_FETCH\].*$",re.M)
CARD_ID=re.compile(r"(?P<name>.+)#(?P<id>\d+)$")


def sha(p):
    h=hashlib.sha256()
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

def field(line,key,next_key=None):
    start=line.find(key+'=')
    if start<0:return None
    start+=len(key)+1
    if next_key:
        end=line.find(' '+next_key+'=',start)
        if end>=0:return line[start:end]
    return line[start:]

def parse_fetch_line(line):
    keys=['host','hostId','api','path','origin','destination','legalCandidates','controlledLands','tronPresent','tronMissing','missingAvailable','selected','classification']
    out={}
    for i,k in enumerate(keys):out[k]=field(line,k,keys[i+1] if i+1<len(keys) else None)
    return out

def parse_decision_line(line):
    out={'raw':line}
    for key in ['activated','reason','allowed','selected']:
        m=re.search(r'(?:^| )'+re.escape(key)+r'=([^ ]+(?: [^ ]+)*?)(?= [A-Za-z]+\w*=|$)',line)
        if m:out[key]=m.group(1)
    return out

def crop_events(text):
    return {
        'realpath':[x for x in REAL_LINE.findall(text)],
        'decisions':[parse_decision_line(x) for x in DECISION_LINE.findall(text)],
        'fetches':[parse_fetch_line(x) for x in FETCH_LINE.findall(text)],
    }

def selected_card(decisions):
    for d in decisions:
        if d.get('activated')=='true' and d.get('selected') and d.get('selected')!='none':
            m=CARD_ID.match(d['selected'])
            if m:return m.group('name'),int(m.group('id'))
    return None

def actual_sacrifice(text,name,cid):
    pat=rf"Zone Change: {re.escape(name)} \({cid}\) was put into Graveyard from Battlefield\."
    return re.search(pat,text) is not None

def mine_to_mine_telemetry(events):
    sacrifices=[]
    for d in events['decisions']:
        if d.get('activated')=='true' and d.get('selected'):
            m=CARD_ID.match(d['selected'])
            if m:sacrifices.append(m.group('name'))
    fetches=[f.get('selected','').rsplit('#',1)[0] for f in events['fetches'] if f.get('selected') not in (None,'none')]
    return any(s.startswith("Urza's") and s in fetches for s in sacrifices)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['gate1','gate3'],required=True);ap.add_argument('--recovered',type=Path);ap.add_argument('--candidate',type=Path,required=True);ap.add_argument('--deck-dir',type=Path,required=True);ap.add_argument('--source-decks',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--branch-sha',required=True);a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True);(a.output/'logs').mkdir(exist_ok=True)
    conds=GATE1 if a.mode=='gate1' else GATE3;rows=[];fails=[];all_events=[]
    builds=[('candidate',a.candidate)] if a.mode=='gate1' else [('recovered',a.recovered),('candidate',a.candidate)]
    if a.mode=='gate3' and a.recovered is None:raise SystemExit('--recovered required for gate3')
    for build,jar in builds:
        for c,d1,d2,s in conds:
            try:rc,t,cmd=run(jar,a.deck_dir,d1,d2,s)
            except subprocess.TimeoutExpired:fails.append({'build':build,'condition':c,'seed':s,'issues':['timeout']});break
            lp=a.output/'logs'/f'{build}-{c}-seed-{s}.log';lp.write_text(t);bad=issues(rc,t)
            if bad:fails.append({'build':build,'condition':c,'seed':s,'issues':bad,'log':str(lp)});break
            ev=crop_events(t);all_events.append({'build':build,'condition':c,'seed':s,**ev})
            rows.append({'build':build,'condition':c,'deck_a':d1,'deck_b':d2,'seed':s,'winner':result(t),'log':str(lp),'realpath_events':len(ev['realpath']),'candidate_activations':sum(1 for d in ev['decisions'] if d.get('activated')=='true'),'fetch_events':len(ev['fetches']),'star':len(re.findall(r'Mana: Chromatic Star .*Add',t,re.I)),'sphere':len(re.findall(r'Mana: Chromatic Sphere .*Add',t,re.I)),'refractor':len(re.findall(r'Mana: Energy Refractor .*Add',t,re.I)),'payoffs':len(re.findall(r"cast (?:Mulldrifter|Fangren Marauder|Ulamog's Crusher|Rolling Thunder)",t,re.I))})
        if fails:break
    if a.mode=='gate1' and not fails:
        ct=(a.output/'logs'/'candidate-tron-white-seed-95001.log').read_text();ev=crop_events(ct)
        if not ev['realpath']:fails.append({'issues':['missing_candidate_realpath_telemetry']})
        chosen=selected_card(ev['decisions'])
        if chosen is None:fails.append({'issues':['candidate_rule_not_invoked']})
        elif chosen[0].startswith("Urza's"):fails.append({'issues':['no_expendable_land_selected'],'selected':chosen[0]})
        elif not actual_sacrifice(ct,*chosen):fails.append({'issues':['selected_land_not_actually_sacrificed'],'selected':chosen})
        if not ev['fetches']:fails.append({'issues':['missing_direct_fetch_telemetry']})
        else:
            direct=[f for f in ev['fetches'] if f.get('classification')=='missing_distinct_piece']
            if not direct:fails.append({'issues':['missing_distinct_piece_not_fetched'],'fetches':ev['fetches']})
        # The known unique Mine is card 35 in deterministic seed 95001. It must not be paid as the Crop cost
        # and remains observable after resolution in the ordinary game log.
        if re.search(r"Zone Change: Urza's Mine \(35\) was put into Graveyard from Battlefield\.",ct):fails.append({'issues':['unique_mine_was_sacrificed']})
        if not re.search(r"Mana: Urza's Mine \(35\)",ct):fails.append({'issues':['unique_mine_not_observed_after_crop']})
        if mine_to_mine_telemetry(ev):fails.append({'issues':['same_piece_selection_persisted']})
    (a.output/'per-game.json').write_text(json.dumps(rows,indent=2)+'\n');(a.output/'crop-events.json').write_text(json.dumps(all_events,indent=2)+'\n');(a.output/'runtime-failures.json').write_text(json.dumps(fails,indent=2)+'\n');ids={'branch_sha':a.branch_sha,'candidate_sha256':sha(a.candidate)}
    if a.recovered is not None:ids['recovered_diag_sha256']=sha(a.recovered)
    (a.output/'build-identities.json').write_text(json.dumps(ids,indent=2)+'\n')
    if rows:
        with (a.output/'per-game.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    expected=1 if a.mode=='gate1' else 16
    (a.output/'gate-report.md').write_text(f'# Phase 4 verification {a.mode}\n\nGames completed: {len(rows)}/{expected}.\nFailures: {len(fails)}.\n')
    return 1 if fails else 0
if __name__=='__main__':sys.exit(main())
