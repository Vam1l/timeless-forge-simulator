#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

DECKS = [
    "01-white-weenie.dck",
    "02-madness-burn.dck",
    "03-green-stompy.dck",
    "04-black-sacrifice.dck",
    "05-blue-terror.dck",
    "06-jund-wildfire.dck",
    "07-esper-control.dck",
    "08-sultai-beans.dck",
    "09-hunting-storm.dck",
    "10-tron.dck",
]
SEEDS = list(range(97001, 97011))
CLOCK_SECONDS = 120
EXPECTED_DECK_TREE = "3d55da96aa15ea6a7da5ed2cf98e7ff6417bee35"

FATAL = re.compile(
    r"ClassCastException|NullPointerException|ExecutionException|AssertionError|"
    r"java\.lang\.\w*(?:Exception|Error)|^\s*at\s+forge\.",
    re.I | re.M,
)
BYTE_INTEGER = re.compile(r"Byte.*Integer|Integer.*Byte|numeric[-_ ]map", re.I)
DECK_LOAD = re.compile(r"No deck found|Could not load deck|match cannot start", re.I)
ILLEGAL = re.compile(r"illegal action|illegal move|cannot legally|not a legal", re.I)
TIMEOUT_TEXT = re.compile(r"timed out|timeout", re.I)
START = re.compile(r"\b(?:Turn\s+1|Mulligan|Opening Hand|Game\s+1)\b", re.I)
WIN = re.compile(r"Game Result:\s*Game\s+\d+\s+ended in\s+(\d+)\s+ms\.\s*(.+?)\s+has won!", re.I)
DRAW = re.compile(r"Game Result:.*\b(?:draw|drawn)\b", re.I)
WARNING = re.compile(r"(?im)^.*(?:warning|warn:|AI failed to play|not_payable|could not pay|unable to).*$")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize(name: str) -> str:
    stem = Path(name).stem.lower()
    stem = re.sub(r"^ai\(\d+\)-", "", stem, flags=re.I)
    stem = re.sub(r"^\d+[-_ ]*", "", stem)
    return re.sub(r"[^a-z0-9]", "", stem)


def label(deck: str) -> str:
    return re.sub(r"^\d+[-_]", "", Path(deck).stem).replace("-", " ").title()


def orientations() -> list[dict]:
    out = []
    pair_id = 0
    orientation_id = 0
    for i in range(len(DECKS)):
        for j in range(i + 1, len(DECKS)):
            pair_id += 1
            for seat_a, seat_b in ((DECKS[i], DECKS[j]), (DECKS[j], DECKS[i])):
                out.append({
                    "pair_id": pair_id,
                    "orientation_id": orientation_id,
                    "deck_a": seat_a,
                    "deck_b": seat_b,
                    "canonical_a": DECKS[i],
                    "canonical_b": DECKS[j],
                })
                orientation_id += 1
    assert len(out) == 90
    return out


