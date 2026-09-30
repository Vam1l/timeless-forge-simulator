from pathlib import Path
import json

BASE = {
    "Glaring Fleshraker": 4,
    "Sowing Mycospawn": 4,
    "Thought-Knot Seer": 4,
    "Devourer of Destiny": 4,
    "It That Heralds the End": 4,
    "Wastescape Battlemage": 2,
    "Sire of Seven Deaths": 1,
    "Kozilek's Command": 4,
    "Chalice of the Void": 4,
    "Once Upon a Time": 4,
    "Ancient Tomb": 4,
    "Eldrazi Temple": 4,
    "Ugin's Labyrinth": 4,
    "Eye of Ugin": 3,
    "Cavern of Souls": 3,
    "Petrified Hamlet": 2,
    "Karplusan Forest": 2,
    "Forest": 1,
    "Wastes": 1,
    "Strip Mine": 1,
}

SIDEBOARD = {
    "Dismember": 3,
    "Leyline of the Void": 3,
    "Thorn of Amethyst": 2,
    "Disruptor Flute": 2,
    "Vexing Bauble": 2,
    "Wastescape Battlemage": 1,
    "Bojuka Bog": 1,
    "Strip Mine": 1,
}

VARIANTS = {
    "baseline": {},
    "eye2-cavern4": {"Eye of Ugin": -1, "Cavern of Souls": 1},
    "eye4-karplusan1": {"Eye of Ugin": 1, "Karplusan Forest": -1},
    "ouat3-battlemage3": {"Once Upon a Time": -1, "Wastescape Battlemage": 1},
    "ouat2-battlemage3-sire2": {"Once Upon a Time": -2, "Wastescape Battlemage": 1, "Sire of Seven Deaths": 1},
    "strip2-karplusan1": {"Strip Mine": 1, "Karplusan Forest": -1},
    "chalice3-battlemage3": {"Chalice of the Void": -1, "Wastescape Battlemage": 1},
    "sire2-karplusan1": {"Sire of Seven Deaths": 1, "Karplusan Forest": -1},
}

OPPONENTS = {
    "bug": "froganimator-splits/split-grief2.dck",
    "mardu": "mardu-opt/stock.dck",
    "showtell": "froganimator-splits/show-and-tell.dck",
}

OUT = Path("eldrazi-opt")
OUT.mkdir(exist_ok=True)

def apply(delta):
    d = dict(BASE)
    for card, change in delta.items():
        d[card] = d.get(card, 0) + change
        if d[card] == 0:
            del d[card]
    assert sum(d.values()) == 60, sum(d.values())
    return d

def render(name, main):
    lines = ["[metadata]", f"Name=eldrazi-{name}", "", "[Main]"]
    for card, n in main.items():
        lines.append(f"{n} {card}")
    lines += ["", "[Sideboard]"]
    for card, n in SIDEBOARD.items():
        lines.append(f"{n} {card}")
    return "\n".join(lines) + "\n"

matchups = []
for variant, delta in VARIANTS.items():
    deck_path = OUT / f"{variant}.dck"
    deck_path.write_text(render(variant, apply(delta)))
    for opp_name, opp_path in OPPONENTS.items():
        matchups.append({
            "name": f"{variant}-vs-{opp_name}",
            "deck_a": str(deck_path),
            "deck_b": opp_path,
        })
        matchups.append({
            "name": f"{opp_name}-vs-{variant}",
            "deck_a": opp_path,
            "deck_b": str(deck_path),
        })

config = {
    "name": "Eldrazi optimization screen 2026-09-30",
    "deck_dir": ".",
    "games_preboard": 80,
    "games_postboard": 0,
    "clock_seconds": 120,
    "matchups": matchups,
}
(OUT / "experiment.json").write_text(json.dumps(config, indent=2) + "\n")
print(f"Generated {len(VARIANTS)} variants and {len(matchups)} matchups")
