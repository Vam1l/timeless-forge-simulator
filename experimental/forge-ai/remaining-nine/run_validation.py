#!/usr/bin/env python3
"""Bounded stock-vs-recovered behavioral validation for every deck except Hunting Storm.

Exactly 52 behavioral games are scheduled: 12 Tron, 12 Esper, and 28 across the
other seven decks. The script is fail-fast and never retries or substitutes games.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

FORGE_VERSION = "2.0.14"
RECOVERED_AI_SHA = "237300550e94586479bba9b1c6123af3e87cb179"
VALIDATED_BASE_SHA = "29ac1c40fee5a7058f040398654198ae270f5b22"

DECKS = {
    "white": "01-white-weenie.dck",
    "madness": "02-madness-burn.dck",
    "green": "03-green-stompy.dck",
    "black": "04-black-sacrifice.dck",
    "blue": "05-blue-terror.dck",
    "jund": "06-jund-wildfire.dck",
    "esper": "07-esper-control.dck",
    "sultai": "08-sultai-beans.dck",
    "tron": "10-tron.dck",
}

# Each tuple is: phase, target, opponent, deck_a, deck_b, seed.
# 6 Tron conditions + 6 Esper conditions + 14 other-deck conditions = 26;
# stock + patched = exactly 52 behavioral games.
CONDITIONS = [
    ("tron", "tron", "white", DECKS["tron"], DECKS["white"], 95001),
    ("tron", "tron", "white", DECKS["white"], DECKS["tron"], 95002),
    ("tron", "tron", "blue", DECKS["tron"], DECKS["blue"], 95003),
    ("tron", "tron", "blue", DECKS["blue"], DECKS["tron"], 95004),
    ("tron", "tron", "jund", DECKS["tron"], DECKS["jund"], 95005),
    ("tron", "tron", "jund", DECKS["jund"], DECKS["tron"], 95006),

    ("esper", "esper", "white", DECKS["esper"], DECKS["white"], 95101),
    ("esper", "esper", "white", DECKS["white"], DECKS["esper"], 95102),
    ("esper", "esper", "blue", DECKS["esper"], DECKS["blue"], 95103),
    ("esper", "esper", "blue", DECKS["blue"], DECKS["esper"], 95104),
    ("esper", "esper", "black", DECKS["esper"], DECKS["black"], 95105),
    ("esper", "esper", "black", DECKS["black"], DECKS["esper"], 95106),

    ("audit", "white", "jund", DECKS["white"], DECKS["jund"], 95201),
    ("audit", "white", "jund", DECKS["jund"], DECKS["white"], 95202),
    ("audit", "madness", "esper", DECKS["madness"], DECKS["esper"], 95203),
    ("audit", "madness", "esper", DECKS["esper"], DECKS["madness"], 95204),
    ("audit", "green", "esper", DECKS["green"], DECKS["esper"], 95205),
    ("audit", "green", "esper", DECKS["esper"], DECKS["green"], 95206),
    ("audit", "black", "white", DECKS["black"], DECKS["white"], 95207),
    ("audit", "black", "white", DECKS["white"], DECKS["black"], 95208),
    ("audit", "blue", "jund", DECKS["blue"], DECKS["jund"], 95209),
    ("audit", "blue", "jund", DECKS["jund"], DECKS["blue"], 95210),
    ("audit", "jund", "blue", DECKS["jund"], DECKS["blue"], 95211),
    ("audit", "jund", "blue", DECKS["blue"], DECKS["jund"], 95212),
    ("audit", "sultai", "white", DECKS["sultai"], DECKS["white"], 95213),
    ("audit", "sultai", "white", DECKS["white"], DECKS["sultai"], 95214),
]

FATAL = re.compile(
    r"ClassCastException|NullPointerException|ExecutionException|AssertionError|"
    r"java\.lang\.\w*(?:Exception|Error)|^\s*at\s+forge\.", re.I | re.M
)
BYTE_INTEGER = re.compile(r"(?:Byte.*Integer|Integer.*Byte|ClassCastException.*(?:Byte|Integer)|numeric[- ]map)", re.I)
ILLEGAL = re.compile(r"illegal action|illegal move|cannot legally|not a legal", re.I)
TIMEOUT_TEXT = re.compile(r"timed out|timeout reached|simulation timeout", re.I)
DECK_LOAD = re.compile(r"No deck found|Could not load deck|match cannot start", re.I)
START = re.compile(r"\b(?:Turn\s+1|Mulligan|Opening Hand|Game\s+1)\b", re.I)
ACTION = re.compile(r"cast|play|activat|sacrific|discard|attack|block|target|resolve|choose|counter|destroy|damage|mana", re.I)

CARDS = {
    "tron": ["Expedition Map", "Ancient Stirrings", "Crop Rotation", "Chromatic Star", "Chromatic Sphere",
             "Energy Refractor", "Urza's Mine", "Urza's Power Plant", "Urza's Tower", "Forest",
             "Mulldrifter", "Mnemonic Wall", "Fangren Marauder", "Ulamog's Crusher", "Rolling Thunder", "Steel Hellkite"],
    "esper": ["Counterspell", "Cast Down", "Doom Blade", "Journey to Nowhere", "Drown in the Loch",
              "Supreme Verdict", "Prismatic Strands", "Ephemerate", "Archaeomancer", "Mulldrifter",
              "Thorn of the Black Rose", "Gurmag Angler"],
    "white": ["Ardent Recruit", "Court Homunculus", "Kor Skyfisher", "Battle Screech", "Ramosian Rally",
              "Journey to Nowhere", "Thraben Charm", "Prismatic Strands", "Bonesplitter"],
    "madness": ["Monastery Swiftspear", "Dragon's Rage Channeler", "Faithless Looting", "Grab the Prize",
                "Fiery Temper", "Lightning Bolt", "Lava Dart", "Fireblast", "Skullcrack"],
    "green": ["Nettle Sentinel", "Quirion Ranger", "Skarrgan Pit-Skulk", "Burning-Tree Emissary",
              "Strangleroot Geist", "Rancor", "Vines of Vastwood", "Savage Swipe", "Hunger of the Howlpack"],
    "black": ["Carrion Feeder", "Bloodthrone Vampire", "Ravenous Squirrel", "Gixian Infiltrator",
              "Nested Shambler", "Village Rites", "Corrupted Conviction", "Accursed Marauder",
              "Supernatural Stamina", "Dark Triumph"],
    "blue": ["Delver of Secrets", "Tolarian Terror", "Cryptic Serpent", "Brainstorm", "Ponder", "Thought Scour",
             "Counterspell", "Daze", "Foil", "Lose Focus", "Deem Inferior"],
    "jund": ["Cleansing Wildfire", "Ichor Wellspring", "Deadly Dispute", "Eviscerator's Insight",
             "Refurbished Familiar", "Writhing Chrysalis", "Mayhem Devil", "Cast Down", "Crypt Rats",
             "Makeshift Munitions", "Drossforge Bridge", "Slagwoods Bridge"],
    "sultai": ["Up the Beanstalk", "Generous Ent", "Chitin Gravestalker", "Gurmag Nightwatch", "Nemesis of Mortals",
               "Malevolent Rumble", "Mire Triton", "Overwhelming Remorse", "Far // Away", "Accursed Marauder"],
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", Path(value).stem.lower())


def winner(text: str):
    matches = re.findall(r"Game Result:\s*Game\s+\d+\s+ended in \d+ ms\.\s*(.+?)\s+has won!", text, re.I)
    if not matches:
        matches = re.findall(r"Game Outcome:\s*(.+?)\s+has won", text, re.I)
    return matches[-1].strip() if matches else None


def game_duration_ms(text: str):
    matches = re.findall(r"Game Result:\s*Game\s+\d+\s+ended in (\d+) ms", text, re.I)
    return int(matches[-1]) if matches else None


def turn_count(text: str):
    turns = [int(x) for x in re.findall(r"\bTurn\s+(\d+)\b", text, re.I)]
    return max(turns) if turns else None


def game_started(text: str) -> bool:
    return bool(START.search(text) or winner(text))


def repeated_loop(text: str) -> bool:
    # Conservative stall detector: the same action-like log line repeated 20 times consecutively.
    last = None
    streak = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or not ACTION.search(line):
            continue
        if line == last:
            streak += 1
            if streak >= 20:
                return True
        else:
            last, streak = line, 1
    return False


def runtime_issues(rc: int, text: str, timed_out: bool = False):
    issues = []
    if timed_out:
        issues.append("timeout")
    if rc:
        issues.append(f"exit={rc}")
    if DECK_LOAD.search(text):
        issues.append("deck_load_failure")
    if BYTE_INTEGER.search(text):
        issues.append("byte_integer_or_numeric_map_failure")
    if FATAL.search(text):
        issues.append("exception_or_stack_trace")
    if ILLEGAL.search(text):
        issues.append("illegal_action")
    if TIMEOUT_TEXT.search(text):
        issues.append("timeout")
    if repeated_loop(text):
        issues.append("stall_or_loop")
    if not game_started(text):
        issues.append("game_not_started")
    if not winner(text):
        issues.append("unparsed_game")
    return list(dict.fromkeys(issues))


def sim_args(deck_dir: Path, a: str, b: str, seed: int):
    return ["sim", "-d", a, b, "-D", str(deck_dir), "-n", "1", "-c", "120", "-s", str(seed)]


def run_game(jar: Path, args, wall_timeout=135):
    cmd = ["xvfb-run", "-a", "java", "-jar", str(jar), *args]
    started = time.monotonic()
    try:
        p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=wall_timeout)
        return p.returncode, p.stdout, " ".join(cmd), time.monotonic() - started, False
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", errors="replace")
        return 124, out, " ".join(cmd), time.monotonic() - started, True


def contexts(text: str, cards, radius=3, limit=30):
    lines = text.splitlines()
    found = []
    used = set()
    for i, line in enumerate(lines):
        if not any(card.lower() in line.lower() for card in cards):
            continue
        if not ACTION.search(line):
            continue
        lo, hi = max(0, i-radius), min(len(lines), i+radius+1)
        key = (lo, hi)
        if key in used:
            continue
        used.add(key)
        found.append({"line": i+1, "excerpt": lines[lo:hi]})
        if len(found) >= limit:
            break
    return found


def explicit_filter_activations(text: str):
    return [line.strip() for line in text.splitlines()
            if re.search(r"Mana:.*Chromatic (?:Star|Sphere).*(?:Sacrifice|Add)", line, re.I)]


def tron_specific(text: str):
    return {
        "filters": explicit_filter_activations(text),
        "land_choice_contexts": contexts(text, ["Expedition Map", "Ancient Stirrings", "Crop Rotation", "Urza's Mine", "Urza's Power Plant", "Urza's Tower", "Forest"], 4, 40),
        "payoff_contexts": contexts(text, ["Mulldrifter", "Mnemonic Wall", "Fangren Marauder", "Ulamog's Crusher", "Rolling Thunder", "Steel Hellkite"], 4, 30),
        "land_loss_contexts": contexts(text, ["Urza's Mine", "Urza's Power Plant", "Urza's Tower", "Forest"], 4, 40),
    }


def esper_specific(text: str):
    return {
        "removal_contexts": contexts(text, ["Cast Down", "Doom Blade", "Journey to Nowhere", "Drown in the Loch"], 5, 40),
        "counter_contexts": contexts(text, ["Counterspell"], 5, 30),
        "verdict_contexts": contexts(text, ["Supreme Verdict"], 8, 20),
        "strands_contexts": contexts(text, ["Prismatic Strands"], 8, 30),
        "wincon_contexts": contexts(text, ["Mulldrifter", "Thorn of the Black Rose", "Gurmag Angler", "Archaeomancer", "Ephemerate"], 5, 30),
    }


def result_for_target(target: str, a: str, b: str, won: str):
    if not won:
        return "unparsed"
    target_file = DECKS[target]
    target_is_a = a == target_file
    nw = normalize(won)
    a_won = normalize(a) in nw or nw in normalize(a)
    b_won = normalize(b) in nw or nw in normalize(b)
    if not (a_won or b_won):
        return "unparsed"
    return "win" if (target_is_a and a_won) or ((not target_is_a) and b_won) else "loss"


def write_failure(out: Path, failures, message: str):
    (out / "runtime-failures.json").write_text(json.dumps(failures, indent=2) + "\n", encoding="utf-8")
    (out / "final-gate-report.md").write_text(f"# Remaining-nine validation gate\n\n**STOPPED:** {message}\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stock", required=True, type=Path)
    ap.add_argument("--patched", required=True, type=Path)
    ap.add_argument("--source-decks", required=True, type=Path)
    ap.add_argument("--deck-dir", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--branch-sha", default="")
    args = ap.parse_args()

    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    logs_dir = out / "logs"
    logs_dir.mkdir(exist_ok=True)
    reviews_dir = out / "per-deck-reviews"
    reviews_dir.mkdir(exist_ok=True)
    stock = args.stock.resolve(); patched = args.patched.resolve()
    deck_dir = args.deck_dir.expanduser().resolve(); source_decks = args.source_decks.resolve()

    if len(CONDITIONS) != 26 or sum(1 for c in CONDITIONS if c[0] == "tron") != 6 or sum(1 for c in CONDITIONS if c[0] == "esper") != 6:
        raise RuntimeError("condition matrix is not exactly 26 conditions / 52 stock+patched games")
    if any("09-hunting-storm" in x for c in CONDITIONS for x in c if isinstance(x, str)):
        raise RuntimeError("Hunting Storm is prohibited from this validation matrix")

    # Identity files are written before games.
    identities = {
        "forge_version": FORGE_VERSION,
        "validated_base_sha": VALIDATED_BASE_SHA,
        "historical_recovered_ai_sha": RECOVERED_AI_SHA,
        "workflow_checkout_sha": args.branch_sha,
        "stock_jar_sha256": sha256(stock),
        "patched_jar_sha256": sha256(patched),
    }
    (out / "identities.json").write_text(json.dumps(identities, indent=2) + "\n", encoding="utf-8")

    deck_hashes = {}
    for key, filename in DECKS.items():
        src, dst = source_decks / filename, deck_dir / filename
        if not src.is_file() or not dst.is_file():
            write_failure(out, [{"stage": "deck_identity", "deck": filename, "issue": "deck_load_failure"}], "missing deck file")
            return 1
        src_hash, dst_hash = sha256(src), sha256(dst)
        deck_hashes[filename] = {"source_sha256": src_hash, "installed_sha256": dst_hash, "byte_identical": src.read_bytes() == dst.read_bytes()}
        if src_hash != dst_hash or not deck_hashes[filename]["byte_identical"]:
            write_failure(out, [{"stage": "deck_identity", "deck": filename, "issue": "artifact_integrity_failure"}], "installed deck differs from source")
            return 1
    (out / "deck-hashes.json").write_text(json.dumps(deck_hashes, indent=2) + "\n", encoding="utf-8")

    failures = []
    preflight = []
    pre_args = sim_args(deck_dir, DECKS["white"], DECKS["jund"], 94999)
    for build, jar in (("stock", stock), ("patched", patched)):
        rc, text, cmd, elapsed, timed_out = run_game(jar, pre_args)
        log = out / f"preflight-{build}.log"; log.write_text(text, encoding="utf-8")
        issues = runtime_issues(rc, text, timed_out)
        preflight.append({"build": build, "seed": 94999, "simulator_args": pre_args, "command": cmd,
                          "game_started": game_started(text), "winner": winner(text), "issues": issues, "elapsed_seconds": elapsed})
        if issues:
            failures.append({"stage": "preflight", "build": build, "issues": issues, "log": log.name})
            break
    (out / "preflight.json").write_text(json.dumps(preflight, indent=2) + "\n", encoding="utf-8")
    if failures:
        write_failure(out, failures, "stock/patched preflight failed; no behavioral games started")
        return 1

    rows = []
    evidence = []
    counters = defaultdict(Counter)
    matched = []

    for condition_index, (phase, target, opponent, a, b, seed) in enumerate(CONDITIONS, 1):
        common_args = sim_args(deck_dir, a, b, seed)
        pair = {"phase": phase, "target": target, "opponent": opponent, "orientation": f"{Path(a).stem}__vs__{Path(b).stem}", "seed": seed, "simulator_args": common_args, "builds": {}}
        for build, jar in (("stock", stock), ("patched", patched)):
            rc, text, cmd, elapsed, timed_out = run_game(jar, common_args)
            log_name = f"{condition_index:02d}-{phase}-{target}-vs-{opponent}-{Path(a).stem}__{Path(b).stem}-seed-{seed}-{build}.log"
            log_path = logs_dir / log_name
            log_path.write_text(text, encoding="utf-8")
            issues = runtime_issues(rc, text, timed_out)
            if issues:
                failures.append({"stage": phase, "target": target, "opponent": opponent, "orientation": pair["orientation"], "seed": seed,
                                 "build": build, "issues": issues, "log": f"logs/{log_name}"})
                write_failure(out, failures, "hard runtime gate fired; batch stopped without retry")
                return 1
            won = winner(text)
            target_result = result_for_target(target, a, b, won)
            if target_result == "unparsed":
                failures.append({"stage": phase, "target": target, "seed": seed, "build": build, "issues": ["unparsed_game"], "log": f"logs/{log_name}"})
                write_failure(out, failures, "winner could not be mapped to target deck")
                return 1
            card_contexts = contexts(text, CARDS[target], 3, 60)
            specific = tron_specific(text) if target == "tron" else esper_specific(text) if target == "esper" else {}
            record = {
                "phase": phase, "target": target, "opponent": opponent, "orientation": pair["orientation"], "seed": seed,
                "build": build, "deck_a": a, "deck_b": b, "winner": won, "target_result": target_result,
                "turns_completed": turn_count(text), "game_duration_ms": game_duration_ms(text), "wall_seconds": round(elapsed, 3),
                "log": f"logs/{log_name}", "simulator_args": " ".join(common_args), "issues": "",
            }
            rows.append(record)
            evidence_record = {"phase": phase, "target": target, "opponent": opponent, "orientation": pair["orientation"], "seed": seed,
                               "build": build, "log": record["log"], "card_action_contexts": card_contexts, "specific": specific}
            evidence.append(evidence_record)
            counters[(build, target)]["games"] += 1
            counters[(build, target)][target_result] += 1
            counters[(build, target)]["filter_activations"] += len(explicit_filter_activations(text))
            pair["builds"][build] = {"winner": won, "target_result": target_result, "log": record["log"],
                                      "turns_completed": record["turns_completed"], "game_duration_ms": record["game_duration_ms"],
                                      "event_context_count": len(card_contexts)}
        # Common simulator arguments are constructed once and shared by both builds.
        if pair["builds"].keys() != {"stock", "patched"}:
            failures.append({"stage": phase, "target": target, "seed": seed, "issues": ["settings_mismatch"]})
            write_failure(out, failures, "matched build pair incomplete")
            return 1
        matched.append(pair)

    if len(rows) != 52:
        failures.append({"stage": "final_count", "issues": ["artifact_integrity_failure"], "games": len(rows)})
        write_failure(out, failures, "behavioral game count was not exactly 52")
        return 1

    fields = ["phase","target","opponent","orientation","seed","build","deck_a","deck_b","winner","target_result",
              "turns_completed","game_duration_ms","wall_seconds","log","simulator_args","issues"]
    with (out / "per-game.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    (out / "per-game.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    (out / "behavior-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    (out / "matched-stock-patched.json").write_text(json.dumps(matched, indent=2) + "\n", encoding="utf-8")
    (out / "runtime-failures.json").write_text("[]\n", encoding="utf-8")

    summary_rows = []
    for target in ["tron", "esper", "white", "madness", "green", "black", "blue", "jund", "sultai"]:
        for build in ("stock", "patched"):
            c = counters[(build, target)]
            summary_rows.append({"deck": target, "build": build, "games": c["games"], "wins": c["win"], "losses": c["loss"],
                                 "explicit_filter_activations": c["filter_activations"]})
    (out / "parsed-outcomes.json").write_text(json.dumps(summary_rows, indent=2) + "\n", encoding="utf-8")

    # Machine-generated review index. Human behavioral classification occurs after artifact inspection.
    by_target = defaultdict(list)
    for r in rows:
        by_target[r["target"]].append(r)
    for target, target_rows in by_target.items():
        md = [f"# {target} verbose-review index", "", "This file indexes every ordinary verbose log. It does not auto-classify AI correctness.", "",
              "| Build | Opponent | Orientation | Seed | Result | Turns | Log |", "|---|---|---|---:|---|---:|---|"]
        for r in target_rows:
            md.append(f"| {r['build']} | {r['opponent']} | {r['orientation']} | {r['seed']} | {r['target_result']} | {r['turns_completed'] or ''} | `{r['log']}` |")
        (reviews_dir / f"{target}.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    repro = [
        "# Exact reproduction commands",
        "",
        "Install unchanged decks:",
        "```bash",
        "python experimental/forge-ai/prepare_forge_decks.py --source battlebox/decks --destination \"$HOME/.forge/decks/constructed\"",
        "```",
        "",
        "Run the bounded validator after producing `forge-stock.jar` and `forge-patched.jar` with the existing recovered-source build:",
        "```bash",
        "python experimental/forge-ai/remaining-nine/run_validation.py \\",
        "  --stock forge-stock.jar --patched forge-patched.jar \\",
        "  --source-decks battlebox/decks --deck-dir \"$HOME/.forge/decks/constructed\" \\",
        "  --output remaining-nine-results --branch-sha \"$(git rev-parse HEAD)\"",
        "```",
    ]
    (out / "reproduction.md").write_text("\n".join(repro) + "\n", encoding="utf-8")

    gate = [
        "# Remaining-nine Forge AI validation gate",
        "",
        "- Behavioral games completed: **52/52**",
        "- Tron: **12** total (6 stock, 6 patched)",
        "- Esper: **12** total (6 stock, 6 patched)",
        "- Other seven decks: **28** total (14 stock, 14 patched)",
        "- Runtime/deck-load/timeout/illegal/numeric-map/unparsed failures: **0**",
        "- Hunting Storm games: **0**",
        "",
        "No win-rate or automated event counter in this artifact is a behavioral correctness conclusion. Manual review of every verbose log is required.",
    ]
    (out / "final-gate-report.md").write_text("\n".join(gate) + "\n", encoding="utf-8")
    print("REMAINING-NINE AUTOMATED GATES PASSED: 52/52 behavioral games; manual verbose review required")
    return 0


if __name__ == "__main__":
    sys.exit(main())