def install_decks(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name in DECKS:
        src = source / name
        dst = destination / name
        if not src.is_file():
            raise RuntimeError(f"missing source deck: {src}")
        shutil.copyfile(src, dst)
        if src.read_bytes() != dst.read_bytes():
            raise RuntimeError(f"deck byte verification failed: {name}")


def parse_result(text: str, deck_a: str, deck_b: str) -> tuple[str | None, int | None, str | None]:
    matches = WIN.findall(text)
    if matches:
        duration_ms, winner_raw = matches[-1]
        nw = normalize(winner_raw.strip())
        na, nb = normalize(deck_a), normalize(deck_b)
        if nw == na or na in nw or nw in na:
            return deck_a, int(duration_ms), winner_raw.strip()
        if nw == nb or nb in nw or nw in nb:
            return deck_b, int(duration_ms), winner_raw.strip()
        return None, int(duration_ms), winner_raw.strip()
    if DRAW.search(text):
        return "DRAW", None, "DRAW"
    return None, None, None


def runtime_issues(returncode: int, text: str, winner: str | None) -> list[str]:
    issues = []
    if returncode:
        issues.append(f"exit={returncode}")
    if FATAL.search(text):
        issues.append("exception_or_stack_trace")
    if BYTE_INTEGER.search(text):
        issues.append("byte_integer_or_numeric_map_failure")
    if DECK_LOAD.search(text):
        issues.append("deck_load_failure")
    if ILLEGAL.search(text):
        issues.append("illegal_action")
    if TIMEOUT_TEXT.search(text):
        issues.append("timeout_marker")
    if not START.search(text) and winner is None:
        issues.append("game_not_started")
    if winner is None:
        issues.append("unparsed_result")
    return issues


def hunting_events(text: str) -> dict:
    lines = text.splitlines()
    original_casts = 0
    storm_copies = 0
    for i, line in enumerate(lines):
        if re.search(r"Add To Stack: .* cast Hunting Pack\b", line, re.I):
            following = lines[i + 1] if i + 1 < len(lines) else ""
            if re.search(r"Add To Stack: .* triggered Hunting Pack\b", following, re.I):
                original_casts += 1
            else:
                storm_copies += 1
    beasts = len(re.findall(r"(?i)(?:Token|Zone Change|resolve[^\n]*):?[^\n]*4/4 green Beast", text))
    if beasts == 0:
        beasts = len(re.findall(r"(?i)4/4 green Beast[^\n]*(?:Battlefield|token)", text))
    return {
        "hunting_pack_original_casts": original_casts,
        "hunting_pack_storm_copy_stack_events": storm_copies,
        "beast_token_resolution_markers": beasts,
        "chromatic_star_mana_activations": len(re.findall(r"Mana: Chromatic Star .*Add", text, re.I)),
        "chromatic_sphere_mana_activations": len(re.findall(r"Mana: Chromatic Sphere .*Add", text, re.I)),
        "hunting_pack_discards": len(re.findall(r"Zone Change: Hunting Pack \(\d+\) was put into Graveyard from Hand", text, re.I)),
    }


def tron_events(text: str) -> dict:
    return {
        "crop_rotation_casts": len(re.findall(r"cast Crop Rotation\b", text, re.I)),
        "chromatic_star_mana_activations": len(re.findall(r"Mana: Chromatic Star .*Add", text, re.I)),
        "chromatic_sphere_mana_activations": len(re.findall(r"Mana: Chromatic Sphere .*Add", text, re.I)),
        "energy_refractor_mana_activations": len(re.findall(r"Mana: Energy Refractor .*Add", text, re.I)),
        "mulldrifter_casts": len(re.findall(r"cast Mulldrifter\b", text, re.I)),
        "fangren_marauder_casts": len(re.findall(r"cast Fangren Marauder\b", text, re.I)),
        "rolling_thunder_casts": len(re.findall(r"cast Rolling Thunder\b", text, re.I)),
        "moments_peace_casts": len(re.findall(r"cast Moment.?s Peace\b", text, re.I)),
        "weather_the_storm_casts": len(re.findall(r"cast Weather the Storm\b", text, re.I)),
        "ulamogs_crusher_casts": len(re.findall(r"cast Ulamog.?s Crusher\b", text, re.I)),
    }


def run_one(jar: Path, deck_dir: Path, deck_a: str, deck_b: str, seed: int) -> tuple[int, str, list[str]]:
    cmd = [
        "xvfb-run", "-a", "java", "-jar", str(jar.resolve()), "sim",
        "-d", deck_a, deck_b,
        "-D", str(deck_dir.resolve()),
        "-n", "1", "-c", str(CLOCK_SECONDS), "-s", str(seed),
    ]
    proc = subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=150,
        check=False,
    )
    return proc.returncode, proc.stdout, cmd


def run_preflight(args) -> int:
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "logs").mkdir(exist_ok=True)
    install_decks(args.source_decks, args.deck_dir)
    try:
        rc, text, cmd = run_one(args.forge_jar, args.deck_dir, "10-tron.dck", "01-white-weenie.dck", 96999)
    except subprocess.TimeoutExpired:
        (args.output / "runtime-failures.json").write_text(json.dumps([{"issues": ["subprocess_timeout"]}], indent=2) + "\n")
        return 1
    log = args.output / "logs" / "preflight-tron-vs-white-seed-96999.log"
    log.write_text(text)
    winner, duration, raw_winner = parse_result(text, "10-tron.dck", "01-white-weenie.dck")
    issues = runtime_issues(rc, text, winner)
    payload = {
        "commit": args.production_sha,
        "jar_sha256": sha256(args.forge_jar),
        "seed": 96999,
        "deck_a": "10-tron.dck",
        "deck_b": "01-white-weenie.dck",
        "winner": winner,
        "winner_raw": raw_winner,
        "duration_ms": duration,
        "command": cmd,
        "issues": issues,
    }
    (args.output / "preflight.json").write_text(json.dumps(payload, indent=2) + "\n")
    (args.output / "runtime-failures.json").write_text(json.dumps(([payload] if issues else []), indent=2) + "\n")
    return 1 if issues else 0


