from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .deck import load_deck, validate_deck
from .runner import ForgeEngine, MockEngine, run_experiment


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="timeless-forge")
    commands = root.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="validate one deck or every .dck in a directory")
    validate.add_argument("path", type=Path)
    run = commands.add_parser("run", help="run an experiment")
    run.add_argument("config", type=Path)
    run.add_argument("--forge-jar", type=Path)
    run.add_argument("--java", default="java")
    run.add_argument("--mock", action="store_true")
    run.add_argument("--seed", type=int, default=1)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "validate":
        paths = sorted(args.path.glob("*.dck")) if args.path.is_dir() else [args.path]
        failed = False
        for path in paths:
            errors = validate_deck(load_deck(path))
            print(f"{'FAIL' if errors else 'OK  '} {path}")
            for error in errors:
                print(f"     {error}")
            failed |= bool(errors)
        return int(failed)
    if args.mock:
        engine = MockEngine(seed=args.seed)
    elif args.forge_jar:
        engine = ForgeEngine(args.forge_jar, args.java)
    else:
        print("error: --forge-jar is required unless --mock is used", file=sys.stderr)
        return 2
    output = run_experiment(args.config.resolve(), engine)
    print(f"Results: {output}")
    return 0
