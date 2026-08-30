/*
 * Decompiled with CFR 0.152.
 * 
 * Could not load the following classes:
 *  forge.game.CardTraitBase
 *  forge.game.CardTraitPredicates
 *  forge.game.GameObject
 *  forge.game.ability.AbilityUtils
 *  forge.game.card.Card
 *  forge.game.card.CardCollection
 *  forge.game.card.CardLists
 *  forge.game.card.CardPredicates
 *  forge.game.card.CounterType
 *  forge.game.cost.CostRemoveCounter
 *  forge.game.keyword.Keyword
 *  forge.game.mana.Mana
 *  forge.game.mana.ManaPool
 *  forge.game.phase.PhaseHandler
 *  forge.game.phase.PhaseType
 *  forge.game.player.Player
 *  forge.game.player.PlayerCollection
 *  forge.game.player.PlayerPredicates
 *  forge.game.spellability.SpellAbility
 *  forge.game.zone.ZoneType
 *  forge.util.Aggregates
 *  forge.util.IterableUtil
 */
package forge.ai.ability;

import forge.ai.AiAbilityDecision;
import forge.ai.AiPlayDecision;
import forge.ai.ComputerUtil;
import forge.ai.ComputerUtilAbility;
import forge.ai.ComputerUtilCard;
import forge.ai.ComputerUtilCost;
import forge.ai.ComputerUtilMana;
import forge.ai.PlayerControllerAi;
import forge.ai.SpellAbilityAi;
import forge.card.ColorSet;
import forge.card.MagicColor;
import forge.card.mana.ManaCost;
import forge.game.CardTraitBase;
import forge.game.CardTraitPredicates;
import forge.game.GameObject;
import forge.game.ability.AbilityUtils;
import forge.game.card.Card;
import forge.game.card.CardCollection;
import forge.game.card.CardLists;
import forge.game.card.CardPredicates;
import forge.game.card.CounterType;
import forge.game.cost.CostRemoveCounter;
import forge.game.keyword.Keyword;
import forge.game.mana.Mana;
import forge.game.mana.ManaPool;
import forge.game.phase.PhaseHandler;
import forge.game.phase.PhaseType;
import forge.game.player.Player;
import forge.game.player.PlayerCollection;
import forge.game.player.PlayerPredicates;
import forge.game.spellability.SpellAbility;
import forge.game.zone.ZoneType;
import forge.util.Aggregates;
import forge.util.IterableUtil;
import java.util.Arrays;
import java.util.Collection;
import java.util.List;
import java.util.function.Predicate;

