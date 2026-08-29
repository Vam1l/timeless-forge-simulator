package forge.ai.ability;

import forge.ai.AiAbilityDecision;
import forge.ai.AiPlayDecision;
import forge.ai.ComputerUtil;
import forge.ai.SpellAbilityAi;
import forge.game.card.Card;
import forge.game.card.CardLists;
import forge.game.card.CardPredicates;
import forge.game.phase.PhaseHandler;
import forge.game.phase.PhaseType;
import forge.game.player.Player;
import forge.game.spellability.SpellAbility;
import forge.game.zone.ZoneType;

public class PermanentAi extends SpellAbilityAi {

    @Override
    protected boolean checkPhaseRestrictions(Player ai, SpellAbility sa, PhaseHandler phase) {
        Card card = sa.getHostCard();
        if (card.hasKeyword("MayFlashSac") && !ai.canCastSorcery()) {
            return false;
        }
        if (phase.is(PhaseType.MAIN1) && phase.isPlayerTurn(ai) && !sa.hasParam("WithoutManaCost")) {
            String name = card.getName();
            if ("Chromatic Star".equals(name) || "Chromatic Sphere".equals(name) || "Tinder Wall".equals(name)) {
                return true;
            }
            if (card.isArtifact() && !card.getManaAbilities().isEmpty()) {
                return true;
            }
            return ComputerUtil.castPermanentInMain1(ai, sa);
        }
        return true;
    }

    @Override
    protected AiAbilityDecision checkApiLogic(Player ai, SpellAbility sa) {
        Card card = sa.getHostCard();
        if (!card.ignoreLegendRule() && ai.isCardInPlay(card.getName())) {
            if (!card.hasSVar("AILegendaryException")) {
                return new AiAbilityDecision(0, AiPlayDecision.WouldDestroyLegend);
            }
            String exception = card.getSVar("AILegendaryException");
            if ("TwoCopiesAllowed".equals(exception)) {
                int count = CardLists.count(ai.getCardsIn(ZoneType.Battlefield), CardPredicates.nameEquals(card.getName()));
                if (count > 1) {
                    return new AiAbilityDecision(0, AiPlayDecision.WouldDestroyLegend);
                }
            }
        }
        return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
    }

    @Override
    protected AiAbilityDecision doTriggerNoCost(Player ai, SpellAbility sa, boolean mandatory) {
        if (mandatory) {
            return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
        }
        return canPlay(ai, sa);
    }
}
