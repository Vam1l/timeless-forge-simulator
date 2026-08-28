#!/usr/bin/env python3
"""
Run a subset of matchups from the round-robin configuration.
Usage: python scripts/run_matchup_batch.py --matchup-indices 0 1 2 3 4 --forge-jar /path/to/forge.jar --output results_dir
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
    parser.add_argument('--matchup-indices', type=int, nargs='+', required=True, help='Indices of matchups to run')
    parser.add_argument('--forge-jar', type=Path, required=True, help='Path to forge.jar')
    parser.add_argument('--output', type=Path, required=True, help='Output directory')
    args = parser.parse_args()
    
    # Load full configuration
    config_path = repo_root / "battlebox" / "roundrobin.json"
    with open(config_path) as f:
        full_config = json.load(f)
    
    # Filter to requested matchups
    matchup_indices = set(args.matchup_indices)
    filtered_matchups = [
        m for i, m in enumerate(full_config['matchups'])
        if i in matchup_indices
    ]
    
    # Create batch config
    batch_config = dict(full_config)
    batch_config['matchups'] = filtered_matchups
    batch_config['output_dir'] = str(args.output)
    
    # Write temp config
    temp_config_path = args.output.parent / f"batch-config-{args.output.name}.json"
    temp_config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(temp_config_path, 'w') as f:
        json.dump(batch_config, f, indent=2)
    
    print(f"Running {len(filtered_matchups)} matchups from config {temp_config_path}")
    print(f"Output: {args.output}")
    
    # Run with real Forge engine
    engine = ForgeEngine(args.forge_jar)
    try:
        result_dir = run_experiment(temp_config_path, engine)
        print(f"\nBatch complete: {result_dir}")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
