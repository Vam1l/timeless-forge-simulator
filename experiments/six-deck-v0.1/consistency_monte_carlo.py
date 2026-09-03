#!/usr/bin/env python3
"""Reproducible opening-hand and early-mana Monte Carlo for Battle Box v0.1."""

from __future__ import annotations

import argparse
import csv
import random
from collections import Counter
from pathlib import Path


LANDS = {
    "Plains", "Forest", "Mountain", "Swamp", "Island",
    "Tinder Farm", "Rugged Highlands",
}
MANA_ACCEL = {"Llanowar Elves", "Wild Growth"}
STORM_FILTER = {"Wild Cantor", "Chromatic Star"}


def read_deck(path: Path) -> list[str]:
    cards: list[str] = []
    in_main = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line == "[Main]":
            in_main = True
            continue
        if not in_main or not line or line.startswith("["):
            continue
        count, name = line.split(" ", 1)
        cards.extend([name] * int(count))
    if len(cards) != 60:
        raise ValueError(f"{path.name}: expected 60 cards, found {len(cards)}")
    return cards


def is_land(card: str) -> bool:
    return card in LANDS


def storm_colors(hand: list[str]) -> tuple[bool, bool]:
    red = any(c in {"Mountain", "Tinder Farm", "Rugged Highlands"} for c in hand)
    green = any(c in {"Forest", "Tinder Farm", "Rugged Highlands"} for c in hand)
    # A red or green source can cast Cantor; Star can filter once any mana exists.
    if (red or green) and any(c in STORM_FILTER for c in hand):
        red = green = True
    return red, green


def keep(deck_name: str, hand: list[str], mulligans: int, storm_one_land: bool = False) -> bool:
    lands = sum(map(is_land, hand))
    if mulligans >= 2:  # Keep seven-card draws after bottoming to five.
        return True
    if "red-burn" in deck_name:
        return 1 <= lands <= 3
    if "green-ramp" in deck_name:
        return 2 <= lands <= 4 or (lands == 1 and any(c in MANA_ACCEL for c in hand))
    if "gruul-chatterstorm" in deck_name:
        red, green = storm_colors(hand)
        if 2 <= lands <= 4 and red and green:
            return True
        if storm_one_land and lands == 1:
            land = next(c for c in hand if is_land(c))
            filters = {"Wild Cantor", "Chromatic Star"}
            if land == "Forest":
                filters.add("Tinder Wall")
            return land in {"Forest", "Mountain"} and any(c in filters for c in hand)
        return False
    return 2 <= lands <= 4


def target_lands(deck_name: str) -> int:
    if "red-burn" in deck_name:
        return 2
    if "green-ramp" in deck_name or "gruul-chatterstorm" in deck_name:
        return 2
    return 3


def bottom_cards(deck_name: str, seven: list[str], mulligans: int, rng: random.Random) -> list[str]:
    hand = seven.copy()
    target = target_lands(deck_name)
    for _ in range(mulligans):
        lands = [i for i, c in enumerate(hand) if is_land(c)]
        spells = [i for i, c in enumerate(hand) if not is_land(c)]
        if len(lands) > target:
            idx = rng.choice(lands)
        elif spells:
            # Random among spells avoids inventing card-specific strategic skill.
            idx = rng.choice(spells)
        else:
            idx = rng.randrange(len(hand))
        hand.pop(idx)
    return hand


def simulate(
    deck_name: str,
    deck: list[str],
    trials: int,
    seed: int,
    storm_one_land: bool = False,
) -> dict[str, float]:
    rng = random.Random(seed)
    totals: Counter[str] = Counter()
    mulligan_total = 0
    effective_cards = 0

    for _ in range(trials):
        mulligans = 0
        while True:
            shuffled = deck.copy()
            rng.shuffle(shuffled)
            seven = shuffled[:7]
            library = shuffled[7:]
            if keep(deck_name, seven, mulligans, storm_one_land):
                break
            mulligans += 1

        hand = bottom_cards(deck_name, seven, mulligans, rng)
        mulligan_total += mulligans
        effective_cards += len(hand)
        totals[f"mull_{mulligans}"] += 1

        opening_lands = sum(map(is_land, hand))
        totals[f"opening_lands_{opening_lands}"] += 1
        if 1 <= opening_lands <= 4:
            totals["playable_land_count"] += 1

        if "gruul-chatterstorm" in deck_name:
            red, green = storm_colors(hand)
            totals["storm_both_colors_open"] += int(red and green)

        # On the play: no draw on turn one, then one card before turns 2-5.
        available = hand.copy()
        battlefield_lands: list[str] = []
        lands_in_play = 0
        for turn in range(1, 6):
            if turn >= 2 and library:
                available.append(library.pop(0))
            land_index = next((i for i, c in enumerate(available) if is_land(c)), None)
            if land_index is not None:
                battlefield_lands.append(available.pop(land_index))
                lands_in_play += 1
            if lands_in_play >= turn:
                totals[f"hit_land_{turn}"] += 1
            if turn == 3 and "gruul-chatterstorm" in deck_name:
                red, green = storm_colors(hand + available + battlefield_lands)
                totals["storm_both_colors_t3"] += int(red and green)

        seen_lands_t5 = opening_lands + sum(is_land(c) for c in shuffled[7:11])
        totals["flood_5plus_by_t5"] += int(seen_lands_t5 >= 5)

    pct = lambda key: 100.0 * totals[key] / trials
    return {
        "trials": trials,
        "avg_mulligans": mulligan_total / trials,
        "avg_starting_cards": effective_cards / trials,
        "keep_7_pct": pct("mull_0"),
        "to_6_pct": pct("mull_1"),
        "to_5_pct": pct("mull_2"),
        "playable_land_count_pct": pct("playable_land_count"),
        "hit_land_2_pct": pct("hit_land_2"),
        "hit_land_3_pct": pct("hit_land_3"),
        "hit_land_4_pct": pct("hit_land_4"),
        "flood_5plus_by_t5_pct": pct("flood_5plus_by_t5"),
        "storm_both_colors_open_pct": pct("storm_both_colors_open"),
        "storm_both_colors_t3_pct": pct("storm_both_colors_t3"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=250_000)
    parser.add_argument("--seed", type=int, default=96_001)
    parser.add_argument("--storm-one-land", action="store_true")
    parser.add_argument("--deck-dir", type=Path, default=Path(__file__).with_name("decks"))
    parser.add_argument("--out", type=Path, default=Path(__file__).with_name("consistency-results.csv"))
    args = parser.parse_args()

    rows = []
    for index, path in enumerate(sorted(args.deck_dir.glob("*.dck"))):
        result = simulate(
            path.stem,
            read_deck(path),
            args.trials,
            args.seed + index,
            storm_one_land=args.storm_one_land,
        )
        rows.append({"deck": path.stem, **result})

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    for row in rows:
        print(
            f"{row['deck']}: keep7={row['keep_7_pct']:.1f}% "
            f"T2/T3/T4={row['hit_land_2_pct']:.1f}/{row['hit_land_3_pct']:.1f}/{row['hit_land_4_pct']:.1f}% "
            f"floodT5={row['flood_5plus_by_t5_pct']:.1f}%"
        )


if __name__ == "__main__":
    main()
