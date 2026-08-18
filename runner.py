from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import random
import re
import subprocess
import tempfile
from typing import Protocol

from .deck import apply_sideboard, load_deck, validate_deck, write_deck
from .stats import wilson_interval

WIN_PATTERNS = (
    re.compile(r"(?im)^(.+?)\s+(?:has won|wins the game|won the game)\b"),
    re.compile(r"(?im)^Winner:\s*(.+?)\s*$"),
)
DRAW_PATTERN = re.compile(r"(?im)\b(?:game is a draw|result:\s*draw|timed out)\b")


@dataclass
class BatchResult:
    matchup: str
    phase: str
    deck_a: str
    deck_b: str
    requested_games: int
    parsed_games: int
    wins_a: int
    wins_b: int
    draws: int
    unparsed: int
    win_rate_a: float
    ci95_low: float
    ci95_high: float
    raw_log: str


class Engine(Protocol):
    def run(self, deck_a: Path, deck_b: Path, games: int, clock: int) -> str: ...


class ForgeEngine:
    def __init__(self, jar: Path, java: str = "java"):
        if not jar.is_file():
            raise FileNotFoundError(f"Forge jar not found: {jar}")
        self.jar, self.java = jar.resolve(), java

    def run(self, deck_a: Path, deck_b: Path, games: int, clock: int) -> str:
        command = [self.java, "-jar", str(self.jar), "sim", "-d", deck_a.name, deck_b.name,
                   "-D", str(deck_a.parent.resolve()), "-n", str(games), "-q", "-c", str(clock)]
        completed = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, check=False)
        if completed.returncode:
            raise RuntimeError(f"Forge exited {completed.returncode}\n{completed.stdout[-4000:]}")
        return completed.stdout


class MockEngine:
    def __init__(self, seed: int = 1, probability_a: float = 0.5):
        self.random = random.Random(seed)
        self.probability_a = probability_a

    def run(self, deck_a: Path, deck_b: Path, games: int, clock: int) -> str:
        return "\n".join(
            f"Winner: {deck_a.stem if self.random.random() < self.probability_a else deck_b.stem}"
            for _ in range(games)
        )


def parse_output(text: str, deck_a: str, deck_b: str, requested: int) -> tuple[int, int, int, int]:
    winners: list[str] = []
    for pattern in WIN_PATTERNS:
        winners = [m.strip().lower() for m in pattern.findall(text)]
        if winners:
            break
    a, b = Path(deck_a).stem.lower(), Path(deck_b).stem.lower()
    wins_a = sum(1 for winner in winners if a in winner)
    wins_b = sum(1 for winner in winners if b in winner)
    draws = len(DRAW_PATTERN.findall(text))
    unparsed = max(0, requested - wins_a - wins_b - draws)
    return wins_a, wins_b, draws, unparsed


def _batch(engine: Engine, matchup: str, phase: str, deck_a: Path, deck_b: Path,
           games: int, clock: int, log_path: Path) -> BatchResult:
    text = engine.run(deck_a, deck_b, games, clock)
    log_path.write_text(text, encoding="utf-8")
    wins_a, wins_b, draws, unparsed = parse_output(text, deck_a.name, deck_b.name, games)
    decisive = wins_a + wins_b
    low, high = wilson_interval(wins_a, decisive)
    return BatchResult(matchup, phase, deck_a.stem, deck_b.stem, games,
                       wins_a + wins_b + draws, wins_a, wins_b, draws, unparsed,
                       wins_a / decisive if decisive else 0.0, low, high, str(log_path))


def run_experiment(config_path: Path, engine: Engine) -> Path:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    deck_dir = (config_path.parent / config.get("deck_dir", "decks")).resolve()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = (config_path.parent / config.get("output_dir", f"../results/{run_id}")).resolve()
    output.mkdir(parents=True, exist_ok=True)
    clock = int(config.get("clock_seconds", 120))
    results: list[BatchResult] = []
    with tempfile.TemporaryDirectory(prefix="timeless-forge-") as temporary:
        boarded_dir = Path(temporary)
        for index, matchup in enumerate(config["matchups"], 1):
            deck_a_path, deck_b_path = deck_dir / matchup["deck_a"], deck_dir / matchup["deck_b"]
            deck_a, deck_b = load_deck(deck_a_path), load_deck(deck_b_path)
            errors = validate_deck(deck_a) + validate_deck(deck_b)
            if errors:
                raise ValueError("; ".join(errors))
            label = matchup.get("name", f"{deck_a_path.stem}-vs-{deck_b_path.stem}")
            pre = int(matchup.get("games_preboard", config.get("games_preboard", 0)))
            post = int(matchup.get("games_postboard", config.get("games_postboard", 0)))
            if pre:
                results.append(_batch(engine, label, "preboard", deck_a_path, deck_b_path,
                                      pre, clock, output / f"{index:02d}-preboard.log"))
            if post:
                a_boarded = write_deck(apply_sideboard(deck_a, matchup.get("sideboard_a", {})), boarded_dir / f"{index:02d}-a.dck")
                b_boarded = write_deck(apply_sideboard(deck_b, matchup.get("sideboard_b", {})), boarded_dir / f"{index:02d}-b.dck")
                results.append(_batch(engine, label, "postboard", a_boarded, b_boarded,
                                      post, clock, output / f"{index:02d}-postboard.log"))
    payload = {
        "schema_version": 1,
        "run_id": run_id,
        "experiment": config.get("name", config_path.stem),
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "results": [asdict(result) for result in results],
    }
    (output / "summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    fields = list(asdict(results[0]).keys()) if results else []
    with (output / "summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if fields:
            writer.writeheader(); writer.writerows(asdict(result) for result in results)
    lines = [f"# {payload['experiment']}", "", "| Matchup | Phase | Games | A wins | B wins | Draws | A win rate | 95% CI | Unparsed |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for result in results:
        lines.append(f"| {result.matchup} | {result.phase} | {result.parsed_games} | {result.wins_a} | {result.wins_b} | {result.draws} | {result.win_rate_a:.1%} | {result.ci95_low:.1%}–{result.ci95_high:.1%} | {result.unparsed} |")
    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output
