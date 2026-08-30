#!/usr/bin/env python3
"""Verify byte-for-byte provenance of the recovered Forge AI source tree."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "experimental" / "forge-ai"
PATCH_ROOT = EXPERIMENT / "forge-patches"
MANIFEST = EXPERIMENT / "RECOVERED_BLOBS.txt"


def git_blob_sha(path: Path) -> str:
    completed = subprocess.run(
        ["git", "hash-object", "--no-filters", str(path)],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def main() -> int:
    expected: dict[str, str] = {}
    for raw_line in MANIFEST.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("PR2_FINAL_SHA="):
            continue
        relative, sha = line.split()
        if relative.startswith("forge/"):
            expected[relative] = sha

    actual_files = {
        path.relative_to(PATCH_ROOT).as_posix()
        for path in PATCH_ROOT.rglob("*")
        if path.is_file()
    }
    expected_files = set(expected)

    missing = sorted(expected_files - actual_files)
    unexpected = sorted(actual_files - expected_files)
    if missing or unexpected:
        if missing:
            print("Missing recovered patch files:", *missing, sep="\n  ", file=sys.stderr)
        if unexpected:
            print("Undocumented recovered patch files:", *unexpected, sep="\n  ", file=sys.stderr)
        return 1

    mismatches: list[tuple[str, str, str]] = []
    for relative in sorted(expected):
        path = PATCH_ROOT / relative
        actual_sha = git_blob_sha(path)
        expected_sha = expected[relative]
        if actual_sha != expected_sha:
            mismatches.append((relative, expected_sha, actual_sha))
        else:
            print(f"OK {expected_sha}  {relative}")

    if mismatches:
        print("Recovered Forge source blob integrity failure:", file=sys.stderr)
        for relative, expected_sha, actual_sha in mismatches:
            print(
                f"  {relative}: expected {expected_sha}, got {actual_sha}",
                file=sys.stderr,
            )
        return 1

    print(f"Verified {len(expected)} recovered Forge source blobs byte-for-byte.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
