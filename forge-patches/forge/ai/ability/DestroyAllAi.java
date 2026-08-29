/*
 * Decompiled with CFR 0.152.
 * 
 * Could not load the following classes:
 *  forge.game.CardTraitBase
 *  forge.game.GameEntity
 *  forge.game.GameObject
 *  forge.game.card.Card
 *  forge.game.card.CardCollection
 *  forge.game.card.CardCollectionView
 *  forge.game.card.CardLists
 *  forge.game.card.CardPredicates
 *  forge.game.card.CounterEnumType
 *  forge.game.card.CounterType
 *  forge.game.combat.Combat
 *  forge.game.cost.Cost
 *  forge.game.cost.CostDamage
 *  forge.game.keyword.Keyword
 *  forge.game.phase.PhaseType
 *  forge.game.player.Player
 *  forge.game.spellability.SpellAbility
 *  forge.game.zone.ZoneType
 *  forge.util.collect.FCollectionView
 */
package forge.ai.ability;

import forge.ai.AiAbilityDecision;
import forge.ai.AiBlockController;
import forge.ai.AiPlayDecision;
import forge.ai.ComputerUtilCard;
import forge.ai.ComputerUtilCombat;
import forge.ai.ComputerUtilCost;
import forge.ai.SpecialCardAi;
import forge.ai.SpellAbilityAi;
import forge.game.CardTraitBase;
import forge.game.GameEntity;
import forge.game.GameObject;
import forge.game.card.Card;
import forge.game.card.CardCollection;
import forge.game.card.CardCollectionView;
import forge.game.card.CardLists;
import forge.game.card.CardPredicates;
import forge.game.card.CounterEnumType;
import forge.game.card.CounterType;
import forge.game.combat.Combat;
import forge.game.cost.Cost;
import forge.game.cost.CostDamage;
import forge.game.keyword.Keyword;
import forge.game.phase.PhaseType;
import forge.game.player.Player;
import forge.game.spellability.SpellAbility;
import forge.game.zone.ZoneType;
import forge.util.collect.FCollectionView;
import java.util.Iterator;
import java.util.function.Predicate;

