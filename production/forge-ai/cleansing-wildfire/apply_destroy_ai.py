#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

ANCHOR = '''            // AI doesn't destroy own cards if it isn't defined in AI logic
            list = CardLists.getTargetableCards(ai.getOpponents().getCardsIn(ZoneType.Battlefield), sa);
'''
REPLACEMENT = '''            // Cleansing Wildfire is unusual removal: an indestructible land survives the
            // Destroy event while its controller still gets the optional basic search, and
            // the caster still draws. Stock DestroyAi only constructs opponent targets and
            // removes indestructible permanents, so it cannot discover that line.
            if (isExactCleansingWildfireStructure(sa)) {
                Card wildfireChoice = chooseCleansingWildfireCandidate(ai, sa);
                if (wildfireChoice != null) {
                    sa.getTargets().add(wildfireChoice);
                    return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
                }
            }

            // Stock Forge fallback: AI doesn't destroy own cards if it isn't defined in AI logic.
            list = CardLists.getTargetableCards(ai.getOpponents().getCardsIn(ZoneType.Battlefield), sa);
'''
METHOD_ANCHOR = '''    private boolean shouldApplyLandRemovalLogic(SpellAbility sa, String logic) {
'''
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
            return choice;
        }
        if (decision == CleansingWildfireTargetingPolicy.Decision.SELF_INDESTRUCTIBLE) {
            final Card choice = ComputerUtilCard.getWorstLand(ownIndestructible);
            return choice;
        }

        return null;
    }

'''


def transform(text: str) -> str:
    if text.count(ANCHOR) != 1:
        raise ValueError(f'expected exactly one target-construction anchor, found {text.count(ANCHOR)}')
    if text.count(METHOD_ANCHOR) != 1:
        raise ValueError(f'expected exactly one method anchor, found {text.count(METHOD_ANCHOR)}')
    return text.replace(ANCHOR, REPLACEMENT, 1).replace(METHOD_ANCHOR, METHODS + METHOD_ANCHOR, 1)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    text = transform(args.input.read_text())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text)


if __name__ == '__main__':
    main()
