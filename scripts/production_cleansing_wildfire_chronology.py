#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

BRIDGES = {"Drossforge Bridge", "Slagwoods Bridge"}
URZA = {"Urza's Mine", "Urza's Power Plant", "Urza's Tower"}

TURN_RE = re.compile(r"^Turn: Turn (\d+) \((.+?)\)$")
PHASE_RE = re.compile(r"^Phase: (.+)$")
LAND_RE = re.compile(r"^Land: (Ai\(\d+\)-.+?) played (.+?) \((\d+)\)$")
ZONE_RE = re.compile(r"^Zone Change: (.+?) \((\d+)\) was put into (\w+) from (\w+)\.$")
MANA_RE = re.compile(r"^Mana: (.+?) \((\d+)\) - .+$")
CAST_RE = re.compile(r"^Add To Stack: (Ai\(\d+\)-.+?) cast Cleansing Wildfire targeting \[(.+?) \((\d+)\)\]$")
RESULT_RE = re.compile(r"Game Result:\s*Game\s+\d+\s+ended in\s+\d+\s+ms\.\s*(.+?)\s+has won!", re.I)
FATAL_RE = re.compile(
    r"ClassCastException|NullPointerException|ExecutionException|AssertionError|"
    r"java\.lang\.\w*(?:Exception|Error)|Byte.*Integer|Integer.*Byte|illegal action|"
    r"illegal move|cannot legally|not a legal|SUBPROCESS_TIMEOUT|timed out",
    re.I,
)


@dataclass
class Evidence:
    line_number: int
    line: str
    kind: str

    def as_dict(self) -> dict:
        return {"line_number": self.line_number, "line": self.line, "kind": self.kind}


@dataclass
class TrackedPermanent:
    card_id: str
    name: str
    controller_role: str
    entry: Evidence
    removal: Evidence | None = None

    def as_dict(self) -> dict:
        return {
            "id": self.card_id,
            "name": self.name,
            "controller_role": self.controller_role,
            "entry_evidence": self.entry.as_dict(),
            "removal_evidence": self.removal.as_dict() if self.removal else None,
        }


@dataclass
class BattlefieldState:
    active: dict[str, TrackedPermanent] = field(default_factory=dict)
    removed: list[TrackedPermanent] = field(default_factory=list)

    def observe(self, card_id: str, name: str, controller_role: str, evidence: Evidence) -> None:
        current = self.active.get(card_id)
        if current is not None and current.name == name and current.controller_role == controller_role:
            return
        if current is not None:
            current.removal = Evidence(evidence.line_number, evidence.line, "identity-replaced")
            self.removed.append(current)
        self.active[card_id] = TrackedPermanent(card_id, name, controller_role, evidence)

    def remove(self, card_id: str, evidence: Evidence) -> None:
        current = self.active.pop(card_id, None)
        if current is not None:
            current.removal = evidence
            self.removed.append(current)

    def active_role(self, role: str, names: set[str]) -> list[TrackedPermanent]:
        return sorted(
            (p for p in self.active.values() if p.controller_role == role and p.name in names),
            key=lambda p: (int(p.card_id) if p.card_id.isdigit() else p.card_id, p.name),
        )


def role_for_observation(name: str, controller: str | None, opponent: str) -> str | None:
    if controller is not None:
        if "Jund Wildfire" in controller:
            return "own"
        return "opponent"
    if name in BRIDGES:
        return "own"
    if opponent == "Tron" and name in URZA:
        return "opponent"
    return None


def _card_dicts(cards: Iterable[TrackedPermanent]) -> list[dict]:
    return [c.as_dict() for c in cards]


def parse_preflight_log(text: str, opponent: str) -> dict:
    if FATAL_RE.search(text):
        raise ValueError("runtime failure marker")
    if not RESULT_RE.search(text):
        raise ValueError("unparsed game result")

    turn: int | None = None
    phase: str | None = None
    state = BattlefieldState()
    casts: list[dict] = []
    lines = text.splitlines()

    for line_number, line in enumerate(lines, 1):
        m = TURN_RE.match(line)
        if m:
            turn = int(m.group(1))
            continue
        m = PHASE_RE.match(line)
        if m:
            phase = m.group(1)
            continue

        m = LAND_RE.match(line)
        if m:
            controller, name, card_id = m.groups()
            role = role_for_observation(name, controller, opponent)
            if role and (name in BRIDGES or name in URZA):
                state.observe(card_id, name, role, Evidence(line_number, line, "land-play"))
            continue

        m = ZONE_RE.match(line)
        if m:
            name, card_id, destination, origin = m.groups()
            if origin == "Battlefield" and destination != "Battlefield":
                state.remove(card_id, Evidence(line_number, line, "battlefield-exit"))
            if destination == "Battlefield" and origin != "Battlefield":
                role = role_for_observation(name, None, opponent)
                if role and (name in BRIDGES or name in URZA):
                    state.observe(card_id, name, role, Evidence(line_number, line, "zone-entry"))
            continue

        m = MANA_RE.match(line)
        if m:
            name, card_id = m.groups()
            role = role_for_observation(name, None, opponent)
            if role and (name in BRIDGES or name in URZA):
                state.observe(card_id, name, role, Evidence(line_number, line, "mana-activation"))
            continue

        m = CAST_RE.match(line)
        if not (m and "Jund Wildfire" in m.group(1)):
            continue

        target_name, target_id = m.group(2), m.group(3)
        own = state.active_role("own", BRIDGES)
        urza = state.active_role("opponent", URZA)
        distinct_types = sorted({p.name for p in urza})

        if len(distinct_types) >= 2:
            classification = "visible-Tron disruption"
            passed = target_name in URZA and any(p.card_id == target_id for p in urza)
        elif own:
            classification = "self-Bridge ramp"
            passed = any(p.card_id == target_id for p in own)
        else:
            classification = "stock fallback"
            passed = True

        casts.append({
            "opponent": opponent,
            "turn": turn,
            "phase": phase,
            "active_own_indestructible": _card_dicts(own),
            "active_opposing_urza": _card_dicts(urza),
            "distinct_opposing_urza_types": distinct_types,
            "committed_target": {"id": target_id, "name": target_name, "evidence": {"line_number": line_number, "line": line, "kind": "ordinary-stack-target"}},
            "classification": classification,
            "matches_validated_rule": passed,
        })
        if not passed:
            raise ValueError("target behavior inconsistent with validated policy: " + json.dumps(casts[-1], sort_keys=True))

    # Attach any later explicit removal of cards that were active at each cast. This is
    # report-only evidence and never changes the contemporaneous classification.
    removals_by_id: dict[str, list[dict]] = {}
    for p in state.removed:
        if p.removal:
            removals_by_id.setdefault(p.card_id, []).append(p.removal.as_dict())
    for cast in casts:
        observed_ids = {p["id"] for p in cast["active_own_indestructible"] + cast["active_opposing_urza"]}
        cast["subsequent_removal_evidence"] = {
            card_id: removals_by_id.get(card_id, []) for card_id in sorted(observed_ids) if removals_by_id.get(card_id)
        }

    return {
        "opponent": opponent,
        "result_parsed": True,
        "casts": casts,
        "runtime_failures": 0,
    }


