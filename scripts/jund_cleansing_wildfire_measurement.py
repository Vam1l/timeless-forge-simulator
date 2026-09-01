#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

JUND = "06-jund-wildfire.dck"
BRIDGES = {"Drossforge Bridge", "Slagwoods Bridge"}
URZA = {"Urza's Mine", "Urza's Power Plant", "Urza's Tower"}
CLOCK_SECONDS = 120

MEASURE = re.compile(r"^CWMEASURE\s+(.+)$")
CAST = re.compile(r"Add To Stack: (Ai\(\d+\)-.+?) cast Cleansing Wildfire targeting \[(.+?)\]")
LAND_PLAY = re.compile(r"Land: (Ai\(\d+\)-.+?) played (.+?) \((\d+)\)")
ZONE = re.compile(r"Zone Change: (.+?) \((\d+)\) was put into (\w+) from (\w+)")
MANA_URZA = re.compile(r"Mana: (Urza's (?:Mine|Power Plant|Tower)) \((\d+)\)")
TURN = re.compile(r"Turn: Turn (\d+) \((.+?)\)")
PHASE = re.compile(r"Phase: (.+)")
WIN = re.compile(r"Game Result:\s*Game\s+\d+\s+ended in\s+(\d+)\s+ms\.\s*(.+?)\s+has won!", re.I)
DRAW = re.compile(r"Game Result:.*\b(?:draw|drawn)\b", re.I)
START = re.compile(r"\b(?:Turn\s+1|Mulligan|Opening Hand|Game\s+1)\b", re.I)
FATAL = re.compile(r"ClassCastException|NullPointerException|ExecutionException|AssertionError|java\.lang\.\w*(?:Exception|Error)|^\s*at\s+forge\.", re.I|re.M)
BYTE_INTEGER = re.compile(r"Byte.*Integer|Integer.*Byte|numeric[-_ ]map", re.I)
DECK_LOAD = re.compile(r"No deck found|Could not load deck|match cannot start", re.I)
ILLEGAL = re.compile(r"illegal action|illegal move|cannot legally|not a legal", re.I)
TIMEOUT_TEXT = re.compile(r"timed out|timeout|SUBPROCESS_TIMEOUT", re.I)
LEGACY_CWAI = re.compile(r"CWAI candidates=(\[.*?\]) ownIndestructible=(\[.*?\]) opposingHighValue=(\[.*?\]) selected=(.*?) reason=([\w-]+)$")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize(name: str) -> str:
    s = Path(name).stem.lower()
    s = re.sub(r"^ai\(\d+\)-", "", s)
    s = re.sub(r"^\d+[-_ ]*", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


def split_fields(payload: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for piece in payload.split():
        if "=" not in piece:
            continue
        k, v = piece.split("=", 1)
        out[k] = v
    return out


def parse_card_ref(value: str) -> dict | None:
    if not value or value == "-":
        return None
    if "#" not in value:
        return {"name": value.replace("_", " "), "id": None, "raw": value}
    name, cid = value.rsplit("#", 1)
    return {"name": name.replace("_", " "), "id": cid, "raw": value}


def parse_card_refs(value: str | None) -> list[dict]:
    if not value or value == "-":
        return []
    return [x for x in (parse_card_ref(v) for v in value.split(",")) if x]


def target_from_ordinary(raw: str) -> dict:
    m = re.match(r"(.+?) \((\d+)\)$", raw)
    if not m:
        return {"name": raw, "id": None, "raw": raw}
    return {"name": m.group(1), "id": m.group(2), "raw": raw}


def parse_measurement_events(text: str) -> list[dict]:
    events = []
    measure_index = 0
    for line_index, line in enumerate(text.splitlines()):
        m = MEASURE.match(line)
        if not m:
            continue
        fields = split_fields(m.group(1))
        fields["line_index"] = line_index
        fields["measure_index"] = measure_index
        fields["targets_parsed"] = parse_card_refs(fields.get("targets"))
        if "selected" in fields:
            fields["selected_parsed"] = parse_card_ref(fields.get("selected", "-"))
        if "own" in fields:
            fields["own_parsed"] = parse_card_refs(fields.get("own"))
        if "high" in fields:
            fields["high_parsed"] = parse_card_refs(fields.get("high"))
        if "candidates" in fields:
            fields["candidates_parsed"] = parse_card_refs(fields.get("candidates"))
        events.append(fields)
        measure_index += 1
    return events


def parse_ordinary_casts(text: str) -> list[dict]:
    out = []
    turn = None
    phase = None
    for line_index, line in enumerate(text.splitlines()):
        mt = TURN.match(line)
        if mt:
            turn = int(mt.group(1))
        mp = PHASE.match(line)
        if mp:
            phase = mp.group(1)
        mc = CAST.search(line)
        if mc and "Jund Wildfire" in mc.group(1):
            out.append({
                "ordinal": len(out),
                "line_index": line_index,
                "caster": mc.group(1),
                "target": target_from_ordinary(mc.group(2)),
                "turn": turn,
                "phase": phase,
            })
    return out


def correlate_measurement(text: str) -> dict:
    events = parse_measurement_events(text)
    probes = [e for e in events if e.get("kind") == "probe"]
    posts = [e for e in events if e.get("kind") == "postselect"]
    commits = [e for e in events if e.get("kind") == "commit"]
    ordinary = parse_ordinary_casts(text)
    correlations = []
    used_probe_indexes = set()

    for ordinal, commit in enumerate(commits):
        sa = commit.get("sa")
        host = commit.get("host")
        prior_probes = [e for e in probes if e.get("sa") == sa and e.get("host") == host and e["measure_index"] < commit["measure_index"]]
        prior_posts = [e for e in posts if e.get("sa") == sa and e.get("host") == host and e["measure_index"] < commit["measure_index"]]
        probe = max(prior_probes, key=lambda e: e["measure_index"], default=None)
        post = None
        if probe:
            post = max((e for e in prior_posts if e["measure_index"] > probe["measure_index"]), key=lambda e: e["measure_index"], default=None)
            used_probe_indexes.add(probe["measure_index"])

        ordinary_cast = ordinary[ordinal] if ordinal < len(ordinary) else None
        status = "correlated" if probe else "uncorrelated"
        issues = []
        commit_target = commit.get("targets_parsed", [])
        if len(commit_target) != 1:
            issues.append("commit_target_count_not_one")
        if ordinary_cast:
            if not commit_target or ordinary_cast["target"].get("id") != commit_target[0].get("id"):
                issues.append("ordinary_target_disagrees_with_commit")
        else:
            issues.append("missing_ordinary_cast")

        if probe:
            reason = probe.get("reason")
            selected = probe.get("selected_parsed")
            if reason in ("self-indestructible", "visible-tron"):
                if not post:
                    issues.append("missing_postselect")
                if not selected or not commit_target or selected.get("id") != commit_target[0].get("id"):
                    issues.append("selected_target_disagrees_with_commit")
                if post and [x.get("id") for x in post.get("targets_parsed", [])] != [x.get("id") for x in commit_target]:
                    issues.append("postselect_target_disagrees_with_commit")
            elif reason in ("stock-fallback", "fallback-empty"):
                if selected is not None:
                    issues.append("stock_probe_has_selected_override")

        if issues:
            status = "mismatch" if probe else "uncorrelated"
        correlations.append({
            "ordinal": ordinal,
            "status": status,
            "issues": issues,
            "commit": commit,
            "probe": probe,
            "postselect": post,
            "probe_count_same_identity": len(prior_probes),
            "ordinary_cast": ordinary_cast,
        })

    uncommitted_probes = [e for e in probes if e["measure_index"] not in used_probe_indexes]
    return {
        "events": events,
        "commits": commits,
        "ordinary_casts": ordinary,
        "correlations": correlations,
        "uncommitted_probes": uncommitted_probes,
    }


def parse_result(text: str, a: str, b: str):
    m = WIN.findall(text)
    if m:
        dur, raw = m[-1]
        n = normalize(raw)
        na, nb = normalize(a), normalize(b)
        if n == na or na in n or n in na:
            return a, int(dur), raw
        if n == nb or nb in n or n in nb:
            return b, int(dur), raw
        return None, int(dur), raw
    if DRAW.search(text):
        return "DRAW", None, "DRAW"
    return None, None, None


def runtime_issues(rc: int, text: str, winner) -> list[str]:
    out = []
    if rc: out.append(f"exit={rc}")
    if FATAL.search(text): out.append("exception_or_stack_trace")
    if BYTE_INTEGER.search(text): out.append("byte_integer_or_numeric_map_failure")
    if DECK_LOAD.search(text): out.append("deck_load_failure")
    if ILLEGAL.search(text): out.append("illegal_action")
    if TIMEOUT_TEXT.search(text): out.append("timeout_marker")
    if winner is None: out.append("unparsed_result")
    if not START.search(text) and winner is None: out.append("game_not_started")
    return out


def install_decks(source: Path, dest: Path):
    dest.mkdir(parents=True, exist_ok=True)
    for p in sorted(source.glob("*.dck")):
        q = dest / p.name
        shutil.copyfile(p, q)
        if p.read_bytes() != q.read_bytes():
            raise RuntimeError("deck byte mismatch: " + p.name)


def run_one(jar: Path, deck_dir: Path, a: str, b: str, seed: int):
    cmd = ["xvfb-run", "-a", "java", "-jar", str(jar.resolve()), "sim", "-d", a, b, "-D", str(deck_dir.resolve()), "-n", "1", "-c", str(CLOCK_SECONDS), "-s", str(seed)]
    try:
        p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=150, check=False)
        return p.returncode, p.stdout, cmd
    except subprocess.TimeoutExpired as e:
        return 124, (e.stdout or "") + "\nSUBPROCESS_TIMEOUT\n", cmd


def has_distinct_urya(items: list[dict]) -> bool:
    return len({x["name"] for x in items if x["name"] in URZA}) >= 2


def gate_command(args) -> int:
    args.output.mkdir(parents=True, exist_ok=True)
    logs = args.output / "logs"
    logs.mkdir(exist_ok=True)
    install_decks(args.source_decks, args.deck_dir)
    specs = [
        (JUND, "10-tron.dck", 97004),
        (JUND, "07-esper-control.dck", 97004),
        (JUND, "08-sultai-beans.dck", 97004),
        (JUND, "10-tron.dck", 97001),
    ]
    rows = []
    all_correlations = []
    for a, b, seed in specs:
        rc, text, cmd = run_one(args.candidate, args.deck_dir, a, b, seed)
        path = logs / f"{Path(a).stem}-vs-{Path(b).stem}-seed-{seed}.log"
        path.write_text(text)
        winner, duration, raw = parse_result(text, a, b)
        issues = runtime_issues(rc, text, winner)
        corr = correlate_measurement(text)
        mismatches = [c for c in corr["correlations"] if c["status"] == "mismatch"]
        uncorrelated = [c for c in corr["correlations"] if c["status" == "uncorrelated"]
        if mismatches or uncorrelated:
            issues.append("ambiguous_or_mismatched_committed_target_correlation")
        row.append({
            "deck_a": a, "deck_b": b, "seed": seed, "winner": winner, "duration_ms": duration,
            "issues": issues, "command": " ".join(cmd), "log": str(path),
            "commits": len(corr["commits"]), "uncommitted_probes": len(corr["uncommitted_probes"]),
        })
        for c in corr["correlations"]:
            all_correlations.append({"deck_b": b, "seed": seed, **c})
        if issues:
            (args.output / "runtime-failures.json").write_text(json.dumps(rows, indent=2) + "\n")
            raise SystemExit("fail-stop in four-game correlation gate")
    (args.output / "runtime-failures.json").write_text("[]\n")

    def commits_with(predicate):
        return [c for c in all_correlations if c["status" == "correlated" and c["probe" and predicate(c)]
    stock_fallbacks = commits_with(lambda c: c["probe"].get("reason") in ("stock-fallback", "fallback-empty") and not c["probe"].get("own_parsed", []))
    self_bridge = commits_with(lambda c: c["probe"].get("reason") == "self-indestructible" and c["probe"].get("selected_parsed", {}).get("name") in BRIDGES)
    visible_tron = commits_with(lambda c: c["probe"].get("reason") == "visible-tron" and has_distinct_urya(c["probe"].get("high_parsed", [])))
    duplicate_single_urza_self = commits_with(lambda c: c["probe"].get("reason") == "self-indestructible"
            and len(c["probe"].get("high_parsed", [])) >= 2
            and not has_distinct_urya(c["probe"].get("high_parsed", [])))
    unique_sa_probes = defaultdict(int)
    for c in all_correlations:
        if c["probe"]:
            unique_sa_probes[(c["deck_b"], c["seed"], c["commit"].get("sa"))] = max(unique_sa_probes[(c["deck_b"], c["seed"], c["commit"].get("sa"))], c["probe_count_same_identity"])
    multiple_probes = sum(1 for v in unique_sa_probes.values() if v > 1)
    uncommitted_probes = sum(r["uncommitted_probes"] for r in rows)
    gate = {
        "games": 4,
        "identity_correlated_commits": len(all_correlations),
        "uncorrelated_commits": sum(1 for c in all_correlations if c["status"] == "uncorrelated"),
        "mismatched_commits": sum(1 for c in all_correlations if c["status" == "mismatch"),
        "uncommitted_probes": uncommitted_probes,
        "multiple_probes_same_identity": multiple_probes,
        "stock_fallback_correlated": len(stock_fallbacks),
        "self_bridge_correlated": len(self_bridge),
        "visible_tron_correlated": len(visible_tron),
        "duplicate_single_urya_type_self_correlated": len(duplicate_single_urza_self),
        "runtime_failures": 0,
    }
    gate["pass"] = all([
        gate["identity_correlated_commits"] > 0,
        gate["uncorrelated_commits"] == 0,
        gate["mismatched_commits"] == 0,
        gate["uncommitted_probes"] > 0,
        gate["multiple_probes_same_identity"] > 0,
        gate["stock_fallback_correlated"] > 0,
        gate["self_bridge_correlated"] > 0,
        gate["visible_tron_correlated"] > 0,
        gate["duplicate_single_urza_type_self_correlated"] > 0,
    ])
    (args.output / "per-game.json").write_text(json.dumps(rows, indent=2) + "\n")
    (args.output / "correlations.json").write_text(json.dumps(all_correlations, indent=2) + "\n")
    (args.output / "gate.json").write_text(json.dumps(gate, indent=2) + "\n")
    return 0 if gate["pass"] else 1


def split_legacy_cards(s: str) -> list[str]:
    if s == "[]":
        return []
    body = s[1:-1].strip()
    return [x.strip() for x in body.split(",")] if body else []


def legacy_visible_tron_for_target(text: str, target: dict) -> bool:
    if not target.get("id"):
        return False
    for line in text.splitlines():
        m = LEGACY_CWAI.search(line)
        if not m:
            continue
        candidates, own, high, selected, reason = m.groups()
        if reason != "visible-tron":
            continue
        sm = re.match(r".+? \((\d+)\)$", selected)
        if not sm or sm.group(1) != target["id"]:
            continue
        names = {re.sub(r" \(\d+\)$", "", x) for x in split_legacy_cards(high) if re.sub(r" \(\d+\)$", "", x) in URZA}
        if len(names) >= 2:
            return True
    return False


def ordinary_accounting(text: str, build: str, opponent: str, seed: int) -> list[dict]:
    turn = None
    phase = None
    bridges: dict[str, str] = {}
    opponent_urza: dict[str, str] = {}
    out = []
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        mt = TURN.match(line)
        if mt:
            turn = int(mt.group(1))
        mp = PHASE.match(line)
        if mp:
            phase = mp.group(1)
        ml = LAND_PLAY.match(line)
        if ml:
            ctrl, name, cid = ml.groups()
            if "Jund Wildfire" in ctrl and name in BRIDGES:
                bridges[cid] = name
            if "Jund Wildfire" not in ctrl and name in URZA:
                opponent_urza[cid] = name
        mm = MANA_URZA.match(line)
        if mm and opponent == "10-tron.dck":
            name, cid = mm.groups()
            opponent_urya[cid] = name
        mz = ZONE.match(line)
        if mz:
            name, cid, dest, origin = mz.groups()
            if origin == "Battlefield":
                bridges.pop(cid, None)
                opponent_urya.pop(cid, None)
            if dest == "Battlefield" and opponent == "10-tron.dck" and name in URZA:
                opponent_urza[cid] = name
        mc = CAST.search(line)
        if not (mc and "Jund Wildfire" in mc.group(1)):
            continue
        target = target_from_ordinary(mc.group(2))
        bridge_ids = sorted(bridges)
        distinct_urza = set(opponent_urza.values())
        if target["name"] in URZA:
            distinct_urza.add(target["name"])
        legacy_target_tron = build == "candidate" and target["name"] in URZA and legacy_visible_tron_for_target(text, target)
        if target["name"] in BRIDGES:
            classification = "self-Bridge ramp"
            evidence = "ordinary committed target"
        elif target["name"] in URZA and (len(distinct_urza) >= 2 or legacy_target_tron):
            classification = "visible-Tron disruption"
            evidence = "ordinary board chronology" if len(distinct_urza) >= 2 else "legacy telemetry exact target-ID pre-destruction correlation"
        elif build == "candidate" and not bridge_ids:
            classification = "legitimate no-Bridge stock fallback"
            evidence = "ordinary board chronology"
        elif build == "candidate" and bridge_ids:
            classification = "candidate targeting defect"
            evidence = "ordinary board chronology"
        else:
            classification = "replaceable-land targeting"
            evidence = "ordinary committed target"
        out.append(y4T4 