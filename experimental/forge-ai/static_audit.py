#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
PATCH = ROOT / "forge-patches"

required = {
    "forge/ai/ComputerUtilMana.java": [
        "for (Object key : manaAbilityMap.keySet())",
        "if (!(key instanceof Number)) continue;",
        "((Number) key).intValue()",
        "ArrayListMultimap<Integer, SpellAbility> manaMap",
        "manaMap.put((int) ManaAtom.fromName",
        "manaMap.put((int) color, m)",
    ],
    "forge/ai/ComputerUtilCard.java": [
        "Urza's Mine", "Urza's Tower", "Urza's Power Plant", "tronCompleteField", "Hunting Pack", "Prismatic Strands"
    ],
    "forge/ai/ability/ManaAi.java": ["Hunting Pack", "ManaRitual"],
    "forge/ai/ability/PermanentAi.java": ["Chromatic Star", "Chromatic Sphere", "Tinder Wall"],
    "forge/ai/ability/TokenAi.java": ["Hunting Pack", "Keyword.STORM"],
    "forge/ai/ability/DestroyAllAi.java": ["Supreme Verdict", "lifeInDanger"],
}

errors = []
for rel, needles in required.items():
    path = PATCH / rel
    if not path.is_file():
        errors.append(f"missing recovered source: {rel}")
        continue
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            errors.append(f"{rel}: missing expected historical marker {needle!r}")

mana = (PATCH / "forge/ai/ComputerUtilMana.java").read_text(encoding="utf-8")
for needle in (
    "for (Integer colorint : manaAbilityMap.keySet())",
    "ArrayListMultimap manaMap = ArrayListMultimap.create()",
):
    if needle in mana:
        errors.append(f"ComputerUtilMana.java retains unsafe historical pattern: {needle}")

proc = subprocess.run(
    ["git", "diff", "--exit-code", "origin/main...HEAD", "--", "battlebox/decks"],
    cwd=REPO, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
)
if proc.returncode:
    errors.append("battle-box deck files differ from origin/main:\n" + proc.stdout)

for path in PATCH.rglob("*.java"):
    text = path.read_text(encoding="utf-8")
    if "TEMPORARY_PLACEHOLDER" in text or text.strip() == "PLACEHOLDER":
        errors.append(f"placeholder source remains: {path}")

if errors:
    print("STATIC AUDIT FAILED")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("STATIC AUDIT PASSED")
print("- final PR #2 source markers present")
print("- Byte/Integer key normalization present")
print("- Tron land-selection markers present")
print("- Hunting Storm ritual/setup/payoff markers present")
print("- Esper Prismatic Strands/Supreme Verdict markers present")
print("- battlebox/decks unchanged from origin/main")
