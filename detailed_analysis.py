import re
from pathlib import Path

logs = sorted(Path("diagnostic-results").glob("*.log"))

def parse_game_blocks(log_path):
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

cards_to_check = [
    "Chromatic Star",
    "Chromatic Sphere",
    "Tinder Wall",
    "Hunting Pack",
    "Prismatic Strands",
    "Fact or Fiction",
    "Supreme Verdict",
    "Energy Refractor",
    "Crop Rotation"
]

for log in logs:
    blocks = parse_game_blocks(log)
    for g_idx, block in enumerate(blocks, 1):
        print(f"\n==================== {log.name} - Game {g_idx} ====================")
        # Check winner
        for line in block.splitlines():
            if "Game Result:" in line:
                print(f"RESULT: {line}")
            if "has kept a hand" in line:
                print(f"HAND: {line}")
        
        # Check mentions of cards
        for card in cards_to_check:
            matches = [l for l in block.splitlines() if card.lower() in l.lower()]
            if matches:
                print(f"  --- {card} ({len(matches)} occurrences) ---")
                for m in matches[:10]:
                    print(f"      {m}")

