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

hs_matchups = [
    ("01-09-hunting-storm-vs-07-esper-control.log", "Ai(1)-Hunting Storm", "Ai(2)-Esper Control"),
    ("02-07-esper-control-vs-09-hunting-storm.log", "Ai(2)-Hunting Storm", "Ai(1)-Esper Control"),
    ("03-09-hunting-storm-vs-06-jund-wildfire.log", "Ai(1)-Hunting Storm", "Ai(2)-Jund Wildfire"),
    ("04-06-jund-wildfire-vs-09-hunting-storm.log", "Ai(2)-Hunting Storm", "Ai(1)-Jund Wildfire")
]

game_counter = 0
for log_name, hs_p, opp_p in hs_matchups:
    log_path = Path("diagnostic-results") / log_name
    blocks = get_game_blocks(log_path)
    for g_num, block in enumerate(blocks, 1):
        game_counter += 1
        lines = block.splitlines()
        
        print(f"\n==========================================")
        print(f"GAME {game_counter}: {log_name} Game {g_num} ({hs_p} vs {opp_p})")
        
        # Check cards drawn/exiled/discarded
        c_star_in_game = [l for l in lines if "Chromatic Star" in l]
        c_sph_in_game = [l for l in lines if "Chromatic Sphere" in l]
        tw_in_game = [l for l in lines if "Tinder Wall" in l]
        hp_in_game = [l for l in lines if "Hunting Pack" in l]
        
        # Check cast
        hp_casts = [l for l in lines if f"{hs_p} cast Hunting Pack" in l]
        
        # Check exiled by glimpse
        glimpse_exiles = [l for l in lines if "Glimpse the Impossible" in l]
        
        print(f"  Chromatic Star lines: {len(c_star_in_game)}")
        for l in c_star_in_game: print("    ", l)
        print(f"  Chromatic Sphere lines: {len(c_sph_in_game)}")
        for l in c_sph_in_game: print("    ", l)
        print(f"  Tinder Wall lines: {len(tw_in_game)}")
        for l in tw_in_game: print("    ", l)
        print(f"  Hunting Pack lines: {len(hp_in_game)}")
        for l in hp_in_game: print("    ", l)
        
        # Determine failure reason if not cast
        if hp_casts:
            print("  Result: Hunting Pack WAS CAST!")
        else:
            # Let's inspect why
            has_hp = len(hp_in_game) > 0
            if not has_hp:
                print("  Result: Hunting Pack NEVER DRAWN")
            else:
                # Check if exiled
                exiled = any("Hunting Pack" in l for l in glimpse_exiles)
                if exiled:
                    print("  Result: Hunting Pack EXILED BY GLIMPSE THE IMPOSSIBLE")
                elif any("discards Hunting Pack" in l for l in lines):
                    print("  Result: Hunting Pack DISCARDED (during cleanup due to hand size / mana bottleneck)")
                else:
                    print("  Result: Hunting Pack STRANDED IN HAND (mana/color/death)")

