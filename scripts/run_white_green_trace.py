#!/usr/bin/env python3
"""Run a verbose, read-only Forge trace for the focused White/Green diagnostic."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECKS = ROOT / "battlebox" / "decks"
WHITE = "Mono-White Tokens ETB-Convoke"
GREEN = "Mono-Green Midrange"
CREATURES = {
    "Llanowar Elves": (1, 1), "Elvish Mystic": (1, 1), "Llanowar Visionary": (2, 2),
    "Pestilent Wolf": (2, 2), "Briarpack Alpha": (3, 3), "Leatherback Baloth": (4, 5),
    "Penumbra Spider": (2, 4), "Territorial Baloth": (4, 4), "Annoyed Altisaur": (6, 5),
    "Arbor Colossus": (6, 6), "Reclamation Sage": (2, 1), "Novice Inspector": (1, 2),
    "Kor Skyfisher": (2, 3), "Inspiring Overseer": (2, 1), "Attended Knight": (2, 2),
    "Doomed Traveler": (1, 1), "Suture Priest": (1, 1), "Goldnight Commander": (2, 2),
    "Mentor of the Meek": (2, 2), "Angel of Invention": (2, 1),
    "Soldier": (1, 1), "Spirit": (1, 1), "Thopter": (1, 1),
}
GREEN_BIG = {"Leatherback Baloth", "Penumbra Spider", "Territorial Baloth", "Arbor Colossus", "Annoyed Altisaur"}


def player(line: str) -> str | None:
    return GREEN if GREEN in line else WHITE if WHITE in line else None


def state(board: dict[str, Counter], life: dict[str, int], name: str) -> dict:
    cards = board[name]
    creature_names = {card: n for card, n in cards.items() if card in CREATURES}
    power = sum(CREATURES[card][0] * n for card, n in creature_names.items())
    toughness = sum(CREATURES[card][1] * n for card, n in creature_names.items())
    dorks = cards["Llanowar Elves"] + cards["Elvish Mystic"]
    lands = cards["Forest"] + cards["Plains"] + cards["Rogue's Passage"]
    return {"life": life[name], "lands": lands, "mana_sources_estimate": lands + dorks,
            "creatures": sum(creature_names.values()), "power": power, "toughness": toughness,
            "power_4_plus": sum(n for c, n in creature_names.items() if CREATURES[c][0] >= 4),
            "power_3_plus": sum(n for c, n in creature_names.items() if CREATURES[c][0] >= 3),
            "flying": sum(n for c, n in creature_names.items() if c in {"Inspiring Overseer", "Angel of Invention", "Spirit", "Thopter"}),
            "reach": cards["Penumbra Spider"], "battlefield": dict(sorted(cards.items()))}


def parse(log: Path, orientation: str) -> list[dict]:
    games, current = [], None
    board = {WHITE: Counter(), GREEN: Counter()}
    life = {WHITE: 20, GREEN: 20}
    turn = 0
    phase = None
    last_cast: dict[str, tuple[str, str]] = {}
    for raw in log.read_text(encoding="utf-8").splitlines():
        if match := re.match(r"Turn: Turn (\d+) \((.+)\)", raw):
            if current is None:
                current = {"orientation": orientation, "events": [], "turns": [], "mulligans": {}, "winner": None}
            turn, active = int(match.group(1)), player(match.group(2))
            if active:
                current["turns"].append({"turn": turn, "active": active,
                                         "start": {WHITE: state(board, life, WHITE), GREEN: state(board, life, GREEN)}})
            continue
        if match := re.match(r"Mulligan: (.+) has kept a hand of (\d+) cards", raw):
            if current is None:
                current = {"orientation": orientation, "events": [], "turns": [], "mulligans": {}, "winner": None}
            who = player(match.group(1))
            if who:
                current["mulligans"][who] = int(match.group(2))
        if current is None:
            continue
        if match := re.match(r"Phase: .+?'s (.+)", raw):
            phase = match.group(1)
        if match := re.match(r"Land: (.+) played (.+?) \(\d+\)", raw):
            who, card = player(match.group(1)), match.group(2)
            if who:
                board[who][card] += 1
                current["events"].append({"type": "land", "turn": turn, "phase": phase, "controller": who, "card": card})
        if match := re.match(r"Add To Stack: (.+) cast (.+?)(?: targeting (.+))?$", raw):
            who, card, targets = player(match.group(1)), match.group(2), match.group(3)
            if who:
                last_cast[card] = (who, card)
                current["events"].append({"type": "cast", "turn": turn, "phase": phase, "controller": who, "card": card, "targets": targets})
        if match := re.match(r"Resolve Stack: (.+?)(?: \(\d+\))?(?: -|$)", raw):
            card = match.group(1)
            if card in last_cast:
                who, _ = last_cast[card]
                if card in CREATURES or card in {"Colossal Majesty", "Tocasia's Welcome", "Conclave Tribunal", "Ajani Steadfast", "Vivien, Champion of the Wilds"}:
                    board[who][card] += 1
                current["events"].append({"type": "resolve", "turn": turn, "phase": phase, "controller": who, "card": card})
        if match := re.match(r"Zone Change: (.+?) \(\d+\) was put into (.+?) from Battlefield", raw):
            card, zone = match.group(1), match.group(2)
            for who in (WHITE, GREEN):
                if board[who][card]:
                    board[who][card] -= 1
                    if not board[who][card]:
                        del board[who][card]
                    current["events"].append({"type": "removed", "turn": turn, "phase": phase, "controller": who, "card": card, "zone": zone})
                    break
        if match := re.match(r"Life: Life: (.+) (-?\d+) > (-?\d+)", raw):
            who = player(match.group(1))
            if who:
                life[who] = int(match.group(3))
                current["events"].append({"type": "life", "turn": turn, "phase": phase, "controller": who, "from": int(match.group(2)), "to": life[who]})
        if raw.startswith("Combat:"):
            current["events"].append({"type": "combat", "turn": turn, "phase": phase, "detail": raw[8:]})
        if match := re.match(r"Game Result: Game (\d+) ended.*? (.+?) has won!", raw):
            current["game"] = int(match.group(1))
            current["winner"] = player(match.group(2))
            current["ending_turn"] = turn
            current["ending_life"] = dict(life)
            games.append(current)
            current, board, life, last_cast = None, {WHITE: Counter(), GREEN: Counter()}, {WHITE: 20, GREEN: 20}, {}
    return games


def run(jar: Path, first: str, second: str, games: int, seed: int, log: Path) -> None:
    constructed = Path.home() / ".forge" / "decks" / "constructed"
    constructed.mkdir(parents=True, exist_ok=True)
    for filename in (first, second):
        shutil.copy2(DECKS / filename, constructed / filename)
    command = ["java", "-jar", str(jar), "sim", "-d", first, second, "-D", str(DECKS),
               "-n", str(games), "-c", "120", "-s", str(seed)]
    if shutil.which("xvfb-run") and "DISPLAY" not in __import__("os").environ:
        command = ["xvfb-run", "-a"] + command
    complete = subprocess.run(command, cwd=jar.parent, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, check=False)
    log.write_text(complete.stdout, encoding="utf-8")
    if complete.returncode:
        raise RuntimeError(complete.stdout[-4000:])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forge-jar", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--games-per-orientation", type=int, default=50)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    plans = [("white-listed-first", "01-white-weenie.dck", "03-green-stompy.dck", 97001),
             ("green-listed-first", "03-green-stompy.dck", "01-white-weenie.dck", 97002)]
    all_games = []
    for label, first, second, seed in plans:
        log = args.output / f"{label}.log"
        run(args.forge_jar, first, second, args.games_per_orientation, seed, log)
        all_games.extend(parse(log, label))
    (args.output / "trace.json").write_text(json.dumps(all_games, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(all_games)} traced games to {args.output}")


if __name__ == "__main__":
    main()
