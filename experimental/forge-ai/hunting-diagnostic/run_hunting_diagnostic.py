#!/usr/bin/env python3
"""Bounded Hunting Storm vs Jund diagnostic using telemetry-only Forge overlay."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

FATAL = re.compile(r"ClassCastException|NullPointerException|ExecutionException|AssertionError|java\.lang\.\w*(?:Exception|Error)|^\s*at\s+forge\.", re.I | re.M)
ILLEGAL = re.compile(r"illegal action|illegal move|cannot legally|not a legal", re.I)
TIMEOUT = re.compile(r"timed out|timeout", re.I)
DECK_LOAD = re.compile(r"No deck found|Could not load deck|match cannot start", re.I)
START = re.compile(r"\b(?:Turn\s+1|Mulligan|Opening Hand|Game\s+1)\b", re.I)
RESULT = re.compile(r"Game Result:\s*Game\s+\d+\s+ended in \d+ ms\.\s*(.+?)\s+has won!", re.I)
PACK_CAST = re.compile(r"^Add To Stack: Ai\(1\)-Hunting Storm cast Hunting Pack\b.*$", re.I | re.M)
PACK_PAYOFF = re.compile(r"Resolve Stack: Storm .*Hunting Pack|Hunting Pack.*Storm", re.I)
PACK_TOKEN = re.compile(r"Bear Token|create .*2/2.*Bear|Token.*Hunting Pack", re.I)
PACK_LOST = re.compile(r"(?:Discard: Ai\(1\)-Hunting Storm discards Hunting Pack|Hunting Pack.*(?:Exile|Graveyard)|(?:Exile|Graveyard).*Hunting Pack)", re.I)
DIAG = re.compile(r"^HUNTING_DIAG\|(.*)$", re.M)


def parse_diag(text: str):
    out=[]
    for m in DIAG.finditer(text):
        fields={}
        for part in m.group(1).split("|"):
            if "=" in part:
                k,v=part.split("=",1); fields[k]=v
        out.append(fields)
    return out


def runtime_issues(rc: int, text: str):
    bad=[]
    if rc: bad.append(f"exit={rc}")
    if DECK_LOAD.search(text): bad.append("deck_load_failure")
    if FATAL.search(text): bad.append("exception_or_stack_trace")
    if ILLEGAL.search(text): bad.append("illegal_action")
    if TIMEOUT.search(text): bad.append("timeout")
    if not (START.search(text) or RESULT.search(text)): bad.append("game_not_started")
    if not RESULT.search(text): bad.append("unparsed_game")
    return bad


def run_game(jar: Path, deck_dir: Path, a: str, b: str, seed: int):
    cmd=["xvfb-run","-a","java","-jar",str(jar),"sim","-d",a,b,"-D",str(deck_dir),"-n","1","-c","120","-s",str(seed)]
    p=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    return p.returncode,p.stdout," ".join(cmd)


def classify_game(text: str, diag):
    final=[d for d in diag if d.get("event")=="final_decision" and d.get("decision")=="WillPlay"]
    evals=[d for d in diag if d.get("event")=="ai_evaluation"]
    costs=[d for d in diag if d.get("event")=="cost_check"]
    cast=PACK_CAST.search(text)
    payoff=bool(cast and PACK_PAYOFF.search(text[cast.start():]) and PACK_TOKEN.search(text[cast.start():]))
    opportunity=bool(final and costs and any(d.get("decision")=="payable" for d in costs))
    if opportunity and cast:
        status="repair demonstrated"
    elif opportunity and not cast:
        status="repair failed"
    elif evals and not final:
        status="unobservable"
    else:
        status="no reachable opportunity in game"
    return status, opportunity, cast.group(0) if cast else None, payoff


def evidence_excerpt(text: str):
    lines=text.splitlines()
    keep=[]
    for i,line in enumerate(lines):
        if "HUNTING_DIAG|" in line or "Hunting Pack" in line or "Chromatic Star" in line or "Chromatic Sphere" in line or "Tinder Wall" in line or "Add To Stack:" in line or "Mana:" in line:
            keep.append(f"{i+1}: {line}")
    return keep[-80:]


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--jar",required=True,type=Path)
    ap.add_argument("--deck-dir",default=Path.home()/".forge/decks/constructed",type=Path)
    ap.add_argument("--output",required=True,type=Path)
    ap.add_argument("--start-seed",type=int,default=74001)
    args=ap.parse_args(); args.output.mkdir(parents=True,exist_ok=True)
    deck_dir=args.deck_dir.expanduser().resolve(); jar=args.jar.resolve()
    hunting="09-hunting-storm.dck"; jund="06-jund-wildfire.dck"
    for name in (hunting,jund):
        if not (deck_dir/name).is_file():
            raise SystemExit(f"missing installed deck: {name}")

    games=[]; opportunities=[]; runtime_failure=None
    conditions=[]
    for i in range(30):
        seed=args.start_seed+i
        if i%2==0: a,b=hunting,jund
        else: a,b=jund,hunting
        conditions.append((seed,a,b))

    for seed,a,b in conditions:
        rc,text,cmd=run_game(jar,deck_dir,a,b,seed)
        log=args.output/f"seed-{seed}-{Path(a).stem}-vs-{Path(b).stem}.log"
        log.write_text(text,encoding="utf-8")
        bad=runtime_issues(rc,text)
        diag=parse_diag(text)
        if bad:
            runtime_failure={"seed":seed,"log":log.name,"issues":bad}
            games.append({"seed":seed,"orientation":f"{a} vs {b}","classification":"runtime failure","issues":bad,"log":log.name,"command":cmd})
            break
        status,opp,cast,payoff=classify_game(text,diag)
        row={"seed":seed,"orientation":f"{a} vs {b}","classification":status,"legally_castable_opportunity":opp,"cast_event":cast,"payoff_resolved":payoff,"telemetry":diag,"hunting_pack_lost_later":bool(PACK_LOST.search(text)),"log":log.name,"command":cmd,"chronological_excerpt":evidence_excerpt(text)}
        games.append(row)
        if opp:
            opportunities.append(row)
            if len(opportunities)>=3:
                break

    if runtime_failure:
        overall="runtime failure"
    elif opportunities:
        if any(g["cast_event"] for g in opportunities): overall="repair demonstrated"
        elif all(g["classification"]=="repair failed" for g in opportunities): overall="repair failed"
        else: overall="unobservable"
    elif any(g["telemetry"] for g in games):
        overall="no reachable test state"
    else:
        overall="unobservable"

    payload={"scope":"Hunting Storm vs Jund only","max_games":30,"clock_seconds":120,"early_stop":"3 independently reached legally castable Hunting Pack states","games_run":len(games),"opportunities":len(opportunities),"overall_classification":overall,"runtime_failure":runtime_failure,"games":games}
    (args.output/"diagnostic-results.json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    md=["# Hunting Storm bounded diagnostic","",f"Overall classification: **{overall}**",f"Games run: **{len(games)} / 30**",f"Legally castable opportunities observed: **{len(opportunities)} / 3 early-stop target**","","| Seed | Orientation | Classification | Cast | Payoff |", "|---:|---|---|---|---|"]
    for g in games:
        md.append(f"| {g['seed']} | {g['orientation']} | {g['classification']} | {'yes' if g.get('cast_event') else 'no'} | {'yes' if g.get('payoff_resolved') else 'no'} |")
    md += ["","## Claimed opportunities"]
    if not opportunities: md.append("No game established all required legal-playability gates within the bounded search.")
    for g in opportunities:
        md += ["",f"### Seed {g['seed']}","```",*g["chronological_excerpt"],"```"]
    md += ["","## Reproduction","",f"`python experimental/forge-ai/hunting-diagnostic/run_hunting_diagnostic.py --jar forge-hunting-diagnostic.jar --deck-dir $HOME/.forge/decks/constructed --output hunting-diagnostic-results --start-seed {args.start_seed}`"]
    (args.output/"report.md").write_text("\n".join(md)+"\n",encoding="utf-8")
    print(f"HUNTING DIAGNOSTIC COMPLETE: {overall}; games={len(games)} opportunities={len(opportunities)}")
    return 1 if runtime_failure else 0


if __name__=="__main__":
    sys.exit(main())
