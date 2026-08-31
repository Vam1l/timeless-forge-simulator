#!/usr/bin/env python3
"""Bounded recovered-vs-candidate Tron Crop Rotation validation.

Exactly 16 gameplay runs: six matched Tron conditions plus two matched non-Tron
smoke conditions, each once on recovered control and candidate. Fail-fast; no retry.
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
from pathlib import Path

CONDITIONS = [
    ("tron", "tron-white", "10-tron.dck", "01-white-weenie.dck", 95001),
    ("tron", "white-tron", "01-white-weenie.dck", "10-tron.dck", 95002),
    ("tron", "tron-blue", "10-tron.dck", "05-blue-terror.dck", 95003),
    ("tron", "blue-tron", "05-blue-terror.dck", "10-tron.dck", 95004),
    ("tron", "tron-jund", "10-tron.dck", "06-jund-wildfire.dck", 95005),
    ("tron", "jund-tron", "06-jund-wildfire.dck", "10-tron.dck", 95006),
    ("smoke", "white-green", "01-white-weenie.dck", "03-green-stompy.dck", 95301),
    ("smoke", "blue-black", "05-blue-terror.dck", "04-black-sacrifice.dck", 95302),
]

DECK_DISPLAY = {
    "01-white-weenie.dck": "White Weenie",
    "03-green-stompy.dck": "Green Stompy",
    "04-black-sacrifice.dck": "Black Sacrifice",
    "05-blue-terror.dck": "Blue Terror",
    "06-jund-wildfire.dck": "Jund Wildfire",
    "10-tron.dck": "Tron",
}

FATAL = re.compile(r"ClassCastException|NullPointerException|ExecutionException|AssertionError|java\.lang\.\w*(?:Exception|Error)|^\s*at\s+forge\.", re.I | re.M)
BYTE = re.compile(r"Byte.*Integer|Integer.*Byte|ClassCastException.*(?:Byte|Integer)", re.I)
ILLEGAL = re.compile(r"illegal action|illegal move|cannot legally|not a legal", re.I)
TIMEOUT = re.compile(r"timed out|timeout", re.I)
DECK_LOAD = re.compile(r"No deck found|Could not load deck|match cannot start", re.I)
START = re.compile(r"\b(?:Turn\s+1|Mulligan|Opening Hand|Game\s+1)\b", re.I)
WINNER = re.compile(r"Game Result:\s*Game\s+\d+\s+ended in \d+ ms\.\s*(.+?)\s+has won!", re.I)
DRAW = re.compile(r"Game Result:.*\b(?:draw|drawn)\b", re.I)
CROP_CAST = re.compile(r"Add To Stack: .* cast Crop Rotation", re.I)
PHASE = re.compile(r"^Turn\s+(\d+)\s+Phase:\s+(.+)$", re.I)
REPEAT_ACTION = re.compile(r"(?:Add To Stack|Resolve Stack|Mana:|Land:|Combat -)")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parsed_result(text: str):
    matches = WINNER.findall(text)
    if matches:
        return matches[-1].strip()
    if DRAW.search(text):
        return "DRAW"
    return None


def runtime_issues(rc: int, text: str):
    issues = []
    if rc:
        issues.append(f"exit={rc}")
    if DECK_LOAD.search(text): issues.append("deck_load_failure")
    if FATAL.search(text): issues.append("exception_or_stack_trace")
    if BYTE.search(text): issues.append("byte_integer_failure")
    if ILLEGAL.search(text): issues.append("illegal_action")
    if TIMEOUT.search(text): issues.append("timeout")
    if not START.search(text) and parsed_result(text) is None: issues.append("game_not_started")
    if parsed_result(text) is None: issues.append("unparsed_result")

    # Conservative repeated-loop detector: one exact action line repeated >= 40 times.
    counts = {}
    for line in text.splitlines():
        s = line.strip()
        if REPEAT_ACTION.search(s):
            counts[s] = counts.get(s, 0) + 1
    if any(v >= 40 for v in counts.values()):
        issues.append("stall_or_repeated_loop")
    return issues


def run_game(jar: Path, deck_dir: Path, a: str, b: str, seed: int):
    cmd = ["xvfb-run", "-a", "java", "-jar", str(jar.resolve()), "sim",
           "-d", a, b, "-D", str(deck_dir.resolve()), "-n", "1", "-c", "120", "-s", str(seed)]
    started = time.monotonic()
    p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=150)
    return p.returncode, p.stdout, cmd, time.monotonic() - started


def crop_excerpts(text: str):
    lines = text.splitlines()
    phase = ""
    turn = ""
    phase_at = {}
    for i, line in enumerate(lines):
        m = PHASE.search(line.strip())
        if m:
            turn, phase = m.group(1), m.group(2)
        phase_at[i] = (turn, phase)
    out = []
    for i, line in enumerate(lines):
        if not CROP_CAST.search(line):
            continue
        lo, hi = max(0, i - 12), min(len(lines), i + 18)
        out.append({
            "turn": phase_at.get(i, ("", ""))[0],
            "phase": phase_at.get(i, ("", ""))[1],
            "cast_line": line.strip(),
            "excerpt": [x.strip() for x in lines[lo:hi]],
        })
    return out


def event_counts(text: str):
    return {
        "crop_casts": len(CROP_CAST.findall(text)),
        "star_mana_activations": len(re.findall(r"Mana: Chromatic Star .*Add", text, re.I)),
        "sphere_mana_activations": len(re.findall(r"Mana: Chromatic Sphere .*Add", text, re.I)),
        "mulldrifter_casts": len(re.findall(r"Add To Stack: .* cast Mulldrifter", text, re.I)),
        "fangren_casts": len(re.findall(r"Add To Stack: .* cast Fangren Marauder", text, re.I)),
        "crusher_casts": len(re.findall(r"Add To Stack: .* cast Ulamog's Crusher", text, re.I)),
        "rolling_thunder_casts": len(re.findall(r"Add To Stack: .* cast Rolling Thunder", text, re.I)),
        "candidate_selector_events": len(re.findall(r"\[TRON_CROP_CANDIDATE\]", text)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--recovered", required=True, type=Path)
    ap.add_argument("--candidate", required=True, type=Path)
    ap.add_argument("--deck-dir", required=True, type=Path)
    ap.add_argument("--source-decks", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--branch-sha", required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "logs").mkdir(exist_ok=True)

    expected = {a for _, _, a, _, _ in CONDITIONS} | {b for _, _, _, b, _ in CONDITIONS}
    deck_hashes = {}
    for name in sorted(expected):
        src, installed = args.source_decks / name, args.deck_dir / name
        if not src.is_file() or not installed.is_file() or src.read_bytes() != installed.read_bytes():
            raise SystemExit(f"deck identity failure: {name}")
        deck_hashes[name] = sha256(src)
    (args.output / "deck-hashes.json").write_text(json.dumps(deck_hashes, indent=2) + "\n")

    rows, failures, crops = [], [], []
    common_nonjar = ["sim", "-D", str(args.deck_dir.resolve()), "-n", "1", "-c", "120"]
    identities = {
        "branch_sha": args.branch_sha,
        "recovered_ai_sha": "237300550e94586479bba9b1c6123af3e87cb179",
        "recovered_jar_sha256": sha256(args.recovered),
        "candidate_jar_sha256": sha256(args.candidate),
        "common_nonjar_settings": common_nonjar,
    }
    (args.output / "build-identities.json").write_text(json.dumps(identities, indent=2) + "\n")

    for build, jar in (("recovered", args.recovered), ("candidate", args.candidate)):
        for stage, condition, a, b, seed in CONDITIONS:
            try:
                rc, text, cmd, duration = run_game(jar, args.deck_dir, a, b, seed)
            except subprocess.TimeoutExpired as exc:
                text = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
                failures.append({"build": build, "condition": condition, "seed": seed, "issues": ["timeout"]})
                (args.output / "runtime-failures.json").write_text(json.dumps(failures, indent=2) + "\n")
                return 1
            log_name = f"{build}-{condition}-seed-{seed}.log"
            (args.output / "logs" / log_name).write_text(text, encoding="utf-8")
            issues = runtime_issues(rc, text)
            if issues:
                failures.append({"build": build, "condition": condition, "seed": seed, "issues": issues, "log": f"logs/{log_name}"})
                (args.output / "runtime-failures.json").write_text(json.dumps(failures, indent=2) + "\n")
                return 1
            result = parsed_result(text)
            events = event_counts(text)
            ce = crop_excerpts(text)
            for item in ce:
                crops.append({"build": build, "condition": condition, "seed": seed, "log": f"logs/{log_name}", **item})
            rows.append({
                "build": build, "stage": stage, "condition": condition, "deck_a": a, "deck_b": b,
                "seed": seed, "winner": result, "duration_seconds": round(duration, 3),
                "log": f"logs/{log_name}", "command": " ".join(cmd), **events,
            })

    # Exact matched settings gate: each condition must have recovered/candidate rows with identical non-JAR args.
    for _, condition, a, b, seed in CONDITIONS:
        pair = [r for r in rows if r["condition"] == condition and r["seed"] == seed]
        if len(pair) != 2 or pair[0]["deck_a"] != pair[1]["deck_a"] or pair[0]["deck_b"] != pair[1]["deck_b"]:
            failures.append({"condition": condition, "seed": seed, "issues": ["build_settings_mismatch"]})
            break
    if len(rows) != 16:
        failures.append({"issues": ["unexpected_game_count"], "actual": len(rows), "expected": 16})

    with (args.output / "per-game.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    (args.output / "per-game.json").write_text(json.dumps(rows, indent=2) + "\n")
    (args.output / "crop-rotation-evidence.json").write_text(json.dumps(crops, indent=2) + "\n")
    (args.output / "runtime-failures.json").write_text(json.dumps(failures, indent=2) + "\n")

    md = ["# Tron Crop Rotation Phase 4 automated gate", "",
          f"Behavioral games completed: {len(rows)}/16.",
          f"Hard failures: {len(failures)}.", "",
          "This report is an automated runtime/indexing gate only; Crop Rotation decisions require manual log review."]
    (args.output / "gate-report.md").write_text("\n".join(md) + "\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
