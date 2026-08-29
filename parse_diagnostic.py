import re
from pathlib import Path

logs = sorted(Path("diagnostic-results").glob("*.log"))

def parse_game_blocks(log_path):
    text = log_path.read_text()
    # Split text into games based on "Game Result:"
    lines = text.splitlines()
    game_blocks = []
    curr = []
    for line in lines:
        curr.append(line)
        if "Game Result:" in line:
            game_blocks.append("\n".join(curr))
            curr = []
    return game_blocks

total_games = 0
for log in logs:
    blocks = parse_game_blocks(log)
    total_games += len(blocks)
    print(f"Log: {log.name} -> {len(blocks)} games")

print(f"Total games parsed across all logs: {total_games}")