def validate_expected_accounting(games: list[dict]) -> None:
    rows = [row for game in games for row in game["casts"]]
    if len(rows) != 6:
        raise ValueError(f"expected exactly six preserved Wildfire casts, found {len(rows)}")

    esper = [r for r in rows if r["opponent"] == "Esper"]
    tron = [r for r in rows if r["opponent"] == "Tron"]
    if [r["classification"] for r in esper] != ["stock fallback", "self-Bridge ramp", "self-Bridge ramp"]:
        raise ValueError("preserved Esper classification sequence differs from expected")
    if [r["committed_target"]["name"] for r in esper] != ["Ash Barrens", "Slagwoods Bridge", "Slagwoods Bridge"]:
        raise ValueError("preserved Esper target sequence differs from expected")
    if [r["classification"] for r in tron] != ["visible-Tron disruption"] * 3:
        raise ValueError("preserved Tron classification sequence differs from expected")
    if [r["committed_target"]["name"] for r in tron] != ["Urza's Mine", "Urza's Tower", "Urza's Power Plant"]:
        raise ValueError("preserved Tron target sequence differs from expected")
    if not all(r["matches_validated_rule"] for r in rows):
        raise ValueError("one or more preserved casts failed the validated rule")


def analyze_preserved_logs(esper_text: str, tron_text: str) -> dict:
    games = [parse_preflight_log(esper_text, "Esper"), parse_preflight_log(tron_text, "Tron")]
    validate_expected_accounting(games)
    rows = [row for game in games for row in game["casts"]]
    return {
        "games_reused": 2,
        "new_games_executed": 0,
        "games": games,
        "wildfire_casts": rows,
        "runtime_failures": 0,
        "pass": True,
    }


def write_reports(report: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "preflight-accounting.json").write_text(json.dumps(report, indent=2) + "\n")
    lines = [
        "# Corrected artifact-only Cleansing Wildfire accounting",
        "",
        "| Opponent | Turn | Phase | Own indestructible | Opposing Urza by ID | Distinct Urza types | Target | Classification | Rule |",
        "|---|---:|---|---|---|---|---|---|---|",
    ]
    for r in report["wildfire_casts"]:
        own = ", ".join(f"{x['name']} ({x['id']})" for x in r["active_own_indestructible"]) or "none"
        urza = ", ".join(f"{x['name']} ({x['id']})" for x in r["active_opposing_urza"]) or "none"
        types = ", ".join(r["distinct_opposing_urza_types"]) or "none"
        target = f"{r['committed_target']['name']} ({r['committed_target']['id']})"
        lines.append(f"| {r['opponent']} | {r['turn']} | {r['phase']} | {own} | {urza} | {types} | {target} | {r['classification']} | {'PASS' if r['matches_validated_rule'] else 'FAIL'} |")
    lines += ["", "## Evidence"]
    for idx, r in enumerate(report["wildfire_casts"], 1):
        lines.append(f"### Cast {idx}: {r['opponent']} turn {r['turn']}")
        for p in r["active_own_indestructible"] + r["active_opposing_urza"]:
            e = p["entry_evidence"]
            lines.append(f"- {p['name']} ({p['id']}) entry: L{e['line_number']} `{e['line']}` ({e['kind']})")
        ce = r["committed_target"]["evidence"]
        lines.append(f"- committed target: L{ce['line_number']} `{ce['line']}`")
        for card_id, removals in r["subsequent_removal_evidence"].items():
            for e in removals:
                lines.append(f"- later removal of ({card_id}): L{e['line_number']} `{e['line']}`")
    (output / "preflight-accounting.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--esper-log", required=True, type=Path)
    p.add_argument("--tron-log", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    report = analyze_preserved_logs(args.esper_log.read_text(errors="replace"), args.tron_log.read_text(errors="replace"))
    write_reports(report, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
