#!/usr/bin/env python3
"""
Run diagnostic matchups with quiet=False to capture full play-by-play telemetry.
Usage: python scripts/run_diagnostic_batch.py --forge-jar /path/to/forge.jar --output diagnostic-results
"""

import argparse
import json
import sys
from pathlib import Path

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from timeless_forge.runner import ForgeEngine, run_experiment

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--matchup-indices', type=int, nargs='+', help='Indices of diagnostic matchups to run (default: all 16)')
    parser.add_argument('--forge-jar', type=Path, required=True, help='Path to forge.jar')
    parser.add_argument('--output', type=Path, required=True, help='Output directory')
    parser.add_argument('--config', type=Path, default=repo_root / "battlebox" / "diagnostic.json", help='Path to diagnostic config')
    args = parser.parse_args()
    
    # Load diagnostic configuration
    with open(args.config) as f:
        full_config = json.load(f)
    
    # Filter to requested matchups if specified
    if args.matchup_indices is not None:
        matchup_indices = set(args.matchup_indices)
        filtered_matchups = [
            m for i, m in enumerate(full_config['matchups'])
            if i in matchup_indices
        ]
    else:
        filtered_matchups = full_config['matchups']
    
    # Create batch config
    batch_config = dict(full_config)
    original_deck_dir = Path(full_config.get('deck_dir', 'decks'))
    if (repo_root / original_deck_dir).exists():
        batch_config['deck_dir'] = str((repo_root / original_deck_dir).resolve())
    elif (args.config.parent / original_deck_dir).exists():
        batch_config['deck_dir'] = str((args.config.parent / original_deck_dir).resolve())
    else:
        batch_config['deck_dir'] = str(original_deck_dir.resolve())
    batch_config['matchups'] = filtered_matchups
    batch_config['output_dir'] = str(args.output)
    
    # Write temp config
    temp_config_path = args.output.parent / f"diagnostic-config-{args.output.name}.json"
    temp_config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(temp_config_path, 'w') as f:
        json.dump(batch_config, f, indent=2)
    
    print(f"Running {len(filtered_matchups)} diagnostic matchups with quiet=False")
    print(f"Output: {args.output}")
    
    # Run with real Forge engine in VERBOSE mode (quiet=False)
    engine = ForgeEngine(args.forge_jar, quiet=False)
    try:
        result_dir = run_experiment(temp_config_path, engine)
        print(f"\nDiagnostic batch complete: {result_dir}")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
