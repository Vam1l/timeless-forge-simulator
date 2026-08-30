#!/usr/bin/env python3
"""Strict fixed-seed behavioral validation for recovered Forge 2.0.14 AI repairs."""
from pathlib import Path
import argparse, json, re, subprocess, sys

FATAL = re.compile(r"ClassCastException|NullPointerException|ExecutionException|AssertionError|java\.lang\.\w*(?:Exception|Error)|^\s*at\s+forge\.", re.I | re.M)
ILLEGAL = re.compile(r"illegal action|illegal move|cannot legally|not a legal", re.I)
TIMEOUT = re.compile(r"timed out|timeout", re.I)
DECK_LOAD = re.compile(r"No deck found|Could not load deck|match cannot start", re.I)
START = re.compile(r"\b(?:Turn\s+1|Mulligan|Opening Hand|Game\s+1)\b", re.I)
PACK_CAST = re.compile(r"^Add To Stack: Ai\(1\)-Hunting Storm cast Hunting Pack\b", re.I | re.M)
FILTER_MANA = re.compile(r"^Mana: Chromatic (?:Star|Sphere) \([^\n]+\) - .*Sacrifice Chromatic (?:Star|Sphere): Add (?:one )?mana", re.I | re.M)
PACK_DISCARD = re.compile(r"^Discard: Ai\(1\)-Hunting Storm discards Hunting Pack\b", re.I | re.M)
DISCARD = re.compile(r"^Discard: Ai\(1\)-Hunting Storm discards (.+?)\s*\(\d+\)\.", re.I | re.M)
HAND_WITH_PACK = re.compile(r"^(?:Hand|Reveal(?:ed)? Hand|Cards in Hand).*Hunting Pack", re.I | re.M)
BYTE_PATH = re.compile(r"ComputerUtilMana.*(?:manaAbilityMap|canPayForShardWithColor|numeric[- ]map|Number\.intValue)", re.I)
TRON_CHOICE_STATE = re.compile(r"(?:choice|choose|selected|candidates?).*(?:Urza|Chromatic)|(?:Urza|Chromatic).*(?:choice|choose|selected|candidates?)", re.I)
ESPER_CHOICE_STATE = re.compile(r"(?:available|alternatives?|choice|choose|selected|candidates?).*(?:Counterspell|Cast Down|Doom Blade|Journey to Nowhere|Prismatic Strands|Supreme Verdict)", re.I)

CORPORA = {
    "hunting": ("09-hunting-storm.dck", "06-jund-wildfire.dck", range(73001, 73013)),
    "tron": ("10-tron.dck", "06-jund-wildfire.dck", range(73101, 73109)),
    "esper": ("07-esper-control.dck", "01-white-weenie.dck", range(73201, 73209)),
}

def winner(text):
    m = re.findall(r"Game Result:\s*Game\s+\d+\s+ended in \d+ ms\.\s*(.+?)\s+has won!", text, re.I)
    if not m: m = re.findall(r"Game Outcome:\s*(.+?)\s+has won", text, re.I)
    return m[-1].strip() if m else None

def game_started(text): return bool(START.search(text) or winner(text))

def runtime_issues(rc, text):
    bad=[]
    if rc: bad.append(f"exit={rc}")
    if DECK_LOAD.search(text): bad.append("deck_load_failure")
    if FATAL.search(text): bad.append("exception_or_stack_trace")
    if ILLEGAL.search(text): bad.append("illegal_action")
    if TIMEOUT.search(text): bad.append("timeout")
    if not game_started(text): bad.append("game_not_started")
    if not winner(text): bad.append("unparsed_game")
    return bad

def run_game(jar, deck_dir, a, b, seed):
    cmd=["xvfb-run","-a","java","-jar",str(jar),"sim","-d",a,b,"-D",str(deck_dir),"-n","1","-c","120","-s",str(seed)]
    p=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    return p.returncode,p.stdout," ".join(cmd)

def exact_filter_activation(text):
    m=FILTER_MANA.search(text)
    return ("demonstrated", m.group(0)) if m else ("failed", None)

def pack_recognition(text):
    m=PACK_CAST.search(text)
    return ("demonstrated", m.group(0)) if m else ("failed", None)

def pack_payoff(text):
    cast=PACK_CAST.search(text)
    if not cast: return "failed", None
    tail=text[cast.start():]
    storm=re.search(r"Resolve Stack: Storm .*\[Card: Hunting Pack\b|Hunting Pack.*Storm", tail, re.I)
    token=re.search(r"(?:Bear Token|create .*2/2.*Bear|Token.*Hunting Pack)", tail, re.I)
    if storm and token:
        return "demonstrated", f"{cast.group(0)} | {storm.group(0)} | {token.group(0)}"
    return "failed", cast.group(0)

def pack_preservation(text):
    if not HAND_WITH_PACK.search(text): return "unobservable", None
    m=DISCARD.search(text)
    if not m: return "unobservable", None
    if PACK_DISCARD.search(text): return "failed", PACK_DISCARD.search(text).group(0)
    return "demonstrated", m.group(0)

def byte_integer_path(text):
    m=BYTE_PATH.search(text)
    if not m: return "unobservable", None
    if "ClassCastException" in text: return "failed", m.group(0)
    return "demonstrated", m.group(0)

def tron_choice(text):
    state=TRON_CHOICE_STATE.search(text)
    if not state: return "unobservable", None
    action=re.search(r"^(?:Mana|Land|Zone Change|Add To Stack): Ai\(1\)-Tron.*$", text[state.end():], re.I|re.M)
    return ("demonstrated", f"{state.group(0)} | {action.group(0)}") if action else ("failed", state.group(0))

