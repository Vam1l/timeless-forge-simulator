#!/usr/bin/env python3
"""Entry point adding exact Forge display-name outcome mapping to run_validation.py."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import re

SCRIPT = Path(__file__).with_name("run_validation.py")
spec = importlib.util.spec_from_file_location("remaining_nine_core", SCRIPT)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)

DISPLAY_NAMES = {
    "white": "White Weenie",
    "madness": "Madness Burn",
    "green": "Green Stompy",
    "black": "Black Sacrifice",
    "blue": "Blue Terror",
    "jund": "Jund Wildfire",
    "esper": "Esper Control",
    "sultai": "Sultai Beans",
    "tron": "Tron",
}

_original_winner = core.winner


def parsed_winner(text: str):
    won = _original_winner(text)
    if won:
        return won
    if re.search(r"Game Result:.*\b(?:draw|drawn)\b|Game Outcome:.*\b(?:draw|drawn)\b", text, re.I):
        return "DRAW"
    return None


def result_for_target(target: str, a: str, b: str, won: str):
    del a, b
    if won == "DRAW":
        return "draw"
    if not won:
        return "unparsed"
    normalized = core.normalize(won)
    for key, display in DISPLAY_NAMES.items():
        if core.normalize(display) in normalized:
            return "win" if key == target else "loss"
    return "unparsed"


core.winner = parsed_winner
core.result_for_target = result_for_target


if __name__ == "__main__":
    raise SystemExit(core.main())
