import re
from pathlib import Path

def get_game_blocks(log_path):
    text = log_path.read_text()
    lines = text.splitlines()
    game_blocks = []
    curr = []
    for line in lines:
        curr.append(line)
        if "Game Result:" in line:
            game_blocks.append("\n".join(curr))
            curr = []
    return game_blocks

esper_matchups = [
    "01-09-hunting-storm-vs-07-esper-control.log",
    "02-07-esper-control-vs-09-hunting-storm.log",
    "05-07-esper-control-vs-01-white-weenie.log",
    "06-01-white-weenie-vs-07-esper-control.log",
    "07-07-esper-control-vs-03-green-stompy.log",
    "08-03-green-stompy-vs-07-esper-control.log"
]

game_counter = 0
for log_name in esper_matchups:
    log_path = Path("diagnostic-results") / log_name
    blocks = get_game_blocks(log_path)
    for g_num, block in enumerate(blocks, 1):
        game_counter += 1
        lines = block.splitlines()
        esper_p = "Ai(1)-Esper Control" if log_name.startswith("02") or log_name.startswith("05") or log_name.startswith("07") else "Ai(2)-Esper Control"
        opp_p = "Ai(2)" if esper_p == "Ai(1)-Esper Control" else "Ai(1)"

        print(f"\n==========================================")
        print(f"ESPER GAME {game_counter}: {log_name} Game {g_num} ({esper_p})")

        strands_in_log = [l for l in lines if "Prismatic Strands" in l]
        strands_drawn = len(strands_in_log) > 0
        strands_discs = [l for l in lines if f"{esper_p} discards Prismatic Strands" in l]
        strands_casts = [l for l in lines if f"{esper_p} cast Prismatic Strands" in l]

        combat_windows = [l for l in lines if "Declare Attackers Step" in l]

        print(f"  Prismatic Strands in log lines: {len(strands_in_log)}")
        for l in strands_in_log: print("    ", l)
        print(f"  Combat Attackers steps in game: {len(combat_windows)}")

