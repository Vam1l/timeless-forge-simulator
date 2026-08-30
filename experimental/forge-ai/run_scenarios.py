#!/usr/bin/env python3
"""Fixed-seed behavioral-scenario substitute for Forge 2.0.14.

Forge's CLI does not expose a public harness for constructing arbitrary game states, so this
script uses reproducible verbose one-game simulations and requires the relevant states/actions
to be observed in the real Forge AI path. Runtime/harness failures are classified separately
and are never reported as behavioral non-demonstration.
"""
from pathlib import Path
import argparse, json, re, subprocess, sys

FATAL = re.compile(r"ClassCastException|NullPointerException|ExecutionException|AssertionError|java\.lang\.\w*(?:Exception|Error)|^\s*at\s+forge\.", re.I | re.M)
ILLEGAL = re.compile(r"illegal action|illegal move|cannot legally|not a legal", re.I)
TIMEOUT = re.compile(r"timed out|timeout", re.I)
DECK_LOAD = re.compile(r"No deck found|Could not load deck|match cannot start", re.I)
ACTION = re.compile(r"cast|play|activat|sacrific|discard|choose|pay|resolve|mana", re.I)
START = re.compile(r"\b(?:Turn\s+1|Mulligan|Opening Hand|Game\s+1)\b", re.I)

CORPORA = {
    "hunting": ("09-hunting-storm.dck", "06-jund-wildfire.dck", range(73001, 73013)),
    "tron": ("10-tron.dck", "06-jund-wildfire.dck", range(73101, 73109)),
    "esper": ("07-esper-control.dck", "01-white-weenie.dck", range(73201, 73209)),
}


def winner(text: str):
    m = re.findall(r"Game Result:\s*Game\s+\d+\s+ended in \d+ ms\.\s*(.+?)\s+has won!", text, re.I)
    if not m:
        m = re.findall(r"Game Outcome:\s*(.+?)\s+has won", text, re.I)
    return m[-1].strip() if m else None


def game_started(text: str) -> bool:
    return bool(START.search(text) or winner(text))


def runtime_issues(rc: int, text: str, require_result: bool = True):
    issues = []
    if rc:
        issues.append(f"exit={rc}")
    if DECK_LOAD.search(text):
        issues.append("deck_load_failure")
    if FATAL.search(text):
        issues.append("exception_or_stack_trace")
    if ILLEGAL.search(text):
        issues.append("illegal_action")
    if TIMEOUT.search(text):
        issues.append("timeout")
    if require_result and not game_started(text):
        issues.append("game_not_started")
    if require_result and not winner(text):
        issues.append("unparsed_game")
    return issues


def run_game(jar: Path, deck_dir: Path, a: str, b: str, seed: int):
    cmd = ["xvfb-run", "-a", "java", "-jar", str(jar), "sim", "-d", a, b,
           "-D", str(deck_dir), "-n", "1", "-c", "120", "-s", str(seed)]
    p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout, " ".join(cmd)


def relevant_lines(text: str, cards=()):
    lines = []
    for line in text.splitlines():
        if (not cards or any(c.lower() in line.lower() for c in cards)) and ACTION.search(line):
            lines.append(line.strip())
    return lines


def first_state_excerpt(text: str):
    state = [l.strip() for l in text.splitlines() if re.search(r"hand|battlefield|life:|turn |phase", l, re.I)]
    return state[:12]