public class ManaAi
extends SpellAbilityAi {
    @Override
    protected boolean checkAiLogic(Player ai, SpellAbility sa, String aiLogic) {
        if (aiLogic.startsWith("ManaRitual") || aiLogic.startsWith("BlackLotus")) {
            return ManaAi.doManaRitualLogic(ai, sa, false);
        }
        if ("Always".equals(aiLogic)) {
            return true;
        }
        return super.checkAiLogic(ai, sa, aiLogic);
    }

    @Override
    protected boolean checkPhaseRestrictions(Player ai, SpellAbility sa, PhaseHandler ph) {
        if (this.improvesPosition(ai, sa)) {
            return true;
        }
        if (!ph.is(PhaseType.MAIN2)) {
            return false;
        }
        return super.checkPhaseRestrictions(ai, sa, ph);
    }

    @Override
    protected boolean checkPhaseRestrictions(Player ai, SpellAbility sa, PhaseHandler ph, String logic) {
        if (logic.startsWith("ManaRitual")) {
            return ph.is(PhaseType.MAIN2, ai) || ph.is(PhaseType.MAIN1, ai);
        }
        if ("AtOppEOT".equals(logic)) {
            return ph.is(PhaseType.END_OF_TURN) && ph.getNextTurn() == ai && (!ai.getManaPool().hasBurn() || !ai.canLoseLife() || ai.cantLoseForZeroOrLessLife());
        }
        return super.checkPhaseRestrictions(ai, sa, ph, logic);
    }

    @Override
    protected AiAbilityDecision checkApiLogic(Player ai, SpellAbility sa) {
        if (sa.hasParam("AILogic")) {
            return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
        }
        if (ComputerUtil.activateForCost(sa, ai)) {
            return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
        }
        if (sa.getPayCosts().hasNoManaCost() && sa.getPayCosts().isReusuableResource() && sa.getSubAbility() == null && (this.improvesPosition(ai, sa) || ComputerUtil.playImmediately(ai, sa))) {
            return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
        }
        return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
    }

    @Override
    protected AiAbilityDecision doTriggerNoCost(Player aiPlayer, SpellAbility sa, boolean mandatory) {
        String logic = sa.getParamOrDefault("AILogic", "");
        if (logic.startsWith("ManaRitual")) {
            boolean result = ManaAi.doManaRitualLogic(aiPlayer, sa, true);
            return result ? new AiAbilityDecision(100, AiPlayDecision.WillPlay) : new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
        }
        return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
    }

    public static boolean doManaRitualLogic(Player ai, SpellAbility sa, boolean fromTrigger) {
        Card host = sa.getHostCard();
        String logic = sa.getParamOrDefault("AILogic", "");
        if (sa.usesTargeting()) {
            PlayerCollection targetableOpps = ai.getOpponents().filter(PlayerPredicates.isTargetableBy((SpellAbility)sa));
            if (targetableOpps.isEmpty()) {
                return false;
            }
            Player mostCards = targetableOpps.max(PlayerPredicates.compareByZoneSize((ZoneType)ZoneType.Hand));
            sa.resetTargets();
            sa.getTargets().add((GameObject)mostCards);
            if (fromTrigger) {
                return true;
            }
        }
        CardCollection manaSources = ComputerUtilMana.getAvailableManaSources(ai, true);
        int numManaSrcs = manaSources.size();
        int manaReceived = sa.hasParam("Amount") ? AbilityUtils.calculateAmount((Card)host, (String)sa.getParam("Amount"), (CardTraitBase)sa) : 1;
        manaReceived *= sa.getParam("Produced").split(" ").length;
        int selfCost = sa.getRootAbility().getPayCosts().getCostMana() != null ? sa.getRootAbility().getPayCosts().getCostMana().getMana().getCMC() : 0;
        String produced = sa.getParam("Produced");
        byte producedColor = produced.equals("Any") ? (byte)31 : (byte)MagicColor.fromName(produced);
        int numCounters = 0;
        int manaSurplus = 0;
        if ("Count$xPaid".equals(host.getSVar("X")) && sa.getPayCosts().hasSpecificCostType(CostRemoveCounter.class)) {
            CounterType ctrType = ((CostRemoveCounter)sa.getPayCosts().getCostPartByType(CostRemoveCounter.class)).counter;
            manaReceived = numCounters = host.getCounters(ctrType);
            if (logic.startsWith("ManaRitualBattery.")) {
                manaSurplus = Integer.parseInt(logic.substring(18));
                manaReceived += manaSurplus;
            }
        }
        int searchCMC = numManaSrcs - selfCost + manaReceived;
        if ("X".equals(sa.getParam("Produced"))) {
            String x = host.getSVar("X");
            if ("Count$CardsInYourHand".equals(x) && host.isInZone(ZoneType.Hand)) {
                --searchCMC;
            } else if (x.startsWith("Count$ValidGraveyard Card.named") && host.isInZone(ZoneType.Graveyard)) {
                --searchCMC;
            }
        }
        if (searchCMC <= 0) {
            return false;
        }
        String restrictValid = sa.getParamOrDefault("RestrictValid", "Card");
        CardCollection cardList = new CardCollection();
        List<SpellAbility> all = ComputerUtilAbility.getSpellAbilities(ai.getCardsIn(ZoneType.Hand), ai);
        for (SpellAbility testSa : ComputerUtilAbility.getOriginalAndAltCostAbilities(all, ai)) {
            SpellAbility testSaNoCost;
            ManaCost cost = testSa.getPayCosts().getTotalMana();
            boolean canPayWithAvailableColors = cost.canBePaidWithAvailable(ColorSet.fromNames(ComputerUtilCost.getAvailableManaColors(ai, (List<Card>)null)).getColor());
            if (cost.getCMC() == 0 && cost.countX() == 0 || cost.getColorProfile() != 0 && !canPayWithAvailableColors || ComputerUtilAbility.getAbilitySourceName(testSa).equals(ComputerUtilAbility.getAbilitySourceName(sa)) || testSa.hasParam("AINoRecursiveCheck") || (testSaNoCost = testSa.copyWithNoManaCost()) == null) continue;
            testSaNoCost.setActivatingPlayer(ai);
            if (((PlayerControllerAi)ai.getController()).getAi().canPlaySa(testSaNoCost) != AiPlayDecision.WillPlay || testSa.getHostCard().isPermanent() && !testSa.getHostCard().hasKeyword(Keyword.HASTE) && !ai.getGame().getPhaseHandler().is(PhaseType.MAIN2) || (testSa.getHostCard().isInstant() && !testSa.getHostCard().hasKeyword(Keyword.STORM) && !"Hunting Pack".equals(testSa.getHostCard().getName())) || cardList.contains(testSa.getHostCard())) continue;
            cardList.add(testSa.getHostCard());
        }
        CardCollection castableSpells = CardLists.filter((Iterable)cardList, Arrays.asList(CardPredicates.restriction((String[])restrictValid.split(","), (Player)ai, (Card)host, (CardTraitBase)sa), CardPredicates.lessCMC((int)searchCMC), CardPredicates.isColorless().or(CardPredicates.isColor((byte)producedColor))));
        if (logic.startsWith("ManaRitualBattery")) {
            int maxCtrs = Aggregates.max((Iterable<Card>)castableSpells, (java.util.function.Function<Card, Integer>)Card::getCMC) - manaSurplus;
            sa.setXManaCostPaid(Integer.valueOf(Math.min(numCounters, maxCtrs)));
        }
        return castableSpells.size() > 0;
    }

    private boolean improvesPosition(Player ai, SpellAbility sa) {
        boolean activateForTrigger = (!ai.getManaPool().hasBurn() || !ai.canLoseLife() || ai.cantLoseForZeroOrLessLife()) && IterableUtil.any((Iterable)IterableUtil.filter((Collection)sa.getHostCard().getTriggers(), (Predicate)CardTraitPredicates.hasParam((String)"AILogic", (String)"ActivateOnce")), t -> sa.getHostCard().getAbilityActivatedThisTurn(((forge.game.trigger.Trigger)t).getOverridingAbility()) == 0);
        PhaseHandler ph = ai.getGame().getPhaseHandler();
        return !(!ph.is(PhaseType.END_OF_TURN) || ph.getNextTurn() != ai && !ComputerUtilCard.willUntap(ai, sa.getHostCard()) || !activateForTrigger && !ManaAi.canRampPool(ai, sa.getHostCard()));
    }

    public static boolean canRampPool(Player ai, Card source) {
        ManaPool mp = ai.getManaPool();
        Mana test = null;
        if (mp.isEmpty()) {
            test = new Mana((byte)32, source, null, ai);
            mp.addManaNoEvent(test);
        }
        boolean lose = mp.willManaBeLostAtEndOfPhase();
        if (test != null) {
            mp.removeManaNoEvent(test);
        }
        return !lose;
    }
}
