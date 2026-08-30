#!/usr/bin/env python3
"""Matched-seed stock vs recovered-patch focused Forge validation."""
from pathlib import Path
import argparse, csv, json, re, subprocess, sys
from collections import Counter, defaultdict

MATCHUPS = [
    ("hunting", "white", "09-hunting-storm.dck", "01-white-weenie.dck"),
    ("hunting", "white", "01-white-weenie.dck", "09-hunting-storm.dck"),
    ("hunting", "blue", "09-hunting-storm.dck", "05-blue-terror.dck"),
    ("hunting", "blue", "05-blue-terror.dck", "09-hunting-storm.dck"),
    ("hunting", "jund", "09-hunting-storm.dck", "06-jund-wildfire.dck"),
    ("hunting", "jund", "06-jund-wildfire.dck", "09-hunting-storm.dck"),
    ("tron", "white", "10-tron.dck", "01-white-weenie.dck"),
    ("tron", "white", "01-white-weenie.dck", "10-tron.dck"),
    ("tron", "jund", "10-tron.dck", "06-jund-wildfire.dck"),
    ("tron", "jund", "06-jund-wildfire.dck", "10-tron.dck"),
    ("tron", "blue", "10-tron.dck", "05-blue-terror.dck"),
    ("tron", "blue", "05-blue-terror.dck", "10-tron.dck"),
    ("esper", "white", "07-esper-control.dck", "01-white-weenie.dck"),
    ("esper", "white", "01-white-weenie.dck", "07-esper-control.dck"),
    ("esper", "black", "07-esper-control.dck", "04-black-sacrifice.dck"),
    ("esper", "black", "04-black-sacrifice.dck", "07-esper-control.dck"),
    ("esper", "jund", "07-esper-control.dck", "06-jund-wildfire.dck"),
    ("esper", "jund", "06-jund-wildfire.dck", "07-esper-control.dck"),
]
SEEDS = tuple(range(88001, 88009))
FATAL = re.compile(r"ClassCastException|NullPointerException|ExecutionException|AssertionError|java\.lang\.\w*(?:Exception|Error)|^\s*at\s+forge\.", re.I | re.M)
ILLEGAL = re.compile(r"illegal action|illegal move|cannot legally|not a legal", re.I)
TIMEOUT = re.compile(r"timed out|timeout", re.I)
DECK_LOAD = re.compile(r"No deck found|Could not load deck|match cannot start", re.I)
START = re.compile(r"\b(?:Turn\s+1|Mulligan|Opening Hand|Game\s+1)\b", re.I)
ACTION = re.compile(r"cast|play|activat|sacrific|discard|choose|pay|resolve|mana", re.I)
EVENTS = {
    "filter_action": ("Chromatic Star", "Chromatic Sphere"),
    "hunting_pack": ("Hunting Pack",),
    "tinder_wall": ("Tinder Wall",),
    "tron_land": ("Urza's Mine", "Urza's Tower", "Urza's Power Plant"),
    "prismatic_strands": ("Prismatic Strands",),
    "supreme_verdict": ("Supreme Verdict",),
    "counterspell": ("Counterspell",),
    "removal": ("Cast Down", "Doom Blade", "Journey to Nowhere"),
}


def normalize(s): return re.sub(r"[^a-z0-9]", "", Path(s).stem.lower())

def winner(text):
    m = re.findall(r"Game Result:\s*Game\s+\d+\s+ended in \d+ ms\.\s*(.+?)\s+has won!", text, re.I)
    if not m: m = re.findall(r"Game Outcome:\s*(.+?)\s+has won", text, re.I)
    return m[-1].strip() if m else None


def game_started(text):
    return bool(START.search(text) or winner(text))


def runtime_issues(rc, text, require_result=True):
    bad = []
    if rc: bad.append(f"exit={rc}")
    if DECK_LOAD.search(text): bad.append("deck_load_failure")
    if FATAL.search(text): bad.append("exception_or_stack_trace")
    if ILLEGAL.search(text): bad.append("illegal_action")
    if TIMEOUT.search(text): bad.append("timeout")
    if require_result and not game_started(text): bad.append("game_not_started")
    if require_result and not winner(text): bad.append("unparsed_game")
    return bad


