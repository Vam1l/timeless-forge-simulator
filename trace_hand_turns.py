import re
from pathlib import Path

def trace_game(log_name, game_idx):
    text = (Path("diagnostic-results") / log_name).read_text()
    blocks = [b for b in text.splitlines()]
    
    # Let's find turns and hand plays in log
    in_game = 0
    curr_game = 0
    for line in blocks:
        if "has kept a hand of" in line:
            if in_game == 0 or any("Game Result:" in l for l in blocks[:blocks.index(line)]):
                curr_game += 1
        if curr_game == game_idx:
            if any(k in line for k in ["Turn ", "Land:", "Spell:", "Ability:", "Discard:", "exiled", "Mulligan:"]):
                print(line)

print("=== TRACING 02-07-esper-control-vs-09-hunting-storm.log Game 2 ===")
trace_game("02-07-esper-control-vs-09-hunting-storm.log", 2)
