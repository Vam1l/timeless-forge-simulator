#!/usr/bin/env python3
"""
Generate card-action and behavioral summary report from verbose diagnostic log files.
Usage: python scripts/generate_behavioral_summary.py <results_dir> <output_file>
"""

import json
import re
import sys
from pathlib import Path


def parse_game_blocks(log_path: Path):
    text = log_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    game_blocks = []
    curr = []
    for line in lines:
        curr.append(line)
        if "Game Result:" in line:
            game_blocks.append("\n".join(curr))
            curr = []
    if curr and any("Turn:" in l for l in curr):
        game_blocks.append("\n".join(curr))
    return game_blocks


def analyze_behavior(results_dir: Path, output_file: Path):
    log_files = sorted(results_dir.glob("*.log"))
    if not log_files:
        print(f"No log files found in {results_dir}")
        return 1

    lines_out = [
        "==========================================================",
        "PEASANT+ FORGE AI TARGETED BEHAVIORAL SUMMARY",
        "==========================================================",
        f"Total Log Files Analyzed: {len(log_files)}",
        "",
    ]

    total_games = 0

    # HS Stats
    star_cast = 0
    star_act = 0
    star_drawn = 0
    sph_cast = 0
    sph_act = 0
    sph_drawn = 0
    tw_cast = 0
    tw_act = 0
    tw_drawn = 0

    hp_orig_cast = 0
    hp_storm_copies = 0
    hp_beast_tokens = 0
    hp_disc = 0
    hp_drawn = 0
    hp_reasons = {
        "never drawn": 0,
        "exiled by Glimpse the Impossible": 0,
        "discarded by opponent": 0,
        "stranded on colors": 0,
        "stranded on total mana": 0,
        "AI declined a legal cast": 0,
        "died before setup": 0,
        "other": 0,
    }

    # Esper Stats
    strands_hand_cast = 0
    strands_flashback_cast = 0
    strands_disc = 0
    strands_drawn = 0

    fof_cast = 0
    sv_cast = 0

    lines_out.append("--- GAME-BY-GAME CARD ACTION DETAILED BREAKDOWN ---")

    for log_path in log_files:
        blocks = parse_game_blocks(log_path)
        log_name = log_path.name
        is_hs_matchup = "hunting-storm" in log_name
        is_esper_matchup = "esper-control" in log_name

        for g_idx, block in enumerate(blocks, 1):
            total_games += 1
            lines = block.splitlines()

            lines_out.append(f"\nMatchup: {log_name} | Game {g_idx}")

            if is_hs_matchup:
                m_hs = re.search(r"(Ai\(\d\)-Hunting Storm)", block)
                hs_player = m_hs.group(1) if m_hs else "Ai(1)-Hunting Storm"
                opp_player = "Ai(2)" if hs_player.startswith("Ai(1)") else "Ai(1)"

                # Star
                c_star_d = any("Chromatic Star" in l for l in lines)
                c_star_c = len([
                    l for l in lines if f"{hs_player} cast Chromatic Star" in l or f"{hs_player} plays Chromatic Star" in l
                ])
                c_star_a = len([
                    l for l in lines if f"Activator: {hs_player}" in l and "Chromatic Star" in l
                ])

                # Sphere
                c_sph_d = any("Chromatic Sphere" in l for l in lines)
                c_sph_c = len([
                    l for l in lines if f"{hs_player} cast Chromatic Sphere" in l or f"{hs_player} plays Chromatic Sphere" in l
                ])
                c_sph_a = len([
                    l for l in lines if f"Activator: {hs_player}" in l and "Chromatic Sphere" in l
                ])

                # Tinder Wall
                tw_d = any("Tinder Wall" in l for l in lines)
                tw_c = len([
                    l for l in lines if f"{hs_player} cast Tinder Wall" in l or f"{hs_player} plays Tinder Wall" in l
                ])
                tw_a = len([
                    l for l in lines if f"Activator: {hs_player}" in l and "Tinder Wall" in l
                ])

                if c_star_d: star_drawn += 1
                star_cast += c_star_c
                star_act += c_star_a

                if c_sph_d: sph_drawn += 1
                sph_cast += c_sph_c
                sph_act += c_sph_a

                if tw_d: tw_drawn += 1
                tw_cast += tw_c
                tw_act += tw_a

                # Hunting Pack
                hp_d = any("Hunting Pack" in l for l in lines)
                hp_orig = [l for l in lines if re.search(r"cast Hunting Pack|plays Hunting Pack", l, re.I) and not re.search(r"copy|storm", l, re.I)]
                hp_copies = [l for l in lines if "Hunting Pack" in l and re.search(r"copy of Hunting Pack|puts a copy|Storm copy|Storm -", l, re.I)]
                hp_tokens = [l for l in lines if re.search(r"3/3 green Beast|Beast creature token|creates a Beast|Beast token", l, re.I)]
                hp_discs = [l for l in lines if "discards Hunting Pack" in l]
                hp_glimpse = any("Glimpse the Impossible" in l and "Hunting Pack" in l for l in lines)

                if hp_d or hp_glimpse: hp_drawn += 1
                hp_orig_cast += len(hp_orig)
                hp_storm_copies += len(hp_copies)
                hp_beast_tokens += len(hp_tokens)
                hp_disc += len(hp_discs)

                # Classify reason
                if hp_orig:
                    reason = "N/A (Cast)"
                else:
                    if not hp_d and not hp_glimpse:
                        reason = "never drawn"
                    elif hp_glimpse:
                        reason = "exiled by Glimpse the Impossible"
                    elif any(f"{opp_player}" in l and "discards Hunting Pack" in l for l in lines):
                        reason = "discarded by opponent"
                    elif any(f"{hs_player} discards Hunting Pack" in l for l in lines):
                        reason = "stranded on colors / total mana (discarded during cleanup)"
                    else:
                        turns = [l for l in lines if "Turn: Turn" in l]
                        last_t = turns[-1] if turns else "Turn 0"
                        m = re.search(r"Turn (\d+)", last_t)
                        t_num = int(m.group(1)) if m else 0
                        if t_num <= 6:
                            reason = "died before setup"
                        else:
                            reason = "stranded on total mana / colors"

                    if reason in hp_reasons:
                        hp_reasons[reason] += 1
                    else:
                        hp_reasons["other"] += 1

                lines_out.append(
                    f"  HS Player Actions: Chromatic Star (drawn={c_star_d}, cast={c_star_c}, act={c_star_a}) | "
                    f"Chromatic Sphere (drawn={c_sph_d}, cast={c_sph_c}, act={c_sph_a}) | "
                    f"Tinder Wall (drawn={tw_d}, cast={tw_c}, act={tw_a}) | "
                    f"Hunting Pack (orig_cast={len(hp_orig)}, storm_copies={len(hp_copies)}, beast_tokens={len(hp_tokens)}, failure_reason='{reason}')"
                )

            if is_esper_matchup:
                m_esper = re.search(r"(Ai\(\d\)-Esper Control)", block)
                esper_player = m_esper.group(1) if m_esper else "Ai(1)-Esper Control"

                str_d = any("Prismatic Strands" in l for l in lines)
                str_casts = [l for l in lines if f"{esper_player} cast Prismatic Strands" in l]
                str_fb = [l for l in lines if f"{esper_player} cast Prismatic Strands" in l and "from graveyard" in l]
                str_discs = [l for l in lines if f"{esper_player} discards Prismatic Strands" in l]

                if str_d: strands_drawn += 1
                strands_hand_cast += (len(str_casts) - len(str_fb))
                strands_flashback_cast += len(str_fb)
                strands_disc += len(str_discs)

                fof = len([l for l in lines if f"{esper_player} cast Fact or Fiction" in l])
                sv = len([l for l in lines if f"{esper_player} cast Supreme Verdict" in l])
                fof_cast += fof
                sv_cast += sv

                lines_out.append(
                    f"  Esper Player Actions: Prismatic Strands (drawn={str_d}, hand_cast={len(str_casts)-len(str_fb)}, fb_cast={len(str_fb)}, disc={len(str_discs)}) | "
                    f"Fact or Fiction (cast={fof}) | Supreme Verdict (cast={sv})"
                )

    lines_out.append("\n==========================================================")
    lines_out.append("AGGREGATE BEHAVIORAL METRICS")
    lines_out.append("==========================================================")
    lines_out.append(f"Total Games Parsed: {total_games}")
    lines_out.append("")
    lines_out.append("HUNTING STORM METRICS:")
    lines_out.append(f"  - Chromatic Star: drawn={star_drawn}, cast={star_cast}, activated={star_act}")
    lines_out.append(f"  - Chromatic Sphere: drawn={sph_drawn}, cast={sph_cast}, activated={sph_act}")
    lines_out.append(f"  - Tinder Wall: drawn={tw_drawn}, cast={tw_cast}, used_mana={tw_act}")
    lines_out.append(f"  - Hunting Pack: drawn={hp_drawn}, original_cast={hp_orig_cast}, storm_copies={hp_storm_copies}, beast_tokens={hp_beast_tokens}, discarded={hp_disc}")
    lines_out.append("  - Hunting Pack Failure Reason Breakdown:")
    for r_name, r_cnt in hp_reasons.items():
        lines_out.append(f"      * {r_name}: {r_cnt}")
    lines_out.append("")
    lines_out.append("ESPER CONTROL METRICS:")
    lines_out.append(f"  - Prismatic Strands: drawn={strands_drawn}, hand_cast={strands_hand_cast}, flashback_cast={strands_flashback_cast}, discarded={strands_disc}")
    lines_out.append(f"  - Fact or Fiction Cast Count: {fof_cast}")
    lines_out.append(f"  - Supreme Verdict Cast Count: {sv_cast}")
    lines_out.append("==========================================================")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(lines_out) + "\n", encoding="utf-8")
    print(f"Wrote behavioral summary to {output_file}")
    return 0


def main():
    if len(sys.argv) < 3:
        print("Usage: generate_behavioral_summary.py <results_dir> <output_file>")
        return 1
    results_dir = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    return analyze_behavior(results_dir, output_file)


if __name__ == "__main__":
    sys.exit(main())