def esper_choice(text):
    state=ESPER_CHOICE_STATE.search(text)
    if not state: return "unobservable", None
    action=re.search(r"^Add To Stack: Ai\(1\)-Esper Control cast (?:Counterspell|Cast Down|Doom Blade|Journey to Nowhere|Prismatic Strands|Supreme Verdict)\b.*$", text[state.end():], re.I|re.M)
    return ("demonstrated", f"{state.group(0)} | {action.group(0)}") if action else ("failed", state.group(0))

def write_stop(output, preflight, failures):
    payload={"method":"fixed-seed verbose Forge games","preflight":preflight,"runtime_failures":failures,"scenarios":[],"status":"stopped_before_behavioral_evaluation"}
    (output/"scenarios.json").write_text(json.dumps(payload,indent=2)+"\n")
    (output/"scenarios.md").write_text("# Deterministic functional scenarios\n\nHARNESS/RUNTIME FAILURE — behavioral scenarios not evaluated.\n")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--jar",required=True,type=Path); ap.add_argument("--deck-dir",default=Path.home()/".forge/decks/constructed",type=Path); ap.add_argument("--output",required=True,type=Path)
    args=ap.parse_args(); args.output.mkdir(parents=True,exist_ok=True); jar=args.jar.resolve(); deck_dir=args.deck_dir.expanduser().resolve()
    a,b=CORPORA["hunting"][:2]; pre={"deck_a":a,"deck_b":b,"seed":72999,"deck_dir":str(deck_dir)}
    missing=[n for n in (a,b) if not (deck_dir/n).is_file()]
    if missing: write_stop(args.output,pre,[{"stage":"preflight","issues":["deck_load_failure"],"missing_files":missing}]); return 1
    rc,text,cmd=run_game(jar,deck_dir,a,b,72999); (args.output/"preflight.log").write_text(text); issues=runtime_issues(rc,text); pre.update({"command":cmd,"match_started":game_started(text),"game_result":winner(text),"issues":issues,"pass":not issues}); (args.output/"preflight.json").write_text(json.dumps(pre,indent=2)+"\n")
    if issues: write_stop(args.output,pre,[{"stage":"preflight","issues":issues}]); return 1
    logs={}
    for corpus,(a,b,seeds) in CORPORA.items():
        logs[corpus]=[]
        for seed in seeds:
            rc,text,_=run_game(jar,deck_dir,a,b,seed); path=args.output/f"{corpus}-{seed}.log"; path.write_text(text); issues=runtime_issues(rc,text)
            if issues: write_stop(args.output,pre,[{"log":path.name,"seed":seed,"issues":issues}]); return 1
            logs[corpus].append((seed,path,text))

    specs=[
      ("Hunting Storm available mana-filter activation","hunting",exact_filter_activation,"An explicit Chromatic Star/Sphere mana-ability event is logged."),
      ("Hunting Storm combo-resource preservation","hunting",pack_preservation,"The log identifies Hunting Pack as available in hand and names the alternative card actually discarded."),
      ("Hunting Storm setup/payoff sequence","hunting",pack_payoff,"Hunting Pack is explicitly cast, its Storm/payoff behavior resolves, and resulting tokens are logged."),
      ("Hunting Storm win-condition recognition","hunting",pack_recognition,"Hunting Storm explicitly casts Hunting Pack / places it on the stack."),
      ("Tron multiple mana/filter choices","tron",tron_choice,"The log exposes competing Tron/filter/expendable-land alternatives and the selected action."),
      ("Esper hold-interaction versus removal","esper",esper_choice,"The log exposes the relevant decision state, available alternatives, and selected interaction."),
      ("Byte/Integer numeric mana path","hunting",byte_integer_path,"The verbose log explicitly identifies execution of the previously crashing numeric mana-map path."),
    ]
    scenarios=[]
    for name,corpus,pred,required in specs:
        best=None; statuses=[]
        for seed,path,text in logs[corpus]:
            status,detail=pred(text); statuses.append(status)
            if status=="demonstrated": best=(seed,path,detail,text); break
        if best:
            status="demonstrated"; actual={"seed":best[0],"log":best[1].name,"game_result":winner(best[3]),"evidence":best[2]}
        elif "failed" in statuses:
            status="failed"; actual=None
        else:
            status="unobservable"; actual=None
        scenarios.append({"scenario":name,"required_evidence":required,"status":status,"pass":status=="demonstrated","actual":actual})
    payload={"method":"strict affirmative fixed-seed verbose Forge evidence","preflight":pre,"runtime_failures":[],"scenarios":scenarios}
    (args.output/"scenarios.json").write_text(json.dumps(payload,indent=2)+"\n")
    md=["# Deterministic functional scenarios","","A scenario is PASS only with exact affirmative evidence. Card-name presence, casting a setup artifact, generic resolution text, or a completed game cannot satisfy an unrelated predicate.",""]
    for s in scenarios:
        md += [f"## {s['status'].upper()} — {s['scenario']}",f"Required evidence: {s['required_evidence']}"]
        if s['actual']: md += [f"Seed/log: `{s['actual']['seed']}` / `{s['actual']['log']}`",f"Evidence: `{s['actual']['evidence']}`"]
        else: md += ["No qualifying affirmative evidence was found in the valid started-game corpus."]
        md.append("")
    (args.output/"scenarios.md").write_text("\n".join(md)+"\n")
    not_demo=[s for s in scenarios if not s['pass']]
    if not_demo:
        print("SCENARIO VALIDATION NOT CLEARED; A/B MUST NOT START")
        for s in not_demo: print(f"- {s['status']}: {s['scenario']}")
        return 1
    print("SCENARIO VALIDATION PASSED")
    return 0

if __name__=="__main__": sys.exit(main())