def run(jar, deck_dir, a, b, seed):
    cmd = ["xvfb-run", "-a", "java", "-jar", str(jar), "sim", "-d", a, b,
           "-D", str(deck_dir), "-n", "1", "-c", "120", "-s", str(seed)]
    p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout, " ".join(cmd)


def action_lines(text, cards):
    return [l.strip() for l in text.splitlines() if any(c.lower() in l.lower() for c in cards) and ACTION.search(l)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stock", required=True, type=Path)
    ap.add_argument("--patched", required=True, type=Path)
    ap.add_argument("--deck-dir", default=Path.home() / ".forge" / "decks" / "constructed", type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    rows, failures = [], []
    counters = {"stock": Counter(), "patched": Counter()}
    excerpts = defaultdict(list)
    deck_dir = args.deck_dir.expanduser().resolve()

    pre_a, pre_b = MATCHUPS[0][2], MATCHUPS[0][3]
    missing = [name for name in (pre_a, pre_b) if not (deck_dir / name).is_file()]
    preflights = []
    if missing:
        failures.append({"stage": "preflight", "issues": ["deck_load_failure"], "missing_files": missing})
    else:
        for build, jar in (("stock", args.stock.resolve()), ("patched", args.patched.resolve())):
            rc, text, cmd = run(jar, deck_dir, pre_a, pre_b, 87999)
            log = args.output / f"{build}-preflight.log"
            log.write_text(text, encoding="utf-8")
            issues = runtime_issues(rc, text)
            result = winner(text)
            started = game_started(text)
            loaded = not DECK_LOAD.search(text) and started and result is not None
            record = {"build": build, "deck_a": pre_a, "deck_b": pre_b, "seed": 87999,
                      "command": cmd, "both_decks_loaded": loaded, "match_started": started,
                      "game_result": result, "issues": issues, "pass": not issues and loaded}
            preflights.append(record)
            if issues or not loaded:
                failures.append({"stage": "preflight", "build": build,
                                 "issues": issues or ["deck_load_failure"]})
                break
    (args.output / "preflight.json").write_text(json.dumps(preflights, indent=2) + "\n", encoding="utf-8")
    if failures:
        (args.output / "exceptions-timeouts.json").write_text(json.dumps(failures, indent=2) + "\n", encoding="utf-8")
        (args.output / "comparison.md").write_text(
            "# Focused matched-seed stock vs patched comparison\n\nHARNESS/RUNTIME PREFLIGHT FAILED. A/B games were not started.\n",
            encoding="utf-8",
        )
        print("A/B HARNESS PREFLIGHT FAILED; NO FOCUSED GAMES STARTED")
        return 1

    for build, jar in (("stock", args.stock.resolve()), ("patched", args.patched.resolve())):
        build_dir = args.output / build; build_dir.mkdir(exist_ok=True)
        for idx, (deck, opp, a, b) in enumerate(MATCHUPS, 1):
            for seed in SEEDS:
                rc, text, cmd = run(jar, deck_dir, a, b, seed)
                log = build_dir / f"{idx:02d}-{deck}-{opp}-{Path(a).stem}-vs-{Path(b).stem}-seed-{seed}.log"
                log.write_text(text, encoding="utf-8")
                bad = runtime_issues(rc, text)
                if bad:
                    failures.append({"build": build, "log": str(log), "issues": bad})
                    (args.output / "exceptions-timeouts.json").write_text(json.dumps(failures, indent=2) + "\n", encoding="utf-8")
                    print("A/B VALIDATION STOPPED ON HARNESS/RUNTIME FAILURE")
                    return 1
                w = winner(text)
                normw = normalize(w) if w else ""
                result = "A" if normw and (normalize(a) in normw or normw in normalize(a)) else ("B" if normw and (normalize(b) in normw or normw in normalize(b)) else "unparsed")
                event_row = {}
                for event, cards in EVENTS.items():
                    lines = action_lines(text, cards)
                    event_row[event] = len(lines)
                    counters[build][f"{deck}.{event}"] += len(lines)
                    if lines and len(excerpts[(build, deck, event)]) < 6:
                        excerpts[(build, deck, event)].append({"log": log.name, "seed": seed, "lines": lines[:4]})
                rows.append({"build": build, "deck": deck, "opponent": opp, "orientation": f"{Path(a).stem}__vs__{Path(b).stem}",
                             "seed": seed, "deck_a": a, "deck_b": b, "winner": w or "", "result": result,
                             "log": str(log.relative_to(args.output)), "command": cmd, "game_started": True, **event_row})

    fields = list(rows[0])
    with (args.output / "per-game.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    (args.output / "per-game.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")

    comparison = []
    for deck in ("hunting", "tron", "esper"):
        for event in EVENTS:
            s, p = counters["stock"][f"{deck}.{event}"], counters["patched"][f"{deck}.{event}"]
            comparison.append({"deck": deck, "event": event, "stock": s, "patched": p, "delta": p-s})
    with (args.output / "behavioral-events.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["deck","event","stock","patched","delta"]); w.writeheader(); w.writerows(comparison)
    (args.output / "behavioral-events.json").write_text(json.dumps({"comparison": comparison, "excerpts": {"|".join(k): v for k,v in excerpts.items()}}, indent=2) + "\n", encoding="utf-8")
    (args.output / "exceptions-timeouts.json").write_text(json.dumps(failures, indent=2) + "\n", encoding="utf-8")

    perf = []
    for build in ("stock", "patched"):
        for deck in ("hunting", "tron", "esper"):
            dr = [r for r in rows if r["build"] == build and r["deck"] == deck]
            wins = 0
            for r in dr:
                target_a = (deck == "hunting" and r["deck_a"].startswith("09-")) or (deck == "tron" and r["deck_a"].startswith("10-")) or (deck == "esper" and r["deck_a"].startswith("07-"))
                if (target_a and r["result"] == "A") or ((not target_a) and r["result"] == "B"): wins += 1
            perf.append({"build": build, "deck": deck, "games": len(dr), "wins": wins, "losses": len(dr)-wins, "win_rate": wins/len(dr) if dr else 0})
    (args.output / "directional-performance.json").write_text(json.dumps(perf, indent=2) + "\n", encoding="utf-8")

    indist = []
    target_events = {"hunting": ["filter_action","hunting_pack","tinder_wall"], "tron": ["tron_land","filter_action"], "esper": ["prismatic_strands","supreme_verdict","counterspell","removal"]}
    for deck, evs in target_events.items():
        if all(counters["stock"][f"{deck}.{e}"] == counters["patched"][f"{deck}.{e}"] for e in evs):
            indist.append(deck)
    if indist:
        failures.append({"gate": "behavior_indistinguishable", "decks": indist})
        (args.output / "exceptions-timeouts.json").write_text(json.dumps(failures, indent=2) + "\n", encoding="utf-8")

    md = ["# Focused matched-seed stock vs patched comparison", "",
          "Each condition uses 8 one-game verbose simulations per orientation with the same seed in stock and patched Forge 2.0.14. Total: 144 games/build, 288 games.", "",
          "Deck-loading preflight passed for both stock and patched builds before focused A/B execution.", "",
          "## Directional match performance", "", "| Build | Deck | Games | Wins | Losses | Win rate |", "|---|---|---:|---:|---:|---:|"]
    for p in perf: md.append(f"| {p['build']} | {p['deck']} | {p['games']} | {p['wins']} | {p['losses']} | {p['win_rate']:.1%} |")
    md += ["", "## Behavioral event counters", "", "| Deck | Event | Stock | Patched | Delta |", "|---|---|---:|---:|---:|"]
    for c in comparison: md.append(f"| {c['deck']} | {c['event']} | {c['stock']} | {c['patched']} | {c['delta']:+d} |")
    md += ["", "## Automated safety gates", f"Failures: {len(failures)}"]
    for f in failures: md.append(f"- `{json.dumps(f, sort_keys=True)}`")
    md += ["", "Win rate is reported only as directional context; it is not proof that an AI repair functions."]
    (args.output / "comparison.md").write_text("\n".join(md)+"\n", encoding="utf-8")
    if failures:
        print("A/B VALIDATION FAILED AUTOMATED GATES")
        return 1
    print("A/B AUTOMATED GATES PASSED; verbose behavioral review is still required")
    return 0

if __name__ == "__main__": sys.exit(main())
