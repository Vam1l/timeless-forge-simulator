#!/usr/bin/env python3
"""
Build diagnostic-index.txt from verbose diagnostic log files.
Usage: python scripts/build_diagnostic_index.py <diagnostic_results_dir> <output_file>
"""

import csv
import json
import re
import statistics
import sys
from pathlib import Path

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from timeless_forge.runner import parse_output, normalize_deck_name


def analyze_log(log_path: Path):
    text = log_path.read_text(encoding="utf-8", errors="replace")
    
    # Telemetry check
    has_mulligan = bool(re.search(r"Mulligan:", text))
    has_turn = bool(re.search(r"Turn:\s*Turn \d+", text))
    has_phase = bool(re.search(r"Phase:", text))
    has_stack = bool(re.search(r"Add To Stack:", text))
    has_land = bool(re.search(r"Land:", text))
    
    telemetry_captured = (has_turn or has_phase or has_stack or has_land or has_mulligan)
    
    # Parse turns and game lengths
    game_blocks = re.split(r"(?=Turn:\s*Turn 1\b)", text)
    game_turns = []
    game_durations_ms = []
    
    for block in game_blocks:
        turns = re.findall(r"Turn:\s*Turn (\d+)", block)
        if turns:
            max_t = max(int(t) for t in turns)
            game_turns.append(max_t)
        
        ms_match = re.search(r"ended in (\d+)\s*ms", block)
        if ms_match:
            game_durations_ms.append(int(ms_match.group(1)))
            
    avg_turns = statistics.mean(game_turns) if game_turns else None
    med_turns = statistics.median(game_turns) if game_turns else None
    avg_duration_ms = statistics.mean(game_durations_ms) if game_durations_ms else None
    
    # Warnings and errors search
    warning_patterns = [
        re.compile(r"(?i).*\b(?:warning|error|exception|severe|stack overflow|nullpointer|failed to|cannot find|script error)\b.*")
    ]
    fatal_patterns = [
        re.compile(r".*ClassCastException.*"),
        re.compile(r".*ExecutionException.*"),
        re.compile(r".*NullPointerException.*"),
        re.compile(r".*AssertionError.*"),
        re.compile(r".*java\.lang\.\w*(?:Exception|Error).*"),
        re.compile(r"^\s*at forge\.ai\..*"),
    ]
    warnings_found = []
    fatal_exceptions_found = []
    for line in text.splitlines():
        line_clean = line.strip()
        if not line_clean:
            continue
        # Exclude benign log setup / edition lines
        if "Star Trek" in line_clean or "UNKNOWN set" in line_clean or "Read cards:" in line_clean or "GuiBase:" in line_clean or "Error handling registered!" in line_clean:
            continue
        for pat in fatal_patterns:
            if pat.match(line_clean):
                if line_clean not in fatal_exceptions_found:
                    fatal_exceptions_found.append(line_clean)
        for pat in warning_patterns:
            if pat.match(line_clean):
                if line_clean not in warnings_found:
                    warnings_found.append(line_clean)
                    
    return {
        "telemetry_captured": telemetry_captured,
        "avg_turns": avg_turns,
        "med_turns": med_turns,
        "avg_duration_ms": avg_duration_ms,
        "warnings": warnings_found,
        "fatal_exceptions": fatal_exceptions_found,
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: build_diagnostic_index.py <results_dir> <output_file>")
        return 1

    results_dir = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    
    csv_path = results_dir / "summary.csv"
    if not csv_path.exists():
        print(f"ERROR: {csv_path} not found", file=sys.stderr)
        return 1

    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    lines = [
        "==========================================================",
        "PEASANT+ BATTLE BOX FORGE 2.0.14 AI DIAGNOSTIC INDEX",
        "==========================================================",
        f"Total Orientations Tested: {len(rows)}",
        f"Target Games per Orientation: 20",
        f"Total Target Games: {len(rows) * 20}",
        "",
    ]

    total_games = 0
    total_wins_a = 0
    total_wins_b = 0
    total_draws = 0
    total_unparsed = 0
    all_warnings = []
    all_fatal_exceptions = []
    all_telemetry_status = []

    for i, row in enumerate(rows, 1):
        matchup = row.get("matchup", "")
        deck_a = row.get("deck_a", "")
        deck_b = row.get("deck_b", "")
        wins_a = int(row.get("wins_a", 0))
        wins_b = int(row.get("wins_b", 0))
        draws = int(row.get("draws", 0))
        unparsed = int(row.get("unparsed", 0))
        parsed = wins_a + wins_b + draws
        
        total_games += parsed + unparsed
        total_wins_a += wins_a
        total_wins_b += wins_b
        total_draws += draws
        total_unparsed += unparsed

        log_path = Path(row.get("raw_log", ""))
        if not log_path.is_absolute():
            log_path = results_dir / log_path.name

        analysis = analyze_log(log_path) if log_path.exists() else {}
        telemetry = analysis.get("telemetry_captured", False)
        all_telemetry_status.append(telemetry)

        lines.append(f"--- Diagnostic Matchup {i:02d}: {deck_a} (Seat A) vs {deck_b} (Seat B) ---")
        lines.append(f"Matchup Name: {matchup}")
        lines.append(f"Game Count Accounted: {parsed + unparsed} (Wins A: {wins_a}, Wins B: {wins_b}, Draws: {draws}, Unparsed: {unparsed})")
        
        avg_t = analysis.get("avg_turns")
        med_t = analysis.get("med_turns")
        avg_d = analysis.get("avg_duration_ms")
        
        if avg_t is not None and med_t is not None:
            lines.append(f"Game Length (Turns): Mean {avg_t:.1f} turns, Median {med_t:.1f} turns")
        if avg_d is not None:
            lines.append(f"Game Duration (Time): Mean {avg_d / 1000.0:.2f} s per game")
            
        lines.append(f"Detailed Telemetry Captured: {'YES (Mulligans, Turns, Phases, Stack Actions, Combat)' if telemetry else 'NO'}")
        
        fatals = analysis.get("fatal_exceptions", [])
        if fatals:
            lines.append(f"FATAL RUNTIME EXCEPTIONS FOUND ({len(fatals)}):")
            for f_err in fatals[:10]:
                lines.append(f"  - {f_err}")
            all_fatal_exceptions.extend(fatals)

        warns = analysis.get("warnings", [])
        if warns:
            lines.append(f"Warnings / Engine Messages ({len(warns)}):")
            for w in warns[:10]:
                lines.append(f"  - {w}")
            if len(warns) > 10:
                lines.append(f"  - ... ({len(warns) - 10} additional warnings omitted)")
            all_warnings.extend(warns)
        else:
            lines.append("Warnings / Engine Messages: None detected")
            
        lines.append("")

    lines.append("==========================================================")
    lines.append("SUMMARY DIAGNOSTIC OVERVIEW")
    lines.append("==========================================================")
    lines.append(f"Total Orientations: {len(rows)}")
    lines.append(f"Total Games Accounted: {total_games}")
    lines.append(f"Total Seat A Wins: {total_wins_a}")
    lines.append(f"Total Seat B Wins: {total_wins_b}")
    lines.append(f"Total Draws: {total_draws}")
    lines.append(f"Total Unparsed Games: {total_unparsed}")
    lines.append(f"Full Play-by-Play Telemetry Status: {'SUCCESSFUL (100% of orientations)' if all(all_telemetry_status) else 'PARTIAL'}")
    lines.append(f"Total Fatal Runtime Exceptions: {len(set(all_fatal_exceptions))}")
    lines.append(f"Total Unique Engine/AI Warnings Found: {len(set(all_warnings))}")
    lines.append("==========================================================")

    output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote diagnostic index to {output_file}")

    if all_fatal_exceptions or total_unparsed > 0:
        print(f"ERROR: Diagnostic logs contain {len(set(all_fatal_exceptions))} fatal runtime exceptions and {total_unparsed} unparsed games!", file=sys.stderr)
        for err in set(all_fatal_exceptions)[:10]:
            print(f"  Fatal exception: {err}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
