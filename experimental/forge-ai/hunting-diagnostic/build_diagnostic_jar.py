#!/usr/bin/env python3
"""Build a telemetry-only Hunting Storm diagnostic JAR.

The base is the recovered-AI patched Forge 2.0.14 JAR. This script overlays only
instrumented copies in a temporary workspace; it never edits forge-patches/.
"""
from __future__ import annotations

import argparse
import difflib
from pathlib import Path
import shutil
import subprocess
import sys

AI_CONTROLLER_BLOB = "2625df42e3f1d601770f869ba96361870c0e1921"
TOKEN_AI_BLOB = "a47941e831ab308d4bd977bfc4c0e5d5119a0eda"


def git_blob(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", "--no-filters", str(path)], text=True).strip()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"{label}: expected exactly one replacement target, found {text.count(old)}")
    return text.replace(old, new, 1)


def instrument_ai_controller(text: str) -> str:
    marker = "    private volatile boolean timeoutReached;\n"
    helper = r'''    private volatile boolean timeoutReached;

    private static String huntingDiagClean(Object value) {
        return String.valueOf(value).replace("|", "/").replace("\n", " ").replace("\r", " ");
    }

    private void huntingDiag(String event, SpellAbility sa, String decision, String extra) {
        if (sa == null || sa.getHostCard() == null || !"Hunting Pack".equals(sa.getHostCard().getName())) {
            return;
        }
        Card card = sa.getHostCard();
        PhaseHandler ph = game.getPhaseHandler();
        CardCollection manaSources = ComputerUtilMana.getAvailableManaSources(player, true);
        int greenCapableSources = 0;
        int filters = 0;
        StringBuilder sourceNames = new StringBuilder();
        for (Card src : manaSources) {
            if (sourceNames.length() > 0) sourceNames.append(',');
            sourceNames.append(src.getName());
            if ("Chromatic Star".equals(src.getName()) || "Chromatic Sphere".equals(src.getName())) filters++;
            boolean green = false;
            for (SpellAbility ma : src.getManaAbilities()) {
                if (ma.getManaPart() == null) continue;
                String produced = ma.getManaPart().mana(ma);
                if (produced != null && (produced.contains("G") || produced.contains("Any"))) green = true;
            }
            if (green) greenCapableSources++;
        }
        boolean manaPayable = false;
        try {
            manaPayable = ComputerUtilMana.canPayManaCost(sa, player, 0, false);
        } catch (RuntimeException ex) {
            // Diagnostic observation must never turn a telemetry query into an AI decision.
        }
        StringBuilder hand = new StringBuilder();
        for (Card c : player.getCardsIn(ZoneType.Hand)) {
            if (c.isLand() || "Hunting Pack".equals(c.getName())) continue;
            if (hand.length() > 0) hand.append(',');
            hand.append(c.getName());
        }
        System.out.println("HUNTING_DIAG"
                + "|event=" + huntingDiagClean(event)
                + "|turn=" + ph.getTurn()
                + "|phase=" + huntingDiagClean(ph.getPhase())
                + "|active_player=" + huntingDiagClean(ph.getPlayerTurn())
                + "|hunting_pack_zone=" + huntingDiagClean(card.getZone())
                + "|visible_to_ai=true"
                + "|mana_pool=" + huntingDiagClean(player.getManaPool())
                + "|mana_sources=" + huntingDiagClean(sourceNames)
                + "|green_capable_sources=" + greenCapableSources
                + "|available_green_mana=engine_tested_via_cost"
                + "|total_producible=" + getAvailableManaEstimate(player, false)
                + "|mana_filters=" + filters
                + "|storm_count=" + game.getView().getStormCount()
                + "|other_setup_candidates=" + huntingDiagClean(hand)
                + "|mana_cost_payable=" + manaPayable
                + "|decision=" + huntingDiagClean(decision)
                + "|extra=" + huntingDiagClean(extra));
    }
'''
    text = replace_once(text, marker, helper, "AiController helper")

    old = """        // this is the \"heaviest\" check, which also sets up targets, defines X, etc.\n        AiPlayDecision canPlay = canPlaySa(sa);\n\n        if (canPlay != AiPlayDecision.WillPlay) {\n            return canPlay;\n        }\n\n        if (!ComputerUtilCost.canPayCost(sa, player, sa.isTrigger())) {\n            // for dependent costs with X, e.g. Repeal, which require a valid target to be specified before a decision can be made\n            // on whether the cost can be paid, this can only be checked late after canPlaySa has been run (or the AI will misplay)\n            return AiPlayDecision.CantAfford;\n        }\n"""
    new = """        // this is the \"heaviest\" check, which also sets up targets, defines X, etc.\n        huntingDiag(\"evaluate\", sa, \"pending\", \"enter_canPlayAndPayForFace\");\n        AiPlayDecision canPlay = canPlaySa(sa);\n        huntingDiag(\"ai_evaluation\", sa, canPlay.name(), \"canPlaySa\");\n\n        if (canPlay != AiPlayDecision.WillPlay) {\n            return canPlay;\n        }\n\n        boolean huntingCostPayable = ComputerUtilCost.canPayCost(sa, player, sa.isTrigger());\n        huntingDiag(\"cost_check\", sa, huntingCostPayable ? \"payable\" : \"not_payable\", \"ComputerUtilCost.canPayCost\");\n        if (!huntingCostPayable) {\n            // for dependent costs with X, e.g. Repeal, which require a valid target to be specified before a decision can be made\n            // on whether the cost can be paid, this can only be checked late after canPlaySa has been run (or the AI will misplay)\n            return AiPlayDecision.CantAfford;\n        }\n"""
    text = replace_once(text, old, new, "AiController canPlay/cost")

    old = """        return AiPlayDecision.WillPlay;\n    }\n\n    public AiPlayDecision canPlaySa(SpellAbility sa) {\n"""
    new = """        huntingDiag(\"final_decision\", sa, \"WillPlay\", \"all canPlayAndPayForFace gates passed\");\n        return AiPlayDecision.WillPlay;\n    }\n\n    public AiPlayDecision canPlaySa(SpellAbility sa) {\n"""
    text = replace_once(text, old, new, "AiController final decision")
    return text


def instrument_token_ai(text: str) -> str:
    old = """        if (source != null && (source.hasKeyword(Keyword.STORM) || \"Hunting Pack\".equals(source.getName()))) {\n            if (ph.isPlayerTurn(ai)) {\n                return ph.getPhase().isMain();\n            } else {\n                return ComputerUtil.aiLifeInDanger(ai, false, 0);\n            }\n        }\n"""
    new = """        if (source != null && (source.hasKeyword(Keyword.STORM) || \"Hunting Pack\".equals(source.getName()))) {\n            boolean huntingPhaseDecision;\n            String huntingPhaseReason;\n            if (ph.isPlayerTurn(ai)) {\n                huntingPhaseDecision = ph.getPhase().isMain();\n                huntingPhaseReason = huntingPhaseDecision ? \"own_main_phase\" : \"not_own_main_phase\";\n            } else {\n                huntingPhaseDecision = ComputerUtil.aiLifeInDanger(ai, false, 0);\n                huntingPhaseReason = huntingPhaseDecision ? \"opponent_turn_life_danger\" : \"opponent_turn_not_life_danger\";\n            }\n            if (\"Hunting Pack\".equals(source.getName())) {\n                System.out.println(\"HUNTING_DIAG|event=token_phase|turn=\" + ph.getTurn()\n                        + \"|phase=\" + ph.getPhase() + \"|active_player=\" + ph.getPlayerTurn()\n                        + \"|decision=\" + huntingPhaseDecision + \"|extra=\" + huntingPhaseReason);\n            }\n            return huntingPhaseDecision;\n        }\n"""
    text = replace_once(text, old, new, "TokenAi phase")

    old = """        if (!((double)MyRandom.getRandom().nextFloat() <= chance)) return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);\n        return new AiAbilityDecision(100, AiPlayDecision.WillPlay);\n"""
    new = """        float huntingTokenRoll = MyRandom.getRandom().nextFloat();\n        boolean huntingTokenWillPlay = (double)huntingTokenRoll <= chance;\n        if (\"Hunting Pack\".equals(sa.getHostCard().getName())) {\n            System.out.println(\"HUNTING_DIAG|event=token_api|turn=\" + game.getPhaseHandler().getTurn()\n                    + \"|phase=\" + game.getPhaseHandler().getPhase()\n                    + \"|active_player=\" + game.getPhaseHandler().getPlayerTurn()\n                    + \"|chance=\" + chance + \"|roll=\" + huntingTokenRoll\n                    + \"|decision=\" + (huntingTokenWillPlay ? \"WillPlay\" : \"CantPlayAi\")\n                    + \"|extra=token_generation_probability\");\n        }\n        if (!huntingTokenWillPlay) return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);\n        return new AiAbilityDecision(100, AiPlayDecision.WillPlay);\n"""
    text = replace_once(text, old, new, "TokenAi probability")
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-jar", required=True, type=Path)
    ap.add_argument("--ai-controller", required=True, type=Path)
    ap.add_argument("--token-ai", required=True, type=Path)
    ap.add_argument("--output-jar", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    args = ap.parse_args()

    if git_blob(args.ai_controller) != AI_CONTROLLER_BLOB:
        raise RuntimeError("Forge 2.0.14 AiController source blob mismatch")
    if git_blob(args.token_ai) != TOKEN_AI_BLOB:
        raise RuntimeError("Recovered TokenAi source blob mismatch")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    work = args.output_dir / "overlay-src"
    if work.exists(): shutil.rmtree(work)
    (work / "forge/ai/ability").mkdir(parents=True)
    (work / "forge/ai").mkdir(parents=True, exist_ok=True)

    ai_original = args.ai_controller.read_text(encoding="utf-8")
    token_original = args.token_ai.read_text(encoding="utf-8")
    ai_instrumented = instrument_ai_controller(ai_original)
    token_instrumented = instrument_token_ai(token_original)

    ai_path = work / "forge/ai/AiController.java"
    token_path = work / "forge/ai/ability/TokenAi.java"
    ai_path.write_text(ai_instrumented, encoding="utf-8")
    token_path.write_text(token_instrumented, encoding="utf-8")

    diff = list(difflib.unified_diff(ai_original.splitlines(), ai_instrumented.splitlines(), fromfile="Forge-2.0.14/AiController.java", tofile="diagnostic/AiController.java", lineterm=""))
    diff += list(difflib.unified_diff(token_original.splitlines(), token_instrumented.splitlines(), fromfile="recovered/TokenAi.java", tofile="diagnostic/TokenAi.java", lineterm=""))
    (args.output_dir / "telemetry-overlay.diff").write_text("\n".join(diff) + "\n", encoding="utf-8")

    shutil.copyfile(args.base_jar, args.output_jar)
    classes = args.output_dir / "classes"
    classes.mkdir(exist_ok=True)
    subprocess.run(["javac", "-cp", str(args.output_jar), "-d", str(classes), str(ai_path), str(token_path)], check=True)
    subprocess.run(["jar", "uf", str(args.output_jar), "-C", str(classes), "forge/ai/AiController.class", "-C", str(classes), "forge/ai/ability/TokenAi.class"], check=True)
    subprocess.run(["sha256sum", str(args.base_jar), str(args.output_jar)], check=True, stdout=(args.output_dir / "jar-sha256.txt").open("w"))
    print(f"Diagnostic JAR: {args.output_jar}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
