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

# Stats counters
star_cast = 0
star_act = 0
sph_cast = 0
sph_act = 0
tw_cast = 0
tw_act = 0

hp_cast = 0
hp_disc = 0
hp_reasons = {
    "never drawn": 0,
    "exiled by Glimpse the Impossible": 0,
    "discarded by opponent": 0,
    "stranded on colors": 0,
    "stranded on total mana": 0,
    "AI declined a legal cast": 0,
    "died before setup": 0,
    "other": 0
}

strands_hand_cast = 0
strands_flashback_cast = 0
strands_disc = 0

fof_cast = 0
sv_cast = 0

hs_games_analyzed = 0

print("=== HUNTING STORM 12 GAMES DETAILED ANALYSIS ===")
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
        hs_games_analyzed += 1
        lines = block.splitlines()
        hs_player = "Ai(1)-Hunting Storm" if "09-hunting-storm-vs" in log_name else "Ai(2)-Hunting Storm"
        opp_player = "Ai(2)-Esper Control" if hs_player == "Ai(1)-Hunting Storm" else ("Ai(1)-Esper Control" if "07-esper" in log_name else ("Ai(2)-Jund Wildfire" if hs_player == "Ai(1)-Hunting Storm" else "Ai(1)-Jund Wildfire"))
        
        # Check casts / activations for artifacts & wall
        sc_c = len([l for l in lines if f"{hs_player} cast Chromatic Star" in l or f"{hs_player} plays Chromatic Star" in l])
        sc_a = len([l for l in lines if f"Activator: {hs_player}" in l and "Chromatic Star" in l])
        sp_c = len([l for l in lines if f"{hs_player} cast Chromatic Sphere" in l or f"{hs_player} plays Chromatic Sphere" in l])
        sp_a = len([l for l in lines if f"Activator: {hs_player}" in l and "Chromatic Sphere" in l])
        tw_c = len([l for l in lines if f"{hs_player} cast Tinder Wall" in l or f"{hs_player} plays Tinder Wall" in l])
        tw_a = len([l for l in lines if f"Activator: {hs_player}" in l and "Tinder Wall" in l])
        
        star_cast += sc_c
        star_act += sc_a
        sph_cast += sp_c
        sph_act += sp_a
        tw_cast += tw_c
        tw_act += tw_a

        # Hunting Pack casts / discards
        casts_hp = [l for l in lines if f"{hs_player} cast Hunting Pack" in l]
        discs_hp = [l for l in lines if f"discards Hunting Pack" in l] # could be self cleanup or opponent
        
        hp_cast += len(casts_hp)
        hp_disc += len(discs_hp)
        
        # Determine failure reason if not cast
        # Check if HP was in hand, drawn, exiled, or died before setup
        hp_drawn = any("Hunting Pack" in l for l in lines)
        hp_exiled_glimpse = any("Glimpse the Impossible" in l and "Hunting Pack" in l for l in lines)
        hp_discarded_cleanup = any(f"{hs_player} discards Hunting Pack" in l for l in lines)
        hp_discarded_opp = any(f"{opp_player}" in l and "discards Hunting Pack" in l for l in lines) # e.g. duress/blightning if any

        # Turn count
        turns = [l for l in lines if "Turn: Turn" in l]
        last_turn = turns[-1] if turns else "Turn 0"
        
        reason = "N/A (Cast)"
        if len(casts_hp) == 0:
            if not hp_drawn and not hp_exiled_glimpse:
                reason = "never drawn"
            elif hp_exiled_glimpse:
                reason = "exiled by Glimpse the Impossible"
            elif hp_discarded_opp:
                reason = "discarded by opponent"
            elif hp_discarded_cleanup:
                reason = "discarded by cleanup (stranded on mana/colors)"
            else:
                # Check if game ended early (died before setup)
                # Parse turn number from last turn
                m = re.search(r"Turn (\d+)", last_turn)
                t_num = int(m.group(1)) if m else 0
                if t_num <= 6:
                    reason = "died before setup"
                else:
                    reason = "stranded on total mana / colors"
            hp_reasons[reason if reason in hp_reasons else "other"] += 1

        print(f"{log_name} Game {g_num}: HP cast={len(casts_hp)}, Reason if 0: {reason} | C.Star cast/act=({sc_c}/{sc_a}), C.Sph=({sp_c}/{sp_a}), TW=({tw_c}/{tw_a})")

print("\n=== ESPER / PRISMATIC STRANDS 18 GAMES DETAILED ANALYSIS ===")
esper_matchups = [
    "01-09-hunting-storm-vs-07-esper-control.log",
    "02-07-esper-control-vs-09-hunting-storm.log",
    "05-07-esper-control-vs-01-white-weenie.log",
    "06-01-white-weenie-vs-07-esper-control.log",
    "07-07-esper-control-vs-03-green-stompy.log",
    "08-03-green-stompy-vs-07-esper-control.log"
]

for log_name in esper_matchups:
    log_path = Path("diagnostic-results") / log_name
    blocks = get_game_blocks(log_path)
    for g_num, block in enumerate(blocks, 1):
        lines = block.splitlines()
        esper_player = "Ai(1)-Esper Control" if log_name.startswith("02") or log_name.startswith("05") or log_name.startswith("07") else "Ai(2)-Esper Control"
        
        strands_drawn = any("Prismatic Strands" in l for l in lines)
        strands_discs = [l for l in lines if f"{esper_player} discards Prismatic Strands" in l]
        strands_casts = [l for l in lines if f"{esper_player} cast Prismatic Strands" in l]
        strands_flashbacks = [l for l in lines if f"{esper_player} cast Prismatic Strands" in l and "from graveyard" in l]
        
        strands_disc += len(strands_discs)
        strands_hand_cast += (len(strands_casts) - len(strands_flashbacks))
        strands_flashback_cast += len(strands_flashbacks)

        fof = [l for l in lines if f"{esper_player} cast Fact or Fiction" in l]
        sv = [l for l in lines if f"{esper_player} cast Supreme Verdict" in l]
        fof_cast += len(fof)
        sv_cast += len(sv)

        if strands_drawn or len(strands_discs) > 0 or len(strands_casts) > 0:
            print(f"{log_name} Game {g_num}: Strands drawn={strands_drawn}, disc={len(strands_discs)}, hand_cast={len(strands_casts)-len(strands_flashbacks)}, fb_cast={len(strands_flashbacks)}")

print("\nSummary Counters:")
print(f"Chromatic Star cast: {star_cast}, activated: {star_act}")
print(f"Chromatic Sphere cast: {sph_cast}, activated: {sph_act}")
print(f"Tinder Wall cast: {tw_cast}, used mana: {tw_act}")
print(f"Hunting Pack cast: {hp_cast}, discarded: {hp_disc}")
print(f"Hunting Pack failure reasons: {hp_reasons}")
print(f"Prismatic Strands hand cast: {strands_hand_cast}, flashback cast: {strands_flashback_cast}, discarded: {strands_disc}")
print(f"Fact or Fiction cast: {fof_cast}, Supreme Verdict cast: {sv_cast}")