def run_batch(args) -> int:
    args.output.mkdir(parents=True, exist_ok=True)
    log_dir = args.output / "logs"
    log_dir.mkdir(exist_ok=True)
    install_decks(args.source_decks, args.deck_dir)
    all_orientations = orientations()
    start = args.batch * 10
    chosen = all_orientations[start:start + 10]
    if len(chosen) != 10:
        raise SystemExit(f"invalid batch {args.batch}")
    rows = []
    failures = []
    warnings = []
    for condition in chosen:
        for seed in SEEDS:
            try:
                rc, text, cmd = run_one(args.forge_jar, args.deck_dir, condition["deck_a"], condition["deck_b"], seed)
            except subprocess.TimeoutExpired:
                failures.append({**condition, "seed": seed, "issues": ["subprocess_timeout"]})
                break
            log_name = f"o{condition['orientation_id']:02d}-p{condition['pair_id']:02d}-{Path(condition['deck_a']).stem}-vs-{Path(condition['deck_b']).stem}-seed-{seed}.log"
            log_path = log_dir / log_name
            log_path.write_text(text)
            winner, duration_ms, winner_raw = parse_result(text, condition["deck_a"], condition["deck_b"])
            issues = runtime_issues(rc, text, winner)
            warning_lines = WARNING.findall(text)
            hunt = hunting_events(text)
            tron = tron_events(text)
            row = {
                **condition,
                "seed": seed,
                "winner": winner or "UNPARSED",
                "winner_raw": winner_raw or "",
                "duration_ms": duration_ms if duration_ms is not None else "",
                "log": str(log_path),
                "command": " ".join(cmd),
                "warning_count": len(warning_lines),
                **hunt,
                **{f"tron_{k}": v for k, v in tron.items()},
            }
            rows.append(row)
            if warning_lines:
                warnings.append({
                    "orientation_id": condition["orientation_id"],
                    "pair_id": condition["pair_id"],
                    "seed": seed,
                    "deck_a": condition["deck_a"],
                    "deck_b": condition["deck_b"],
                    "log": str(log_path),
                    "lines": warning_lines,
                })
            if issues:
                failures.append({**row, "issues": issues})
                break
        if failures:
            break
    if rows:
        with (args.output / "per-game.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    (args.output / "per-game.json").write_text(json.dumps(rows, indent=2) + "\n")
    (args.output / "runtime-failures.json").write_text(json.dumps(failures, indent=2) + "\n")
    (args.output / "runtime-warnings.json").write_text(json.dumps(warnings, indent=2) + "\n")
    (args.output / "identity.json").write_text(json.dumps({
        "production_sha": args.production_sha,
        "jar_sha256": sha256(args.forge_jar),
        "batch": args.batch,
        "seeds": SEEDS,
        "clock_seconds": CLOCK_SECONDS,
        "expected_deck_tree": EXPECTED_DECK_TREE,
    }, indent=2) + "\n")
    expected = 100
    return 1 if failures or len(rows) != expected else 0


def wilson(wins: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return max(0.0, center - half), min(1.0, center + half)


def stats_record(name: str, wins: int, losses: int, draws: int = 0) -> dict:
    decisive = wins + losses
    lo, hi = wilson(wins, decisive)
    return {
        "name": name,
        "games": wins + losses + draws,
        "decisive": decisive,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate": wins / decisive if decisive else None,
        "wilson95_low": lo if decisive else None,
        "wilson95_high": hi if decisive else None,
    }


def load_rows(root: Path) -> tuple[list[dict], list[dict], list[dict]]:
    rows, failures, warnings = [], [], []
    for batch in range(9):
        candidates = list(root.rglob(f"pilot-batch-{batch}/per-game.json")) + list(root.rglob(f"batch-{batch}/per-game.json"))
        if not candidates:
            candidates = [p for p in root.rglob("per-game.json") if f"batch-{batch}" in str(p.parent)]
        if len(candidates) != 1:
            raise RuntimeError(f"expected one per-game.json for batch {batch}, found {candidates}")
        rows.extend(json.loads(candidates[0].read_text()))
        fpath = candidates[0].parent / "runtime-failures.json"
        wpath = candidates[0].parent / "runtime-warnings.json"
        failures.extend(json.loads(fpath.read_text()))
        warnings.extend(json.loads(wpath.read_text()))
    return rows, failures, warnings


def aggregate(args) -> int:
    args.output.mkdir(parents=True, exist_ok=True)
    rows, failures, warnings = load_rows(args.input)
    keys = [(int(r["orientation_id"]), int(r["seed"])) for r in rows]
    expected_keys = [(o, s) for o in range(90) for s in SEEDS]
    integrity = {
        "games": len(rows),
        "unique_game_keys": len(set(keys)),
        "expected_games": 900,
        "matrix_complete": sorted(keys) == expected_keys,
        "runtime_failures": len(failures),
        "settings_parity": len({r["command"].replace(r["deck_a"], "DECK_A").replace(r["deck_b"], "DECK_B").replace(str(r["seed"]), "SEED") for r in rows}) == 1,
    }
    if len(rows) != 900 or len(set(keys)) != 900 or not integrity["matrix_complete"] or failures:
        (args.output / "gate-report.md").write_text("# Pilot gate report\n\nTechnical integrity: **FAIL**.\n")
        (args.output / "runtime-failures.json").write_text(json.dumps(failures, indent=2) + "\n")
        return 1

    per_deck = []
    for deck in DECKS:
        wins = losses = draws = 0
        for r in rows:
            if deck not in (r["deck_a"], r["deck_b"]):
                continue
            if r["winner"] == "DRAW":
                draws += 1
            elif r["winner"] == deck:
                wins += 1
            else:
                losses += 1
        rec = stats_record(label(deck), wins, losses, draws)
        rec["deck"] = deck
        per_deck.append(rec)

    per_matchup = []
    for pair_id in range(1, 46):
        rr = [r for r in rows if int(r["pair_id"]) == pair_id]
        ca, cb = rr[0]["canonical_a"], rr[0]["canonical_b"]
        wa = sum(1 for r in rr if r["winner"] == ca)
        wb = sum(1 for r in rr if r["winner"] == cb)
        dr = sum(1 for r in rr if r["winner"] == "DRAW")
        rec = stats_record(f"{label(ca)} vs {label(cb)}", wa, wb, dr)
        rec.update({"pair_id": pair_id, "deck_a": ca, "deck_b": cb})
        per_matchup.append(rec)

    seat = {}
    first_wins = sum(1 for r in rows if r["winner"] == r["deck_a"])
    second_wins = sum(1 for r in rows if r["winner"] == r["deck_b"])
    draws = sum(1 for r in rows if r["winner"] == "DRAW")
    seat["overall"] = stats_record("first seat", first_wins, second_wins, draws)
    seat["per_deck"] = []
    for deck in DECKS:
        first = [r for r in rows if r["deck_a"] == deck]
        second = [r for r in rows if r["deck_b"] == deck]
        seat["per_deck"].append({
            "deck": deck,
            "first_seat": stats_record(label(deck), sum(r["winner"] == deck for r in first), sum(r["winner"] not in (deck, "DRAW") for r in first), sum(r["winner"] == "DRAW" for r in first)),
            "second_seat": stats_record(label(deck), sum(r["winner"] == deck for r in second), sum(r["winner"] not in (deck, "DRAW") for r in second), sum(r["winner"] == "DRAW" for r in second)),
        })

    durations = sorted(int(r["duration_ms"]) for r in rows if str(r["duration_ms"]).isdigit())
    def pct(q):
        if not durations:
            return None
        idx = min(len(durations) - 1, max(0, round((len(durations) - 1) * q)))
        return durations[idx]
    duration_stats = {
        "count": len(durations),
        "min_ms": min(durations) if durations else None,
        "p10_ms": pct(0.10),
        "median_ms": pct(0.50),
        "p90_ms": pct(0.90),
        "p95_ms": pct(0.95),
        "max_ms": max(durations) if durations else None,
        "timeouts": 0,
    }

    hunting_rows = [r for r in rows if "09-hunting-storm.dck" in (r["deck_a"], r["deck_b"])]
    hunting = {
        "games": len(hunting_rows),
        "original_hunting_pack_casts": sum(int(r["hunting_pack_original_casts"]) for r in hunting_rows),
        "storm_copy_stack_events": sum(int(r["hunting_pack_storm_copy_stack_events"]) for r in hunting_rows),
        "beast_token_resolution_markers": sum(int(r["beast_token_resolution_markers"]) for r in hunting_rows),
        "chromatic_star_mana_activations": sum(int(r["chromatic_star_mana_activations"]) for r in hunting_rows),
        "chromatic_sphere_mana_activations": sum(int(r["chromatic_sphere_mana_activations"]) for r in hunting_rows),
        "explicit_hunting_pack_discards": sum(int(r["hunting_pack_discards"]) for r in hunting_rows),
        "games_with_original_pack_cast": sum(int(r["hunting_pack_original_casts"]) > 0 for r in hunting_rows),
        "wins_after_original_pack_cast": sum(int(r["hunting_pack_original_casts"]) > 0 and r["winner"] == "09-hunting-storm.dck" for r in hunting_rows),
        "losses_after_original_pack_cast": sum(int(r["hunting_pack_original_casts"]) > 0 and r["winner"] not in ("09-hunting-storm.dck", "DRAW") for r in hunting_rows),
    }

    tron_rows = [r for r in rows if "10-tron.dck" in (r["deck_a"], r["deck_b"])]
    tron = {}
    for key in ["crop_rotation_casts", "chromatic_star_mana_activations", "chromatic_sphere_mana_activations", "energy_refractor_mana_activations", "mulldrifter_casts", "fangren_marauder_casts", "rolling_thunder_casts", "moments_peace_casts", "weather_the_storm_casts", "ulamogs_crusher_casts"]:
        tron[key] = sum(int(r[f"tron_{key}"]) for r in tron_rows)

    for name, payload in [
        ("per-deck.json", per_deck),
        ("per-matchup.json", per_matchup),
        ("seat-analysis.json", seat),
        ("game-lengths.json", duration_stats),
        ("hunting-storm-events.json", hunting),
        ("tron-events.json", tron),
        ("runtime-warnings.json", warnings),
        ("runtime-failures.json", failures),
        ("integrity.json", integrity),
    ]:
        (args.output / name).write_text(json.dumps(payload, indent=2) + "\n")

    with (args.output / "per-game.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    (args.output / "per-game.json").write_text(json.dumps(rows, indent=2) + "\n")

    md = [
        "# Post-merge 900-game Monte Carlo pilot gate report",
        "",
        "## Technical integrity",
        "",
        f"- Games: {len(rows)}/900",
        f"- Unique orientation/seed identities: {len(set(keys))}/900",
        f"- Complete 45-matchup × 2-orientation × 10-seed matrix: {'PASS' if integrity['matrix_complete'] else 'FAIL'}",
        f"- Runtime failures: {len(failures)}",
        f"- Timeouts: {duration_stats['timeouts']}",
        "",
        "## Per-deck pilot results",
        "",
        "| Deck | W-L-D | Win rate | Wilson 95% CI |",
        "|---|---:|---:|---:|",
    ]
    for r in per_deck:
        md.append(f"| {r['name']} | {r['wins']}-{r['losses']}-{r['draws']} | {r['win_rate']:.1%} | {r['wilson95_low']:.1%}–{r['wilson95_high']:.1%} |")
    md += ["", "## Hunting Storm affirmative event counters", ""]
    for k, v in hunting.items():
        md.append(f"- {k}: {v}")
    md += ["", "## Tron affirmative event counters", ""]
    for k, v in tron.items():
        md.append(f"- {k}: {v}")
    (args.output / "gate-report.md").write_text("\n".join(md) + "\n")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="mode", required=True)
    for mode in ("preflight", "batch"):
        q = sub.add_parser(mode)
        q.add_argument("--forge-jar", type=Path, required=True)
        q.add_argument("--source-decks", type=Path, required=True)
        q.add_argument("--deck-dir", type=Path, required=True)
        q.add_argument("--output", type=Path, required=True)
        q.add_argument("--production-sha", required=True)
        if mode == "batch":
            q.add_argument("--batch", type=int, choices=range(9), required=True)
    q = sub.add_parser("aggregate")
    q.add_argument("--input", type=Path, required=True)
    q.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.mode == "preflight":
        return run_preflight(args)
    if args.mode == "batch":
        return run_batch(args)
    return aggregate(args)


if __name__ == "__main__":
    sys.exit(main())
