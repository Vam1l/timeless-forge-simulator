#!/usr/bin/env python3
"""
Run the 18-game focused behavioral smoke test and generate artifact forge-ai-focused-behavioral-logs.
Usage: python scripts/run_focused_smoke_test.py [--forge-jar /path/to/forge.jar] [--output forge-ai-focused-behavioral-logs]
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from timeless_forge.runner import ForgeEngine, run_experiment

SMOKE_MATCHUPS = [
    {"name": "01-esper-control-vs-white-weenie", "deck_a": "07-esper-control.dck", "deck_b": "01-white-weenie.dck", "games_preboard": 3},
    {"name": "02-white-weenie-vs-esper-control", "deck_a": "01-white-weenie.dck", "deck_b": "07-esper-control.dck", "games_preboard": 3},
    {"name": "03-esper-control-vs-green-stompy", "deck_a": "07-esper-control.dck", "deck_b": "03-green-stompy.dck", "games_preboard": 3},
    {"name": "04-green-stompy-vs-esper-control", "deck_a": "03-green-stompy.dck", "deck_b": "07-esper-control.dck", "games_preboard": 3},
    {"name": "05-hunting-storm-vs-jund-wildfire", "deck_a": "09-hunting-storm.dck", "deck_b": "06-jund-wildfire.dck", "games_preboard": 3},
    {"name": "06-jund-wildfire-vs-hunting-storm", "deck_a": "06-jund-wildfire.dck", "deck_b": "09-hunting-storm.dck", "games_preboard": 3},
]

EXCEPTION_PATTERNS = [
    r"ClassCastException",
    r"ExecutionException",
    r"NullPointerException",
    r"StackOverflowError",
    r"AssertionError",
    r"at forge\..*Exception",
]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--forge-jar', type=Path, default=repo_root / "forge-2.0.14.jar")
    parser.add_argument('--output', type=Path, default=repo_root / "forge-ai-focused-behavioral-logs")
    args = parser.parse_args()

    jar_path = args.forge_jar.resolve()
    out_dir = args.output.resolve()

    if not jar_path.is_file():
        print(f"ERROR: Forge jar not found at {jar_path}", file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "name": "Forge AI Focused Behavioral Smoke Test",
        "description": "18-game focused behavioral smoke test across 6 orientations",
        "games_preboard": 3,
        "games_postboard": 0,
        "clock_seconds": 120,
        "deck_dir": str((repo_root / "battlebox" / "decks").resolve()),
        "output_dir": str(out_dir),
        "matchups": SMOKE_MATCHUPS
    }

    config_path = out_dir.parent / "focused-smoke-config.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    print(f"Running 18-game focused smoke test (6 orientations x 3 games)...")
    print(f"Forge JAR: {jar_path}")
    print(f"Output Directory: {out_dir}")

    engine = ForgeEngine(jar_path, quiet=False)
    run_experiment(config_path, engine)

    # 1. Generate behavioral summary
    print("\nGenerating behavioral summary...")
    beh_summary_script = repo_root / "scripts" / "generate_behavioral_summary.py"
    beh_output_path = out_dir / "behavioral-summary.txt"
    subprocess.run([sys.executable, str(beh_summary_script), str(out_dir), str(beh_output_path)], check=True)

    # 2. Generate diagnostic index
    print("\nGenerating diagnostic index...")
    diag_script = repo_root / "scripts" / "build_diagnostic_index.py"
    diag_output_path = out_dir / "diagnostic-index.txt"
    subprocess.run([sys.executable, str(diag_script), str(out_dir), str(diag_output_path)], check=True)

    # 3. Verify exception / runtime integrity gate across all 18 logs
    print("\nVerifying runtime integrity across all 18 logs...")
    log_files = sorted(out_dir.glob("*.log"))
    exception_counts = {p: 0 for p in EXCEPTION_PATTERNS}
    total_exceptions = 0

    for log_f in log_files:
        content = log_f.read_text(encoding="utf-8", errors="replace")
        for p in EXCEPTION_PATTERNS:
            matches = re.findall(p, content)
            if matches:
                exception_counts[p] += len(matches)
                total_exceptions += len(matches)

    print(f"Total Log Files Checked: {len(log_files)}")
    print(f"Total Runtime Exceptions Found: {total_exceptions}")
    for p, c in exception_counts.items():
        print(f"  - {p}: {c}")

    if total_exceptions > 0:
        print("ERROR: Runtime integrity gate failed!", file=sys.stderr)
        return 1

    print("\nSUCCESS: All 18 games complete, behavioral logs and diagnostic reports generated clean!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
