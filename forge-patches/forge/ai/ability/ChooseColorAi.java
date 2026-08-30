package forge.ai.ability;

import forge.ai.AiAbilityDecision;
import forge.ai.AiPlayDecision;
import forge.ai.ComputerUtilAbility;
import forge.ai.ComputerUtilCost;
import forge.ai.SpecialCardAi;
import forge.ai.SpellAbilityAi;
import forge.card.MagicColor;
import forge.game.Game;
import forge.game.card.Card;
import forge.game.card.CardCollection;
import forge.game.card.CardCollectionView;
import forge.game.card.CardLists;
import forge.game.card.CardPredicates;
import forge.game.combat.Combat;
import forge.game.phase.PhaseHandler;
import forge.game.phase.PhaseType;
import forge.game.player.Player;
import forge.game.spellability.SpellAbility;
import forge.game.zone.ZoneType;

public class ChooseColorAi extends SpellAbilityAi {

    @Override
    protected AiAbilityDecision checkApiLogic(Player ai, SpellAbility sa) {
        Game game = ai.getGame();
        String sourceName = ComputerUtilAbility.getAbilitySourceName(sa);
        PhaseHandler phase = game.getPhaseHandler();

        if (!sa.hasParam("AILogic")) {
            return new AiAbilityDecision(0, AiPlayDecision.MissingLogic);
        }

        String logic = sa.getParam("AILogic");

        if ("Prismatic Strands".equals(sourceName) || ("MostProminentInHumanDeck".equals(logic) && sa.getHostCard() != null && "Prismatic Strands".equals(sa.getHostCard().getName()))) {
            return checkPrismaticStrands(ai, sa, game, phase);
        }

        if ("Nykthos, Shrine to Nyx".equals(sourceName)) {
            if (SpecialCardAi.NykthosShrineToNyx.consider(ai, sa)) {
                return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
            }
            return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
        }

        if ("Oona, Queen of the Fae".equals(sourceName)) {
            if (!phase.isPlayerTurn(ai) && phase.getPhase().isBefore(PhaseType.COMBAT_DECLARE_ATTACKERS)) {
                return new AiAbilityDecision(0, AiPlayDecision.AnotherTime);
            }
            ComputerUtilCost.setMaxXValue(sa, ai, false);
            return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
        }

        if ("Addle".equals(sourceName)) {
            if (!phase.getPhase().isBefore(PhaseType.COMBAT_DECLARE_ATTACKERS) && !ai.getWeakestOpponent().getCardsIn(ZoneType.Hand).isEmpty()) {
                return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
            }
            return new AiAbilityDecision(0, AiPlayDecision.AnotherTime);
        }

        if ("MostExcessOpponentControls".equals(logic)) {
            byte[] wubrg = MagicColor.WUBRG;
            for (byte color : wubrg) {
                CardCollectionView myCards = ai.getColoredCardsInPlay(color);
                CardCollectionView oppCards = ai.getStrongestOpponent().getColoredCardsInPlay(color);
                int diff = forge.ai.ComputerUtilCard.evaluatePermanentList(oppCards) - forge.ai.ComputerUtilCard.evaluatePermanentList(myCards);
                if (diff > 4) {
                    return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
                }
            }
            return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
        }

        if ("MostProminentInComputerDeck".equals(logic)) {
            if ("Astral Cornucopia".equals(sourceName)) {
                CardCollection handNonland = CardLists.filter((Iterable<Card>) ai.getCardsIn(ZoneType.Hand), CardPredicates.NONLAND_PERMANENTS);
                if (!handNonland.isEmpty() && phase.is(PhaseType.MAIN2, ai)) {
                    return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
                }
                return new AiAbilityDecision(0, AiPlayDecision.WaitForMain2);
            }
        }

        if ("HighestDevotionToColor".equals(logic)) {
            if (!phase.is(PhaseType.MAIN2, ai)) {
                return new AiAbilityDecision(0, AiPlayDecision.WaitForMain2);
            }
        }

        return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
    }

    private AiAbilityDecision checkPrismaticStrands(Player ai, SpellAbility sa, Game game, PhaseHandler phase) {
        Combat combat = game.getCombat();
        int life = ai.getLife();

        if (combat != null) {
            CardCollection oppAttackers = CardLists.filterControlledBy(combat.getAttackers(), ai.getOpponents());
            if (!oppAttackers.isEmpty()) {
                int maxColorDamage = 0;
                int totalPower = 0;

                for (byte color : MagicColor.WUBRG) {
                    int colPower = 0;
                    for (Card c : oppAttackers) {
                        if ((c.getColor().getColor() & color) != 0) {
                            colPower += Math.max(0, c.getNetPower());
                        }
                    }
                    if (colPower > maxColorDamage) {
                        maxColorDamage = colPower;
                    }
                }
                for (Card c : oppAttackers) {
                    totalPower += Math.max(0, c.getNetPower());
                }

                // Prefer lethal prevention: total incoming damage or max single-color damage >= current life
                if (totalPower >= life || maxColorDamage >= life) {
                    return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
                }

                // Substantial non-lethal prevention: preventing approx 3+ relevant damage
                if (maxColorDamage >= 3) {
                    return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
                }

                // Near-lethal safety window
                if (life <= 6 && maxColorDamage >= 1) {
                    return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
                }
            }
        }

        return new AiAbilityDecision(0, AiPlayDecision.AnotherTime);
    }

    @Override
    protected AiAbilityDecision doTriggerNoCost(Player ai, SpellAbility sa, boolean mandatory) {
        if (mandatory) {
            return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
        }
        return canPlay(ai, sa);
    }
}