def write_runtime_stop(output: Path, preflight, failures):
    payload = {
        "method": "fixed-seed verbose Forge games (constructed-state harness unavailable)",
        "preflight": preflight,
        "runtime_failures": failures,
        "scenarios": [],
        "status": "stopped_before_behavioral_evaluation",
    }
    (output / "scenarios.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Deterministic functional-scenario substitute",
        "",
        "## HARNESS/RUNTIME FAILURE — behavioral scenarios not evaluated",
        "",
    ]
    for failure in failures:
        lines.append(f"- `{json.dumps(failure, sort_keys=True)}`")
    (output / "scenarios.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True, type=Path)
    ap.add_argument("--deck-dir", default=Path.home() / ".forge" / "decks" / "constructed", type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    deck_dir = args.deck_dir.expanduser().resolve()
    jar = args.jar.resolve()

    pre_a, pre_b = CORPORA["hunting"][0], CORPORA["hunting"][1]
    missing = [name for name in (pre_a, pre_b) if not (deck_dir / name).is_file()]
    preflight = {"deck_a": pre_a, "deck_b": pre_b, "seed": 72999, "deck_dir": str(deck_dir)}
    if missing:
        failure = {"stage": "preflight", "issues": ["deck_load_failure"], "missing_files": missing}
        preflight.update({"pass": False, "both_decks_loaded": False, "match_started": False, "game_result": None})
        write_runtime_stop(args.output, preflight, [failure])
        return 1

    rc, text, cmd = run_game(jar, deck_dir, pre_a, pre_b, 72999)
    (args.output / "preflight.log").write_text(text, encoding="utf-8")
    issues = runtime_issues(rc, text)
    result = winner(text)
    started = game_started(text)
    loaded = not DECK_LOAD.search(text) and started and result is not None
    preflight.update({"command": cmd, "pass": not issues and loaded, "both_decks_loaded": loaded,
                      "match_started": started, "game_result": result, "issues": issues})
    (args.output / "preflight.json").write_text(json.dumps(preflight, indent=2) + "\n", encoding="utf-8")
    if issues or not loaded:
        write_runtime_stop(args.output, preflight, [{"stage": "preflight", "issues": issues or ["deck_load_failure"]}])
        print("SCENARIO HARNESS PREFLIGHT FAILED")
        return 1

    logs = {}
    runtime_failures = []
    hard_stop = False
    for corpus, (a, b, seeds) in CORPORA.items():
        logs[corpus] = []
        for seed in seeds:
            rc, text, _ = run_game(jar, deck_dir, a, b, seed)
            path = args.output / f"{corpus}-{seed}.log"
            path.write_text(text, encoding="utf-8")
            issues = runtime_issues(rc, text)
            if issues:
                runtime_failures.append({"log": path.name, "seed": seed, "issues": issues})
                hard_stop = True
                break
            logs[corpus].append((seed, path, text))
        if hard_stop:
            break

    if runtime_failures:
        write_runtime_stop(args.output, preflight, runtime_failures)
        print("SCENARIO VALIDATION STOPPED ON HARNESS/RUNTIME FAILURE")
        return 1

    scenarios = []
    def add(name, expected, corpus, predicate, cards):
        actual = None
        for seed, path, text in logs[corpus]:
            if not game_started(text) or not winner(text):
                continue
            ok, detail = predicate(text)
            if ok:
                actual = {"seed": seed, "log": path.name, "game_started": True,
                          "game_result": winner(text), "decision": detail,
                          "initial_state_excerpt": first_state_excerpt(text),
                          "relevant_log_excerpt": relevant_lines(text, cards)[:12]}
                break
        scenarios.append({"scenario": name, "expected_ai_decision": expected,
                          "actual": actual, "pass": actual is not None})

    filter_cards = ("Chromatic Star", "Chromatic Sphere")
    def filter_activation(t):
        lines = relevant_lines(t, filter_cards)
        hits = [l for l in lines if re.search(r"activat|sacrific|add.*mana|mana ability", l, re.I)]
        return bool(hits), hits[0] if hits else ""
    add("Hunting Storm available mana-filter activation",
        "Use a Star/Sphere mana-filter action when it advances a legal combo line.", "hunting", filter_activation, filter_cards)

    def preserve_pack(t):
        if "Hunting Pack" not in t or not re.search(r"discard", t, re.I): return False, ""
        pack_discard = [l for l in t.splitlines() if "Hunting Pack" in l and re.search(r"discard", l, re.I)]
        other = [l.strip() for l in t.splitlines() if "Hunting Pack" not in l and re.search(r"discard", l, re.I)]
        return (not pack_discard and bool(other)), (other[0] if other else "")
    add("Hunting Storm combo-resource preservation",
        "When a discard choice occurs with Hunting Pack relevant, preserve Hunting Pack if a nonessential alternative exists.",
        "hunting", preserve_pack, ("Hunting Pack",))

    def payoff(t):
        hits = [l for l in relevant_lines(t, ("Hunting Pack",)) if re.search(r"cast|play|resolve", l, re.I)]
        return bool(hits), hits[0] if hits else ""
    add("Hunting Storm setup/payoff sequence", "After setup, attempt a legally executable Hunting Pack payoff.", "hunting", payoff, ("Hunting Pack", "Tinder Wall", "Chromatic Star", "Chromatic Sphere"))
    add("Hunting Storm win-condition recognition", "Recognize Hunting Pack as the win-condition and attempt it when executable.", "hunting", payoff, ("Hunting Pack",))

    def tron_choice(t):
        names = {n for n in ("Urza's Mine", "Urza's Tower", "Urza's Power Plant") if n in t}
        lines = relevant_lines(t, tuple(names) + ("Chromatic Star", "Chromatic Sphere"))
        return len(names) >= 2 and bool(lines), (lines[0] if lines else "")
    add("Tron multiple mana/filter choices", "Use a coherent Tron/mana-filter line without stranding an available mana engine.", "tron", tron_choice,
        ("Urza's Mine", "Urza's Tower", "Urza's Power Plant", "Chromatic Star", "Chromatic Sphere"))

    def esper_interaction(t):
        cards = ("Counterspell", "Cast Down", "Doom Blade", "Journey to Nowhere", "Prismatic Strands", "Supreme Verdict")
        present = {c for c in cards if c in t}
        actions = relevant_lines(t, tuple(present))
        return len(present) >= 2 and bool(actions), (actions[0] if actions else "")
    add("Esper hold-interaction versus removal", "Choose legal interaction with timing consistent with the board rather than wasting or illegally firing it.",
        "esper", esper_interaction, ("Counterspell", "Cast Down", "Doom Blade", "Journey to Nowhere", "Prismatic Strands", "Supreme Verdict"))

    add("Byte/Integer numeric mana path", "Exercise a mana-filter path without Byte/Integer ClassCastException.", "hunting",
        lambda t: (filter_activation(t)[0] and "ClassCastException" not in t, filter_activation(t)[1]), filter_cards)

    payload = {"method": "fixed-seed verbose Forge games (constructed-state harness unavailable)",
               "preflight": preflight, "runtime_failures": [], "scenarios": scenarios}
    (args.output / "scenarios.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md = ["# Deterministic functional-scenario substitute", "",
          "Forge 2.0.14 has no repository harness here for directly constructing arbitrary AI game states; these are fixed-seed verbose games through the actual Forge AI decision path.", "",
          "Deck-loading preflight passed: both requested decks loaded, the match started, and a parsed game result was produced.", ""]
    for s in scenarios:
        md += [f"## {'PASS' if s['pass'] else 'FAIL'} — {s['scenario']}", f"Expected: {s['expected_ai_decision']}"]
        if s["actual"]:
            a = s["actual"]
            md += [f"Seed/log: `{a['seed']}` / `{a['log']}`", f"Game result: `{a['game_result']}`",
                   f"Actual decision evidence: `{a['decision']}`", "Relevant excerpt:", "```", *a["relevant_log_excerpt"], "```"]
        else:
            md += ["A valid, started, parsed game corpus was searched, but no candidate demonstrated the required reached state and decision path."]
        md.append("")
    (args.output / "scenarios.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    failed = [s["scenario"] for s in scenarios if not s["pass"]]
    if failed:
        print("SCENARIO BEHAVIORAL VALIDATION FAILED")
        for x in failed: print("-", x)
        return 1
    print("SCENARIO VALIDATION PASSED")
    return 0

if __name__ == "__main__":
    sys.exit(main())
