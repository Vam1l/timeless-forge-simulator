from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

LINE_RE = re.compile(r"^\s*(\d+)\s+(.+?)\s*$")


@dataclass
class Deck:
    path: Path
    metadata: list[str] = field(default_factory=list)
    main: dict[str, int] = field(default_factory=dict)
    sideboard: dict[str, int] = field(default_factory=dict)

    @property
    def main_count(self) -> int:
        return sum(self.main.values())

    @property
    def sideboard_count(self) -> int:
        return sum(self.sideboard.values())


def _add_card(target: dict[str, int], line: str, path: Path, number: int) -> None:
    match = LINE_RE.match(line)
    if not match:
        raise ValueError(f"{path}:{number}: expected '<quantity> <card name>'")
    quantity, name = int(match.group(1)), match.group(2)
    if quantity < 1:
        raise ValueError(f"{path}:{number}: quantity must be positive")
    target[name] = target.get(name, 0) + quantity


def load_deck(path: str | Path) -> Deck:
    path = Path(path)
    deck = Deck(path=path)
    section = "metadata"
    for number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            label = line[1:-1].strip().lower()
            section = {"main": "main", "sideboard": "sideboard"}.get(label, "metadata")
            deck.metadata.append(raw)
            continue
        if section == "main":
            _add_card(deck.main, line, path, number)
        elif section == "sideboard":
            _add_card(deck.sideboard, line, path, number)
        else:
            deck.metadata.append(raw)
    return deck


def validate_deck(deck: Deck) -> list[str]:
    errors: list[str] = []
    if deck.main_count < 60:
        errors.append(f"main deck has {deck.main_count} cards; expected at least 60")
    if deck.sideboard_count > 15:
        errors.append(f"sideboard has {deck.sideboard_count} cards; expected at most 15")
    return errors


def parse_card_specs(specs: list[str]) -> dict[str, int]:
    cards: dict[str, int] = {}
    for i, spec in enumerate(specs, 1):
        match = LINE_RE.match(spec)
        if not match:
            raise ValueError(f"sideboard entry {i}: expected '<quantity> <card name>'")
        quantity, name = int(match.group(1)), match.group(2)
        cards[name] = cards.get(name, 0) + quantity
    return cards


def apply_sideboard(deck: Deck, plan: dict[str, list[str]]) -> Deck:
    cards_in = parse_card_specs(plan.get("in", []))
    cards_out = parse_card_specs(plan.get("out", []))
    if sum(cards_in.values()) != sum(cards_out.values()):
        raise ValueError("sideboard plan must move the same number of cards in and out")
    main, side = dict(deck.main), dict(deck.sideboard)
    for name, quantity in cards_out.items():
        if main.get(name, 0) < quantity:
            raise ValueError(f"cannot board out {quantity} {name}; main deck has {main.get(name, 0)}")
        main[name] -= quantity
        side[name] = side.get(name, 0) + quantity
    for name, quantity in cards_in.items():
        if side.get(name, 0) < quantity:
            raise ValueError(f"cannot board in {quantity} {name}; sideboard has {side.get(name, 0)}")
        side[name] -= quantity
        main[name] = main.get(name, 0) + quantity
    return Deck(deck.path, list(deck.metadata), {k: v for k, v in main.items() if v}, {k: v for k, v in side.items() if v})


def write_deck(deck: Deck, path: str | Path) -> Path:
    path = Path(path)
    lines = ["[metadata]", "Name=" + path.stem, "", "[Main]"]
    lines.extend(f"{quantity} {name}" for name, quantity in sorted(deck.main.items()))
    lines.extend(["", "[Sideboard]"])
    lines.extend(f"{quantity} {name}" for name, quantity in sorted(deck.sideboard.items()))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
