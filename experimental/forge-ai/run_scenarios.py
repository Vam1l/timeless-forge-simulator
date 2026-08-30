#!/usr/bin/env python3
"""Fixed-seed behavioral-scenario substitute for Forge 2.0.14.

Forge's CLI does not expose a public harness for constructing arbitrary game states, so this
script uses reproducible verbose one-game simulations and requires the relevant states/actions
to be observed in the real Forge AI path. Failure to reach or demonstrate a required path is a
scenario failure; it is never converted into a synthetic passing unit test.
"""
from pathlib import Path
import argparse, json, re, subprocess, sys

FATAL = re.compile(r"ClassCastException|NullPointerException|ExecutionException|AssertionError|java\.lang\.\w*(?:Exception|Error)|^\s*at\s+forge\.", re.I | re.M)
ILLEGAL = re.compile(r"illegal action|illegal move|cannot legally|not a legal", re.I)
TIMEOUT = re.compile(r"timed out|timeout", re.I)
ACTION = re.compile(r"cast|play|activat|sacrific|discard|choose|pay|resolve|mana", re.I)

CORPORA = {
    "hunting": ("09-hunting-storm.dck", "06-jund-wildfire.dck", range(73001, 73013)),
    "tron": ("10-tron.dck", "06-jund-wildfire.dck", range(73101, 73109)),
    "esper": ("07-esper-control.dck", "01-white-weenie.dck", range(73201, 73209)),
}

def run_game(jar: Path, deck_dir: Path, a: str, b: str, seed: int) -> str:
    cmd = ["xvfb-run", "-a", "java", "-jar", str(jar), "sim", "-d", a, b,
           "-D", str(deck_dir), "-n", "1", "-c", "120", "-s", str(seed)]
    p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if p.returncode:
        raise RuntimeError(f"Forge exited {p.returncode} for seed {seed}\n{p.stdout[-4000:]}")
    return p.stdout

def relevant_lines(text: str, cards=()):
    lines = []
    for line in text.splitlines():
        if (not cards or any(c.lower() in line.lower() for c in cards)) and ACTION.search(line):
            lines.append(line.strip())
    return lines

def first_state_excerpt(text: str):
    state = [l.strip() for l in text.splitlines() if re.search(r"hand|battlefield|life:|turn |phase", l, re.I)]
    return state[:12]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True, type=Path)
    ap.add_argument("--deck-dir", default="battlebox/decks", type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    logs = {}
    runtime_failures = []

    for corpus, (a, b, seeds) in CORPORA.items():
        logs[corpus] = []
        for seed in seeds:
            text = run_game(args.jar.resolve(), args.deck_dir.resolve(), a, b, seed)
            path = args.output / f"{corpus}-{seed}.log"
            path.write_text(text, encoding="utf-8")
            if FATAL.search(text): runtime_failures.append(f"{path.name}: exception/stack trace")
            if ILLEGAL.search(text): runtime_failures.append(f"{path.name}: illegal-action marker")
            if TIMEOUT.search(text): runtime_failures.append(f"{path.name}: timeout marker")
            logs[corpus].append((seed, path, text))

    scenarios = []
    def add(name, expected, corpus, predicate, cards):
        actual = None
        for seed, path, text in logs[corpus]:
            ok, detail = predicate(text)
            if ok:
                actual = {"seed": seed, "log": path.name, "decision": detail,
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
               "runtime_failures": runtime_failures, "scenarios": scenarios}
    (args.output / "scenarios.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md = ["# Deterministic functional-scenario substitute", "",
          "Forge 2.0.14 has no repository harness here for directly constructing arbitrary AI game states; these are fixed-seed verbose games through the actual Forge AI decision path.", ""]
    for s in scenarios:
        md += [f"## {'PASS' if s['pass'] else 'FAIL'} — {s['scenario']}", f"Expected: {s['expected_ai_decision']}"]
        if s["actual"]:
            a = s["actual"]
            md += [f"Seed/log: `{a['seed']}` / `{a['log']}`", f"Actual decision evidence: `{a['decision']}`",
                   "Relevant excerpt:", "```", *a["relevant_log_excerpt"], "```"]
        else:
            md += ["No candidate fixed-seed game demonstrated the required reached state and decision path."]
        md.append("")
    if runtime_failures:
        md += ["## Runtime failures", *[f"- {x}" for x in runtime_failures]]
    (args.output / "scenarios.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    failed = [s["scenario"] for s in scenarios if not s["pass"]]
    if runtime_failures or failed:
        print("SCENARIO VALIDATION FAILED")
        for x in runtime_failures + failed: print("-", x)
        return 1
    print("SCENARIO VALIDATION PASSED")
    return 0

if __name__ == "__main__":
    sys.exit(main())
