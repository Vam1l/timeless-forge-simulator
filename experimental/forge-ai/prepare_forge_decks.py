#!/usr/bin/env python3
"""Install unchanged battle-box decks into Forge's constructed-deck directory."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import sys

EXPECTED = (
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
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="battlebox/decks", type=Path)
    ap.add_argument(
        "--destination",
        type=Path,
        default=Path.home() / ".forge" / "decks" / "constructed",
    )
    args = ap.parse_args()
    source = args.source.resolve()
    destination = args.destination.expanduser().resolve()

    actual_source = {p.name for p in source.glob("*.dck") if p.is_file()}
    expected = set(EXPECTED)
    if actual_source != expected:
        print(f"Unexpected battle-box deck set: {sorted(actual_source)}", file=sys.stderr)
        return 1

    destination.mkdir(parents=True, exist_ok=True)
    for name in EXPECTED:
        src = source / name
        dst = destination / name
        shutil.copyfile(src, dst)
        if src.read_bytes() != dst.read_bytes():
            print(f"Deck copy differs byte-for-byte: {name}", file=sys.stderr)
            return 1
        print(f"OK {sha256(src)}  {dst}")

    installed = {p.name for p in destination.glob("*.dck") if p.name in expected}
    if installed != expected:
        print(f"Missing installed deck(s): {sorted(expected - installed)}", file=sys.stderr)
        return 1

    print(f"Installed and byte-verified all {len(EXPECTED)} decks in {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
