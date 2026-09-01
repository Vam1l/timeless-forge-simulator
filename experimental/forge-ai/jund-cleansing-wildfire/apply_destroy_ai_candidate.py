#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

ANCHOR = '''            // AI doesn't destroy own cards if it isn't defined in AI logic\n            list = CardLists.getTargetableCards(ai.getOpponents().getCardsIn(ZoneType.Battlefield), sa);\n'''
REPLACEMENT = '''            // Cleansing Wildfire is unusual removal: an indestructible land survives the\n            // Destroy event while its controller still gets the optional basic search, and\n            // the caster still draws. Stock DestroyAi only constructs opponent targets and\n            // removes indestructible permanents, so it cannot discover that line.\n            if (isExactCleansingWildfireStructure(sa)) {\n                Card wildfireChoice = chooseCleansingWildfireCandidate(ai, sa);\n                if (wildfireChoice != null) {\n                    sa.getTargets().add(wildfireChoice);\n                    return new AiAbilityDecision(100, AiPlayDecision.WillPlay);\n                }\n            }\n\n            // Stock Forge fallback: AI doesn't destroy own cards if it isn't defined in AI logic.\n            list = CardLists.getTargetableCards(ai.getOpponents().getCardsIn(ZoneType.Battlefield), sa);\n'''

METHOD_ANCHOR = '''    private boolean shouldApplyLandRemovalLogic(SpellAbility sa, String logic) {\n'''
METHODS = r'''    private boolean isExactCleansingWildfireStructure(final SpellAbility sa) {
        if (sa == null || sa.getApi() != ApiType.Destroy || !sa.usesTargeting()) {
            return false;
        }
        if (!"Cleansing Wildfire".equals(sa.getHostCard().getName())) {
            return false;
        }
        if (!"Land".equals(sa.getParamOrDefault("ValidTgts", ""))) {
            return false;
        }
        final SpellAbility search = sa.getSubAbility();
        if (search == null || search.getApi() != ApiType.ChangeZone) {
            return false;
        }
        if (!"Library".equals(search.getParamOrDefault("Origin", ""))
                || !"Battlefield".equals(search.getParamOrDefault("Destination", ""))
                || !search.getParamOrDefault("ChangeType", "").contains("Land.Basic")
                || !"TargetedController".equals(search.getParamOrDefault("DefinedPlayer", ""))) {
            return false;
        }
        final SpellAbility draw = search.getSubAbility();
        return draw != null && draw.getApi() == ApiType.Draw;
    }

    private Card chooseCleansingWildfireCandidate(final Player ai, final SpellAbility sa) {
        final CardCollection legal = CardLists.getTargetableCards(
                ai.getGame().getCardsIn(ZoneType.Battlefield), sa);
        if (legal.isEmpty()) {
            logCleansingWildfireTelemetry(legal, new CardCollection(), new CardCollection(), null, "fallback-empty");
            return null;
        }

        CardCollection ownIndestructible = CardLists.filterControlledBy(legal, ai);
        ownIndestructible = CardLists.filter(ownIndestructible,
                c -> c.isLand() && c.hasKeyword(Keyword.INDESTRUCTIBLE));

        CardCollection opponentLegal = CardLists.filterControlledBy(legal, ai.getOpponents());
        CardCollection urza = CardLists.filter(opponentLegal, c ->
                "Urza's Mine".equals(c.getName())
                || "Urza's Power Plant".equals(c.getName())
                || "Urza's Tower".equals(c.getName()));

        boolean mine = false;
        boolean plant = false;
        boolean tower = false;
        for (Card c : urza) {
            mine |= "Urza's Mine".equals(c.getName());
            plant |= "Urza's Power Plant".equals(c.getName());
            tower |= "Urza's Tower".equals(c.getName());
        }
        final int distinctUrza = (mine ? 1 : 0) + (plant ? 1 : 0) + (tower ? 1 : 0);
        final CleansingWildfireTargetingPolicy.Decision decision =
                CleansingWildfireTargetingPolicy.decide(true, distinctUrza, !ownIndestructible.isEmpty());

        if (decision == CleansingWildfireTargetingPolicy.Decision.DISRUPT_VISIBLE_TRON) {
            final Card choice = ComputerUtilCard.getBestLandToRemoveAI(ai, urza, sa);
            logCleansingWildfireTelemetry(legal, ownIndestructible, urza, choice, "visible-tron");
            return choice;
        }
        if (decision == CleansingWildfireTargetingPolicy.Decision.SELF_INDESTRUCTIBLE) {
            final Card choice = ComputerUtilCard.getWorstLand(ownIndestructible);
            logCleansingWildfireTelemetry(legal, ownIndestructible, urza, choice, "self-indestructible");
            return choice;
        }

        logCleansingWildfireTelemetry(legal, ownIndestructible, urza, null, "stock-fallback");
        return null;
    }

    private void logCleansingWildfireTelemetry(final CardCollection legal,
            final CardCollection ownIndestructible, final CardCollection urza,
            final Card choice, final String reason) {
        System.out.println("CWAI candidates=" + cleansingWildfireNames(legal)
                + " ownIndestructible=" + cleansingWildfireNames(ownIndestructible)
                + " opposingHighValue=" + cleansingWildfireNames(urza)
                + " selected=" + (choice == null ? "<stock>" : choice.toString())
                + " reason=" + reason);
    }

    private String cleansingWildfireNames(final CardCollection cards) {
        final StringBuilder out = new StringBuilder("[");
        boolean first = true;
        for (Card c : cards) {
            if (!first) {
                out.append(", ");
            }
            first = false;
            out.append(c.toString());
        }
        return out.append(']').toString();
    }

'''


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    text = args.input.read_text()
    if text.count(ANCHOR) != 1:
        raise SystemExit(f'expected exactly one target-construction anchor, found {text.count(ANCHOR)}')
    if text.count(METHOD_ANCHOR) != 1:
        raise SystemExit(f'expected exactly one method anchor, found {text.count(METHOD_ANCHOR)}')
    text = text.replace(ANCHOR, REPLACEMENT, 1)
    text = text.replace(METHOD_ANCHOR, METHODS + METHOD_ANCHOR, 1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text)


if __name__ == '__main__':
    main()
