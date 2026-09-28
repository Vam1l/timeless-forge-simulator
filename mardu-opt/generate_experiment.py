#!/usr/bin/env python3
# Triggered analysis run: 2026-09-28
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "stock.dck"

VARIANTS = {
    "stock": {},
    "ragavan3": {"Juggernaut Peddler": -1, "Ragavan, Nimble Pilferer": 1},
    "ragavan4": {"Juggernaut Peddler": -2, "Ragavan, Nimble Pilferer": 2},
    "prison3": {"Juggernaut Peddler": -1, "Static Prison": 1},
    "bombardment4": {"Juggernaut Peddler": -1, "Goblin Bombardment": 1},
    "swords3-ragavan3": {"Swords to Plowshares": -1, "Ragavan, Nimble Pilferer": 1},
    "land22-ragavan3": {"Elegant Parlor": -1, "Ragavan, Nimble Pilferer": 1},
    "land24": {"Juggernaut Peddler": -1, "Elegant Parlor": 1},
    "thoughtseize3": {"Juggernaut Peddler": -1, "Thoughtseize": 1},
}

OPPONENTS = {
    "mirror": "mardu-opt/stock.dck",
    "show-and-tell": "froganimator-splits/show-and-tell.dck",
    "reanimator": "froganimator-splits/reanimator.dck",
    "bug-froganimator": "froganimator-splits/split-grief2.dck",
    "pure-sultai": "froganimator-splits/pure-sultai.dck",
}

def parse_main(text):
    before, rest = text.split("[Main]\n", 1)
    main, side = rest.split("\n[Sideboard]\n", 1)
    cards = []
    for line in main.strip().splitlines():
        qty, name = line.split(" ", 1)
        cards.append([int(qty), name])
    return before, cards, side

def build(name, changes):
    before, cards, side = parse_main(BASE.read_text())
    counts = {card: qty for qty, card in cards}
    order = [card for _, card in cards]
    for card, delta in changes.items():
        counts[card] = counts.get(card, 0) + delta
        if card not in order:
            order.append(card)
    if sum(counts.values()) != 60 or min(counts.values()) < 0:
        raise ValueError(f"invalid variant {name}: {sum(counts.values())}")
    main = "\n".join(f"{counts[c]} {c}" for c in order if counts[c])
    text = before.replace("Name=mardu-stock", f"Name=mardu-{name}") + "[Main]\n" + main + "\n\n[Sideboard]\n" + side
    (ROOT / f"{name}.dck").write_text(text)

for name, changes in VARIANTS.items():
    if name != "stock":
        build(name, changes)

matchups = []
for variant in VARIANTS:
    for opponent, path in OPPONENTS.items():
        variant_path = f"mardu-opt/{variant}.dck"
        matchups.extend([
            {"name": f"{variant}-vs-{opponent}", "deck_a": variant_path, "deck_b": path},
            {"name": f"{opponent}-vs-{variant}", "deck_a": path, "deck_b": variant_path},
        ])

config = {
    "name": "Mardu Energy maindeck optimization 2026-09-28",
    "deck_dir": ".",
    "games_preboard": 40,
    "games_postboard": 0,
    "clock_seconds": 120,
    "matchups": matchups,
}
(ROOT / "experiment.json").write_text(json.dumps(config, indent=2) + "\n")
print(f"Generated {len(VARIANTS)} decks and {len(matchups)} oriented matchups")
