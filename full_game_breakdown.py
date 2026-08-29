import re
from pathlib import Path

logs = sorted(Path("diagnostic-results").glob("*.log"))

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

print("=== HUNTING STORM GAME-BY-GAME ANALYSIS ===")

hs_matchups = [
    "01-09-hunting-storm-vs-07-esper-control.log",
    "02-07-esper-control-vs-09-hunting-storm.log",
    "03-09-hunting-storm-vs-06-jund-wildfire.log",
    "04-06-jund-wildfire-vs-09-hunting-storm.log"
]

for log_name in hs_matchups:
    log_path = Path("diagnostic-results") / log_name
    blocks = get_game_blocks(log_path)
    for g_num, block in enumerate(blocks, 1):
        print(f"\n--- {log_name} Game {g_num} ---")
        lines = block.splitlines()
        
        # Check initial hand & draws / discards / exiles for HS player
        hs_player = "Ai(1)-Hunting Storm" if "09-hunting-storm-vs" in log_name else "Ai(2)-Hunting Storm"
        
        c_star_drawn = any("Chromatic Star" in l for l in lines)
        c_star_cast = any(re.search(rf"{re.escape(hs_player)}.*cast.*Chromatic Star", l, re.I) for l in lines)
        c_star_act = any(re.search(rf"{re.escape(hs_player)}.*activate.*Chromatic Star", l, re.I) or re.search(r"Chromatic Star.*Ability", l, re.I) for l in lines)
        
        c_sph_drawn = any("Chromatic Sphere" in l for l in lines)
        c_sph_cast = any(re.search(rf"{re.escape(hs_player)}.*cast.*Chromatic Sphere", l, re.I) for l in lines)
        c_sph_act = any(re.search(rf"{re.escape(hs_player)}.*activate.*Chromatic Sphere", l, re.I) or re.search(r"Chromatic Sphere.*Ability", l, re.I) for l in lines)

        tw_drawn = any("Tinder Wall" in l for l in lines)
        tw_cast = any(re.search(rf"{re.escape(hs_player)}.*cast.*Tinder Wall", l, re.I) for l in lines)
        tw_mana = any(re.search(rf"{re.escape(hs_player)}.*activate.*Tinder Wall", l, re.I) or re.search(r"Tinder Wall.*Ability", l, re.I) for l in lines)

        hp_drawn = any("Hunting Pack" in l for l in lines)
        hp_cast = [l for l in lines if f"{hs_player} cast Hunting Pack" in l]
        hp_disc = [l for l in lines if f"{hs_player} discards Hunting Pack" in l]
        hp_exile = [l for l in lines if "Glimpse the Impossible" in l and "Hunting Pack" in l]

        print(f"  HS Player: {hs_player}")
        print(f"  Chromatic Star: drawn={c_star_drawn}, cast={c_star_cast}, activated={c_star_act}")
        print(f"  Chromatic Sphere: drawn={c_sph_drawn}, cast={c_sph_cast}, activated={c_sph_act}")
        print(f"  Tinder Wall: drawn={tw_drawn}, cast={tw_cast}, used_mana={tw_mana}")
        print(f"  Hunting Pack: drawn={hp_drawn}, cast_count={len(hp_cast)}, disc_count={len(hp_disc)}, exiled={len(hp_exile)}")

        # Print all lines mentioning these 4 cards in this game block
        for l in lines:
            if any(k in l for k in ["Chromatic Star", "Chromatic Sphere", "Tinder Wall", "Hunting Pack"]):
                print(f"    LOG: {l}")

