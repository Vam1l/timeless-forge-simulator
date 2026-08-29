from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import csv
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil
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
    def __init__(self, jar: Path, java: str = "java", quiet: bool = True):
        if not jar.is_file():
            raise FileNotFoundError(f"Forge jar not found: {jar}")
        self.jar, self.java, self.quiet = jar.resolve(), java, quiet

    def run(self, deck_a: Path, deck_b: Path, games: int, clock: int) -> str:
        for d in (deck_a, deck_b):
            if d.is_file():
                for target_dir in [Path("data/decks/constructed"), Path.home() / ".forge/decks/constructed"]:
                    target_dir.mkdir(parents=True, exist_ok=True)
                    target_file = target_dir / d.name
                    if not target_file.exists() or target_file.stat().st_mtime < d.stat().st_mtime:
                        target_file.write_bytes(d.read_bytes())
        java_cmd = [self.java]
        if shutil.which("xvfb-run") and "DISPLAY" not in os.environ and self.java == "java":
            java_cmd = ["xvfb-run", "-a", self.java]
        command = java_cmd + ["-jar", str(self.jar), "sim", "-d", deck_a.name, deck_b.name,
                             "-D", str(deck_a.parent.resolve()), "-n", str(games), "-c", str(clock)]
        if self.quiet:
            command.append("-q")
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


def normalize_deck_name(name: str) -> str:
    stem = Path(name).stem.lower()
    stem = re.sub(r"^ai\(\d+\)-", "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"^(?:game outcome|winner):\s*", "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"^\d+[-_ ]*", "", stem)
    return re.sub(r"[^a-z0-9]", "", stem)


def parse_output(text: str, deck_a: str, deck_b: str, requested: int) -> tuple[int, int, int, int]:
    norm_a = normalize_deck_name(deck_a)
    norm_b = normalize_deck_name(deck_b)

    wins_a = 0
    wins_b = 0

    # 1. Try 'Game Result: Game N ended in X ms. PlayerName has won!'
    gr_matches = re.findall(r"Game Result:\s*Game\s+\d+\s+ended in \d+ ms\.\s*(.+?)\s+has won!", text, re.IGNORECASE)
    if not gr_matches:
        # 2. Try 'Winner: PlayerName' (MockEngine style)
        gr_matches = re.findall(r"^Winner:\s*(.+?)$", text, re.IGNORECASE | re.MULTILINE)

    if gr_matches:
        for winner in gr_matches:
            nw = normalize_deck_name(winner)
            if nw == norm_a or (norm_a and norm_a in nw) or (nw and nw in norm_a):
                wins_a += 1
            elif nw == norm_b or (norm_b and norm_b in nw) or (nw and nw in norm_b):
                wins_b += 1
    else:
        # 3. Fallback: 'Game Outcome: PlayerName has won'
        go_matches = re.findall(r"Game Outcome:\s*(.+?)\s+has won\b", text, re.IGNORECASE)
        for winner in go_matches:
            nw = normalize_deck_name(winner)
            if nw == norm_a or (norm_a and norm_a in nw) or (nw and nw in norm_a):
                wins_a += 1
            elif nw == norm_b or (norm_b and norm_b in nw) or (nw and nw in norm_b):
                wins_b += 1

    draw_matches = re.findall(r"\b(?:game is a draw|result:\s*draw|timed out)\b", text, re.IGNORECASE)
    draws = len(draw_matches)

    parsed = wins_a + wins_b + draws
    unparsed = max(0, requested - parsed)
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
    raw_deck_dir = Path(config.get("deck_dir", "decks"))
    if raw_deck_dir.is_absolute():
        deck_dir = raw_deck_dir
    elif (config_path.parent / raw_deck_dir).exists():
        deck_dir = (config_path.parent / raw_deck_dir).resolve()
    else:
        deck_dir = raw_deck_dir.resolve()
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
                log_name = f"{index:02d}-{label}.log" if label else f"{index:02d}-preboard.log"
                results.append(_batch(engine, label, "preboard", deck_a_path, deck_b_path,
                                      pre, clock, output / log_name))
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
            writer.writeheader()
            writer.writerows(asdict(result) for result in results)
    lines = [f"# {payload['experiment']}", "", "| Matchup | Phase | Games | A wins | B wins | Draws | A win rate | 95% CI | Unparsed |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for result in results:
        lines.append(f"| {result.matchup} | {result.phase} | {result.parsed_games} | {result.wins_a} | {result.wins_b} | {result.draws} | {result.win_rate_a:.1%} | {result.ci95_low:.1%}–{result.ci95_high:.1%} | {result.unparsed} |")
    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output