public class DestroyAllAi
extends SpellAbilityAi {
    private static final Predicate<Card> predicate = c -> !c.hasKeyword(Keyword.INDESTRUCTIBLE) && c.getCounters((CounterType)CounterEnumType.SHIELD) <= 0 && !c.hasSVar("SacMe");

    @Override
    protected AiAbilityDecision doTriggerNoCost(Player ai, SpellAbility sa, boolean mandatory) {
        if (mandatory) {
            return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
        }
        return DestroyAllAi.doMassRemovalLogic(ai, sa);
    }

    @Override
    public AiAbilityDecision chkDrawback(Player aiPlayer, SpellAbility sa) {
        return DestroyAllAi.doMassRemovalLogic(aiPlayer, sa);
    }

    @Override
    protected AiAbilityDecision checkApiLogic(Player ai, SpellAbility sa) {
        String aiLogic = sa.getParamOrDefault("AILogic", "");
        if ("FellTheMighty".equals(aiLogic)) {
            return SpecialCardAi.FellTheMighty.consider(ai, sa);
        }
        return DestroyAllAi.doMassRemovalLogic(ai, sa);
    }

    public static AiAbilityDecision doMassRemovalLogic(Player ai, SpellAbility sa) {
        Iterator iterator;
        Card source = sa.getHostCard();
        String logic = sa.getParamOrDefault("AILogic", "");
        int CREATURE_EVAL_THRESHOLD = 200 / (!sa.usesTargeting() ? ai.getOpponents().size() : 1);
        if (logic.equals("Always")) {
            return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
        }
        String valid = sa.getParamOrDefault("ValidCards", "");
        if (valid.contains("X") && sa.getSVar("X").equals("Count$xPaid")) {
            ComputerUtilCost.setMaxXValue(sa, ai, sa.isTrigger());
        }
        if ((iterator = ai.getOpponents().iterator()).hasNext()) {
            Player opponent = (Player)iterator.next();
            CardCollection opplist = CardLists.getValidCards((Iterable)opponent.getCardsIn(ZoneType.Battlefield), (String)valid, (Player)source.getController(), (Card)source, (CardTraitBase)sa);
            CardCollection ailist = CardLists.getValidCards((Iterable)ai.getCardsIn(ZoneType.Battlefield), (String)valid, (Player)source.getController(), (Card)source, (CardTraitBase)sa);
            opplist = CardLists.filter((Iterable)opplist, predicate);
            ailist = CardLists.filter((Iterable)ailist, predicate);
            if (opplist.isEmpty()) {
                return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
            }
            if (sa.usesTargeting()) {
                sa.resetTargets();
                if (sa.canTarget((GameObject)opponent)) {
                    sa.getTargets().add((GameObject)opponent);
                    ailist.clear();
                } else {
                    return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
                }
            }
            if (logic.equals("RaidingParty")) {
                int numAiCanSave = Math.min(CardLists.count((Iterable)ai.getCreaturesInPlay(), CardPredicates.isColor((byte)1).and(CardPredicates.UNTAPPED)) * 2, ailist.size());
                int numOppsCanSave = Math.min(CardLists.count((Iterable)ai.getOpponents().getCreaturesInPlay(), CardPredicates.isColor((byte)1).and(CardPredicates.UNTAPPED)) * 2, opplist.size());
                if (numOppsCanSave < opplist.size() && ailist.size() - numAiCanSave < opplist.size() - numOppsCanSave) {
                    return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
                }
                if (numAiCanSave < ailist.size() && opplist.size() - numOppsCanSave < ailist.size() - numAiCanSave) {
                    return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
                }
            }
            if (!CardLists.getType((Iterable)opplist, (String)"Creature").isEmpty() && ai.getGame().getPhaseHandler().is(PhaseType.COMBAT_DECLARE_BLOCKERS) && ai.getGame().getCombat() != null && ComputerUtilCombat.lifeInSeriousDanger(ai, ai.getGame().getCombat())) {
                return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
            }
            if (!CardLists.getType((Iterable)opplist, (String)"Creature").isEmpty() && ai.getGame().getPhaseHandler().is(PhaseType.COMBAT_DECLARE_BLOCKERS) && ai.getGame().getCombat() != null && ComputerUtilCombat.lifeInDanger(ai, ai.getGame().getCombat()) && ComputerUtilCard.evaluatePermanentList((CardCollectionView)ailist) - 6 >= ComputerUtilCard.evaluatePermanentList((CardCollectionView)opplist)) {
                return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
            }
            if (CardLists.getNotType((Iterable)opplist, (String)"Creature").isEmpty() && CardLists.getNotType((Iterable)ailist, (String)"Creature").isEmpty()) {
                if ("Supreme Verdict".equals(source.getName())) {
                    int oppPower = 0;
                    for (Card c : opplist) {
                        oppPower += c.getNetPower();
                    }
                    boolean lifeInDanger = ai.getLife() <= oppPower || (ai.getGame().getCombat() != null && ComputerUtilCombat.lifeInDanger(ai, ai.getGame().getCombat()));
                    if (!lifeInDanger) {
                        if (opplist.size() < 2 && oppPower < 5) {
                            return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
                        }
                        if (opplist.size() < ailist.size() + 1) {
                            return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
                        }
                    }
                }
                if (ComputerUtilCard.evaluateCreatureList((CardCollectionView)ailist) + CREATURE_EVAL_THRESHOLD < ComputerUtilCard.evaluateCreatureList((CardCollectionView)opplist)) {
                    return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
                }
                if (ai.getGame().getPhaseHandler().getPhase().isBefore(PhaseType.MAIN2)) {
                    return new AiAbilityDecision(0, AiPlayDecision.WaitForMain2);
                }
                Combat combat = new Combat(opponent);
                boolean containsAttacker = false;
                for (Card att : opponent.getCreaturesInPlay()) {
                    if (!ComputerUtilCombat.canAttackNextTurn(att, (GameEntity)ai)) continue;
                    combat.addAttacker(att, (GameEntity)ai);
                    containsAttacker = containsAttacker || opplist.contains((Object)att);
                }
                if (!containsAttacker) {
                    return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
                }
                AiBlockController block = new AiBlockController(ai, false);
                block.assignBlockersForCombat(combat);
                if (ComputerUtilCombat.lifeInSeriousDanger(ai, combat)) {
                    return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
                }
                return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
            }
            if (CardLists.getNotType((Iterable)opplist, (String)"Land").isEmpty() && CardLists.getNotType((Iterable)ailist, (String)"Land").isEmpty()) {
                if (ai.isCardInPlay("Crucible of Worlds") && !opponent.isCardInPlay("Crucible of Worlds")) {
                    return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
                }
                CardCollection aiCreatures = ai.getCreaturesInPlay();
                CardCollection oppCreatures = opponent.getCreaturesInPlay();
                if (!oppCreatures.isEmpty() && ComputerUtilCard.evaluateCreatureList((CardCollectionView)aiCreatures) < ComputerUtilCard.evaluateCreatureList((CardCollectionView)oppCreatures) + CREATURE_EVAL_THRESHOLD) {
                    return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
                }
                if (ComputerUtilCard.evaluatePermanentList((CardCollectionView)ailist) > ComputerUtilCard.evaluatePermanentList((CardCollectionView)opplist) + 1) {
                    return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
                }
            } else if (ComputerUtilCard.evaluatePermanentList((CardCollectionView)ailist) + 3 >= ComputerUtilCard.evaluatePermanentList((CardCollectionView)opplist)) {
                return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
            }
            return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
        }
        return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
    }

    @Override
    public boolean willPayUnlessCost(Player payer, SpellAbility sa, Cost cost, boolean alreadyPaid, FCollectionView<Player> payers) {
        Card source = sa.getHostCard();
        if (payers.size() > 1 && alreadyPaid) {
            return false;
        }
        String valid = sa.getParamOrDefault("ValidCards", "");
        CardCollection ailist = CardLists.getValidCards((Iterable)payer.getCardsIn(ZoneType.Battlefield), (String)valid, (Player)source.getController(), (Card)source, (CardTraitBase)sa);
        if ((ailist = CardLists.filter((Iterable)ailist, predicate)).isEmpty()) {
            return false;
        }
        if (cost.hasSpecificCostType(CostDamage.class)) {
            if (!payer.canLoseLife()) {
                return false;
            }
            CostDamage pay = (CostDamage)cost.getCostPartByType(CostDamage.class);
            int realDamage = ComputerUtilCombat.predictDamageTo((GameEntity)payer, pay.getAbilityAmount(sa), source, false);
            if (realDamage > payer.getLife()) {
                return false;
            }
            if (realDamage > ailist.size() * 3) {
                return false;
            }
        }
        return super.willPayUnlessCost(payer, sa, cost, alreadyPaid, payers);
    }
}
