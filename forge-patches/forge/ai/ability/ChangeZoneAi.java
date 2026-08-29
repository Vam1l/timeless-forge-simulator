/*
 * Decompiled with CFR 0.152.
 * 
 * Could not load the following classes:
 *  com.google.common.collect.Iterables
 *  com.google.common.collect.Lists
 *  com.google.common.collect.Multiset$Entry
 *  forge.game.CardTraitBase
 *  forge.game.Game
 *  forge.game.GameEntity
 *  forge.game.GameObject
 *  forge.game.ability.AbilityKey
 *  forge.game.ability.AbilityUtils
 *  forge.game.ability.ApiType
 *  forge.game.card.Card
 *  forge.game.card.CardCollection
 *  forge.game.card.CardCollectionView
 *  forge.game.card.CardCopyService
 *  forge.game.card.CardLists
 *  forge.game.card.CardPredicates
 *  forge.game.card.CardUtil
 *  forge.game.card.CounterEnumType
 *  forge.game.card.CounterType
 *  forge.game.combat.Combat
 *  forge.game.cost.Cost
 *  forge.game.cost.CostDamage
 *  forge.game.cost.CostDiscard
 *  forge.game.cost.CostPart
 *  forge.game.cost.CostPayLife
 *  forge.game.cost.CostPutCounter
 *  forge.game.keyword.Keyword
 *  forge.game.phase.PhaseHandler
 *  forge.game.phase.PhaseType
 *  forge.game.player.Player
 *  forge.game.player.PlayerActionConfirmMode
 *  forge.game.spellability.AbilitySub
 *  forge.game.spellability.SpellAbility
 *  forge.game.spellability.TargetRestrictions
 *  forge.game.staticability.StaticAbilityMustTarget
 *  forge.game.zone.ZoneType
 *  forge.util.Aggregates
 *  forge.util.MyRandom
 *  forge.util.collect.FCollectionView
 *  org.apache.commons.lang3.StringUtils
 */
package forge.ai.ability;

import com.google.common.collect.Iterables;
import com.google.common.collect.Lists;
import com.google.common.collect.Multiset;
import forge.ai.AiAbilityDecision;
import forge.ai.AiAttackController;
import forge.ai.AiCardMemory;
import forge.ai.AiPlayDecision;
import forge.ai.AiProfileUtil;
import forge.ai.AiProps;
import forge.ai.ComputerUtil;
import forge.ai.ComputerUtilAbility;
import forge.ai.ComputerUtilCard;
import forge.ai.ComputerUtilCombat;
import forge.ai.ComputerUtilCost;
import forge.ai.ComputerUtilMana;
import forge.ai.SpecialAiLogic;
import forge.ai.SpecialCardAi;
import forge.ai.SpellAbilityAi;
import forge.ai.ability.AttachAi;
import forge.card.CardType;
import forge.card.MagicColor;
import forge.game.CardTraitBase;
import forge.game.Game;
import forge.game.GameEntity;
import forge.game.GameObject;
import forge.game.ability.AbilityKey;
import forge.game.ability.AbilityUtils;
import forge.game.ability.ApiType;
import forge.game.card.Card;
import forge.game.card.CardCollection;
import forge.game.card.CardCollectionView;
import forge.game.card.CardCopyService;
import forge.game.card.CardLists;
import forge.game.card.CardPredicates;
import forge.game.card.CardUtil;
import forge.game.card.CounterEnumType;
import forge.game.card.CounterType;
import forge.game.combat.Combat;
import forge.game.cost.Cost;
import forge.game.cost.CostDamage;
import forge.game.cost.CostDiscard;
import forge.game.cost.CostPart;
import forge.game.cost.CostPayLife;
import forge.game.cost.CostPutCounter;
import forge.game.keyword.Keyword;
import forge.game.phase.PhaseHandler;
import forge.game.phase.PhaseType;
import forge.game.player.Player;
import forge.game.player.PlayerActionConfirmMode;
import forge.game.spellability.AbilitySub;
import forge.game.spellability.SpellAbility;
import forge.game.spellability.TargetRestrictions;
import forge.game.staticability.StaticAbilityMustTarget;
import forge.game.zone.ZoneType;
import forge.util.Aggregates;
import forge.util.MyRandom;
import forge.util.collect.FCollectionView;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Predicate;
import java.util.stream.Collectors;
import org.apache.commons.lang3.StringUtils;

public class ChangeZoneAi
extends SpellAbilityAi {
    private static CardCollection multipleCardsToChoose = new CardCollection();

    @Override
    protected boolean willPayCosts(Player payer, SpellAbility sa, Cost cost, Card source) {
        if (sa.isHidden()) {
            if (!(ComputerUtilCost.checkSacrificeCost(payer, cost, source, sa) || "Battlefield".equals(sa.getParam("Destination")) || source.isLand())) {
                return false;
            }
            if (!ComputerUtilCost.checkLifeCost(payer, cost, source, 4, sa)) {
                return false;
            }
            if (!ComputerUtilCost.checkDiscardCost(payer, cost, source, sa)) {
                for (CostPart part : cost.getCostParts()) {
                    CostDiscard cd;
                    if (!(part instanceof CostDiscard) || (cd = (CostDiscard)part).payCostFromSource() && ComputerUtil.isWorseThanDraw(payer, source)) continue;
                    return false;
                }
            }
            return true;
        }
        if (sa.isCraft() && !ComputerUtilCost.checkExileFromGraveCost(cost, payer, sa)) {
            return false;
        }
        return super.willPayCosts(payer, sa, cost, source);
    }

    @Override
    protected boolean checkAiLogic(Player ai, SpellAbility sa, String aiLogic) {
        if (sa.getHostCard() != null && sa.getHostCard().hasSVar("AIPreferenceOverride")) {
            sa.getHostCard().removeSVar("AIPreferenceOverride");
        }
        if (aiLogic.equals("SurpriseBlock")) {
            if (ai.getGame().getPhaseHandler().getPhase().isBefore(PhaseType.COMBAT_DECLARE_ATTACKERS)) {
                return false;
            }
        } else if (aiLogic.equals("PriorityOptionalCost")) {
            boolean highPriority = false;
            highPriority |= CardLists.count((Iterable)ai.getCardsIn(ZoneType.Hand), (Predicate)CardPredicates.nameEquals((String)sa.getHostCard().getName())) > 1;
            if (!(highPriority |= ai.getGame().getPhaseHandler().is(PhaseType.COMBAT_DECLARE_BLOCKERS) && ai.getGame().getCombat() != null && ComputerUtilCombat.lifeInDanger(ai, ai.getGame().getCombat())) && Iterables.isEmpty((Iterable)sa.getOptionalCosts())) {
                return false;
            }
        } else {
            if (aiLogic.equals("NoSameCreatureType")) {
                ArrayList origin = Lists.newArrayList();
                if (sa.hasParam("Origin")) {
                    origin.addAll(ZoneType.listValueOf((String)sa.getParam("Origin")));
                } else if (sa.hasParam("TgtZone")) {
                    origin.addAll(ZoneType.listValueOf((String)sa.getParam("TgtZone")));
                }
                CardCollection list = CardLists.getValidCards((Iterable)ai.getGame().getCardsIn((Iterable)origin), (String[])sa.getTargetRestrictions().getValidTgts(), (Player)ai, (Card)sa.getHostCard(), (CardTraitBase)sa);
                ArrayList creatureTypes = Lists.newArrayList();
                for (Card c : list) {
                    creatureTypes.addAll(c.getType().getCreatureTypes());
                }
                for (String type : (Iterable<String>)creatureTypes) {
                    int freq = Collections.frequency(creatureTypes, type);
                    if (freq <= 1) continue;
                    return false;
                }
                return true;
            }
            if (aiLogic.equals("Pongify")) {
                return SpecialAiLogic.doPongifyLogic(ai, sa);
            }
        }
        return super.checkAiLogic(ai, sa, aiLogic);
    }

    @Override
    protected AiAbilityDecision checkApiLogic(Player aiPlayer, SpellAbility sa) {
        multipleCardsToChoose.clear();
        String aiLogic = sa.getParam("AILogic");
        if (aiLogic != null) {
            if (aiLogic.equals("Always")) {
                return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
            }
            if (aiLogic.startsWith("SacAndUpgrade")) {
                return this.doSacAndUpgradeLogic(aiPlayer, sa);
            }
            if (aiLogic.startsWith("SacAndRetFromGrave")) {
                return this.doSacAndReturnFromGraveLogic(aiPlayer, sa);
            }
            if (aiLogic.equals("Necropotence")) {
                return SpecialCardAi.Necropotence.consider(aiPlayer, sa);
            }
            if (aiLogic.equals("ReanimateAll")) {
                return SpecialCardAi.LivingDeath.consider(aiPlayer, sa);
            }
            if (aiLogic.equals("TheScarabGod")) {
                return SpecialCardAi.TheScarabGod.consider(aiPlayer, sa);
            }
            if (aiLogic.equals("SorinVengefulBloodlord")) {
                return SpecialCardAi.SorinVengefulBloodlord.consider(aiPlayer, sa);
            }
            if (aiLogic.equals("Intuition")) {
                multipleCardsToChoose = SpecialCardAi.Intuition.considerMultiple(aiPlayer, sa);
            } else {
                if (aiLogic.equals("MazesEnd")) {
                    return SpecialCardAi.MazesEnd.consider(aiPlayer, sa);
                }
                if (aiLogic.equals("Pongify")) {
                    if (sa.isTargetNumberValid()) {
                        return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
                    }
                    return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
                }
                if (aiLogic.equals("ReturnCastable")) {
                    if (!sa.getHostCard().getExiledCards().isEmpty() && ComputerUtilMana.canPayManaCost(((Card)sa.getHostCard().getExiledCards().getFirst()).getFirstSpellAbility(), aiPlayer, 0, false)) {
                        return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
                    }
                    return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
                }
            }
        }
        if (sa.isHidden()) {
            return ChangeZoneAi.hiddenOriginCanPlayAI(aiPlayer, sa);
        }
        return ChangeZoneAi.knownOriginCanPlayAI(aiPlayer, sa);
    }

    @Override
    public AiAbilityDecision chkDrawback(Player aiPlayer, SpellAbility sa) {
        if (sa.isHidden()) {
            return ChangeZoneAi.hiddenOriginPlayDrawbackAI(aiPlayer, sa);
        }
        return ChangeZoneAi.knownOriginPlayDrawbackAI(aiPlayer, sa);
    }

    @Override
    protected AiAbilityDecision doTriggerNoCost(Player aiPlayer, SpellAbility sa, boolean mandatory) {
        String aiLogic = sa.getParamOrDefault("AILogic", "");
        if (sa.isReplacementAbility() && "Command".equals(sa.getParam("Destination")) && "ReplacedCard".equals(sa.getParam("Defined"))) {
            return this.doReturnCommanderLogic(sa, aiPlayer);
        }
        if ("Always".equals(aiLogic)) {
            return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
        }
        if ("IfNotBuffed".equals(aiLogic)) {
            if (ComputerUtilCard.isUselessCreature(aiPlayer, sa.getHostCard())) {
                return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
            }
            int delta = 0;
            for (Card enc : sa.getHostCard().getEnchantedBy()) {
                if (enc.getController().isOpponentOf(aiPlayer)) {
                    --delta;
                    continue;
                }
                ++delta;
            }
            if (delta <= 0) {
                return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
            }
            return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
        }
        if ("SaviorOfOllenbock".equals(aiLogic)) {
            if (SpecialCardAi.SaviorOfOllenbock.consider(aiPlayer, sa)) {
                return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
            }
            return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
        }
        if (sa.isHidden()) {
            return ChangeZoneAi.hiddenTriggerAI(aiPlayer, sa, mandatory);
        }
        return ChangeZoneAi.knownOriginTriggerAI(aiPlayer, sa, mandatory);
    }

    private static AiAbilityDecision hiddenOriginCanPlayAI(Player ai, SpellAbility sa) {
        Object pDefined;
        TargetRestrictions tgt;
        Card source = sa.getHostCard();
        String sourceName = ComputerUtilAbility.getAbilitySourceName(sa);
        String aiLogic = sa.getParamOrDefault("AILogic", "");
        List origin = null;
        Player opponent = AiAttackController.choosePreferredDefenderPlayer(ai);
        boolean activateForCost = ComputerUtil.activateForCost(sa, ai);
        if (sa.hasParam("Origin")) {
            origin = ZoneType.listValueOf((String)sa.getParam("Origin"));
        }
        String destination = sa.getParam("Destination");
        if (sa.isNinjutsu()) {
            if (!source.ignoreLegendRule() && ai.isCardInPlay(source.getName())) {
                return new AiAbilityDecision(0, AiPlayDecision.WouldDestroyLegend);
            }
            if (ai.getGame().getPhaseHandler().getPhase().isAfter(PhaseType.COMBAT_DAMAGE)) {
                return new AiAbilityDecision(0, AiPlayDecision.WaitForCombat);
            }
            if (ai.getGame().getCombat() == null) {
                return new AiAbilityDecision(0, AiPlayDecision.WaitForCombat);
            }
            CardCollection attackers = ai.getGame().getCombat().getUnblockedAttackers();
            boolean lowerCMC = false;
            for (Card attacker : attackers) {
                if (attacker.getCMC() >= source.getCMC()) continue;
                lowerCMC = true;
                break;
            }
            if (!lowerCMC) {
                return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
            }
        }
        if ((tgt = sa.getTargetRestrictions()) != null && tgt.canTgtPlayer()) {
            sa.resetTargets();
            boolean isCurse = sa.isCurse();
            if (isCurse && sa.canTarget((GameObject)opponent)) {
                sa.getTargets().add((GameObject)opponent);
            } else if (!isCurse && sa.canTarget((GameObject)ai)) {
                sa.getTargets().add((GameObject)ai);
            }
            if (!sa.isTargetNumberValid()) {
                return new AiAbilityDecision(0, AiPlayDecision.TargetingFailed);
            }
            pDefined = sa.getTargets().getTargetPlayers();
        } else {
            pDefined = sa.hasParam("DefinedPlayer") ? AbilityUtils.getDefinedPlayers((Card)source, (String)sa.getParam("DefinedPlayer"), (CardTraitBase)sa) : AbilityUtils.getDefinedPlayers((Card)source, (String)sa.getParam("Defined"), (CardTraitBase)sa);
        }
        String type = sa.getParam("ChangeType");
        if (type != null && type.contains("X")) {
            ComputerUtilCost.setMaxXValue(sa, ai, sa.isTrigger());
        }
        for (Player p : (Iterable<Player>)pDefined) {
            CardCollectionView list = p.getCardsIn((Iterable)origin);
            if (!ai.canSearchLibraryWith(sa, p)) {
                list = CardLists.filter((Iterable)list, CardPredicates.inZone((ZoneType)ZoneType.Library).negate());
            }
            if (type != null && p == ai) {
                list = CardLists.getValidCards((Iterable)list, (String)type, (Player)source.getController(), (Card)source, (CardTraitBase)sa);
                list = CardLists.filter((Iterable)list, c -> {
                    if (c.getType().isLegendary()) {
                        return !ai.isCardInPlay(c.getName());
                    }
                    return true;
                });
            }
            if (origin != null && origin.size() == 1 && ((ZoneType)origin.get(0)).isKnown()) {
                list = CardLists.getValidCards((Iterable)list, (String)type, (Player)source.getController(), (Card)source, (CardTraitBase)sa);
            }
            if (!activateForCost && list.isEmpty()) {
                return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
            }
            if ("Atarka's Command".equals(sourceName) && (list.size() < 2 || ai.getLandsPlayedThisTurn() < 1)) {
                return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
            }
            String num = sa.getParamOrDefault("ChangeNum", "1");
            if (num.contains("X")) {
                if (sa.getSVar("X").equals("Count$xPaid")) {
                    int xPay = ComputerUtilCost.setMaxXValue(sa, ai, sa.isTrigger());
                    if (xPay == 0) {
                        return new AiAbilityDecision(0, AiPlayDecision.CantAffordX);
                    }
                    xPay = Math.min(xPay, list.size());
                    sa.setXManaCostPaid(Integer.valueOf(xPay));
                } else {
                    int xValue = AbilityUtils.calculateAmount((Card)source, (String)"X", (CardTraitBase)sa);
                    if (xValue == 0) {
                        return new AiAbilityDecision(0, AiPlayDecision.CantAffordX);
                    }
                }
            }
            if (!sourceName.equals("Temur Sabertooth")) continue;
            boolean pumpDecision = ComputerUtilCard.shouldPumpCard(ai, (SpellAbility)sa.getSubAbility(), source, 0, 0, Arrays.asList("Indestructible"));
            AiAbilityDecision saveDecision = ComputerUtilCard.canPumpAgainstRemoval(ai, (SpellAbility)sa.getSubAbility());
            if (pumpDecision || saveDecision.willingToPlay()) {
                for (Card c2 : list) {
                    if (ComputerUtilCard.evaluateCreature(c2) >= ComputerUtilCard.evaluateCreature(source)) continue;
                    return new AiAbilityDecision(100, AiPlayDecision.ResponseToStackResolve);
                }
            }
            if (ChangeZoneAi.canBouncePermanent(ai, sa, list) != null) {
                return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
            }
            return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
        }
        if (ComputerUtil.playImmediately(ai, sa)) {
            return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
        }
        if (ai.getGame().getPhaseHandler().getPhase().isBefore(PhaseType.MAIN2) && !sa.hasParam("ActivationPhases")) {
            if (!destination.equals("Battlefield") && !destination.equals("Hand")) {
                return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
            }
            if (ai.getCardsIn(ZoneType.Hand).size() > 1 && destination.equals("Hand") && !aiLogic.equals("AnyMainPhase")) {
                if (!("Expedition Map".equals(sourceName) && ai.getLandsPlayedThisTurn() == 0 && ai.getGame().getPhaseHandler().is(PhaseType.MAIN1, ai))) {
                    return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
                }
            }
        }
        if (ComputerUtil.waitForBlocking(sa)) {
            return new AiAbilityDecision(0, AiPlayDecision.WaitForCombat);
        }
        return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
    }

    private static AiAbilityDecision hiddenOriginPlayDrawbackAI(Player aiPlayer, SpellAbility sa) {
        TargetRestrictions tgt = sa.getTargetRestrictions();
        Player opp = AiAttackController.choosePreferredDefenderPlayer(aiPlayer);
        if (tgt != null && tgt.canTgtPlayer()) {
            boolean isCurse = sa.isCurse();
            if (isCurse && sa.canTarget((GameObject)opp)) {
                sa.getTargets().add((GameObject)opp);
            } else if (!isCurse && sa.canTarget((GameObject)aiPlayer)) {
                sa.getTargets().add((GameObject)aiPlayer);
            } else {
                return new AiAbilityDecision(0, AiPlayDecision.TargetingFailed);
            }
        }
        return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
    }

    private static AiAbilityDecision hiddenTriggerAI(Player ai, SpellAbility sa, boolean mandatory) {
        Object pDefined;
        TargetRestrictions tgt;
        List origin = new ArrayList();
        if (sa.hasParam("Origin")) {
            origin = ZoneType.listValueOf((String)sa.getParam("Origin"));
        }
        String type = sa.getParam("ChangeType");
        if (!mandatory && type != null && type.contains("X")) {
            ComputerUtilCost.setMaxXValue(sa, ai, sa.isTrigger());
        }
        if ((tgt = sa.getTargetRestrictions()) != null && tgt.canTgtPlayer()) {
            Player opp = AiAttackController.choosePreferredDefenderPlayer(ai);
            if (sa.isCurse()) {
                if (sa.canTarget((GameObject)opp)) {
                    sa.getTargets().add((GameObject)opp);
                } else if (mandatory && sa.canTarget((GameObject)ai)) {
                    sa.getTargets().add((GameObject)ai);
                }
            } else if (sa.canTarget((GameObject)ai)) {
                sa.getTargets().add((GameObject)ai);
            } else if (mandatory && sa.canTarget((GameObject)opp)) {
                sa.getTargets().add((GameObject)opp);
            }
            pDefined = sa.getTargets().getTargetPlayers();
            if (Iterables.isEmpty((Iterable)pDefined)) {
                return new AiAbilityDecision(0, AiPlayDecision.TargetingFailed);
            }
            if (mandatory) {
                return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
            }
        } else {
            if (mandatory) {
                return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
            }
            pDefined = AbilityUtils.getDefinedPlayers((Card)sa.getHostCard(), (String)sa.getParam("Defined"), (CardTraitBase)sa);
        }
        for (Player p : (Iterable<Player>)pDefined) {
            CardCollectionView list = p.getCardsIn(origin);
            if (p == ai) {
                list = AbilityUtils.filterListByType((CardCollectionView)list, (String)sa.getParam("ChangeType"), (SpellAbility)sa);
            }
            if (!list.isEmpty()) continue;
            return new AiAbilityDecision(0, AiPlayDecision.MissingNeededCards);
        }
        return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
    }

    private static Card basicManaFixing(Player ai, List<Card> list) {
        CardCollectionView combined = CardCollection.combine((CardCollectionView[])new CardCollectionView[]{ai.getCardsIn(ZoneType.Battlefield), ai.getCardsIn(ZoneType.Hand)});
        ArrayList<String> basics = new ArrayList<String>();
        for (String name : MagicColor.Constant.BASIC_LANDS) {
            if (CardLists.getType((Iterable)list, (String)name).isEmpty()) continue;
            basics.add(name);
        }
        int minSize = Integer.MAX_VALUE;
        String minType = null;
        for (String b : basics) {
            int num = CardLists.getType((Iterable)combined, (String)b).size();
            if (num >= minSize) continue;
            minType = b;
            minSize = num;
        }
        if (minType != null) {
            list = CardLists.getType((Iterable)list, minType);
        }
        if (list.stream().anyMatch(CardPredicates.NONBASIC_LANDS)) {
            list = CardLists.filter((Iterable)list, (Predicate)CardPredicates.NONBASIC_LANDS);
        }
        return (Card)list.get(0);
    }

    private static boolean areAllBasics(String types) {
        for (String ct : types.split(",")) {
            if (MagicColor.Constant.BASIC_LANDS.contains(ct)) continue;
            return false;
        }
        return true;
    }

    private static Card chooseCreature(Player ai, CardCollection list) {
        if (ComputerUtil.aiLifeInDanger(ai, false, 0)) {
            ComputerUtilCard.sortByEvaluateCreature(list);
            for (Card c : list) {
                if (!ComputerUtilMana.hasEnoughManaSourcesToCast(c.getFirstSpellAbility(), ai)) continue;
                return c;
            }
            return null;
        }
        if (ai.getTurn() <= 3) {
            CardCollection nearTerm;
            int manaSources = ComputerUtilMana.getAvailableManaEstimate(ai, false);
            if (CardLists.count((Iterable)ai.getCardsIn(ZoneType.Hand), (Predicate)CardPredicates.LANDS_PRODUCING_MANA) > 0) {
                ++manaSources;
            }
            final int finalManaSources = manaSources + 1;
            if (!(nearTerm = CardLists.filter((Iterable)list, arg_0 -> ChangeZoneAi.checkNearTermMana(finalManaSources, arg_0))).isEmpty()) {
                return ComputerUtilCard.getBestCreatureAI((Iterable<Card>)nearTerm);
            }
        }
        return ComputerUtilCard.getBestCreatureAI((Iterable<Card>)list);
    }

    private static AiAbilityDecision knownOriginCanPlayAI(Player ai, SpellAbility sa) {
        ArrayList origin = Lists.newArrayList();
        if (sa.hasParam("Origin")) {
            origin.addAll(ZoneType.listValueOf((String)sa.getParam("Origin")));
        } else if (sa.hasParam("TgtZone")) {
            origin.addAll(ZoneType.listValueOf((String)sa.getParam("TgtZone")));
        }
        ZoneType destination = ZoneType.smartValueOf((String)sa.getParam("Destination"));
        if (sa.usesTargeting()) {
            if (!ChangeZoneAi.isPreferredTarget(ai, sa, false, false)) {
                return new AiAbilityDecision(0, AiPlayDecision.TargetingFailed);
            }
        } else {
            CardCollection retrieval = sa.knownDetermineDefined(sa.getParam("Defined"));
            if (retrieval == null || retrieval.isEmpty()) {
                return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
            }
            if (origin.contains(ZoneType.Battlefield)) {
                if (ai.getGame().getStack().isEmpty()) {
                    return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
                }
                AbilitySub abSub = sa.getSubAbility();
                ApiType subApi = null;
                if (abSub != null) {
                    subApi = abSub.getApi();
                }
                if (!(destination.equals(ZoneType.Exile) && (subApi == ApiType.DelayedTrigger || subApi == ApiType.ChangeZone || "DelayedBlink".equals(sa.getParam("AILogic"))) || destination.equals(ZoneType.Hand))) {
                    return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
                }
                List<GameObject> objects = ComputerUtil.predictThreatenedObjects(ai, sa);
                boolean contains = false;
                for (Card c : retrieval) {
                    if (!objects.contains(c)) continue;
                    contains = true;
                    break;
                }
                if (!contains) {
                    return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
                }
            }
            if (destination == ZoneType.Battlefield) {
                if (ComputerUtil.isETBprevented((Card)retrieval.get(0))) {
                    return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
                }
                for (Card c : retrieval) {
                    if (!c.isCreature()) continue;
                    Card copy = CardCopyService.getLKICopy((Card)c);
                    ComputerUtilCard.applyStaticContPT(c.getGame(), copy, null);
                    if (copy.getNetToughness() > 0) continue;
                    return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
                }
                boolean nothingWillReturn = true;
                for (Card c : retrieval) {
                    boolean isCraftSa;
                    boolean bl = isCraftSa = sa.isCraft() && sa.getHostCard().equals(c);
                    if (!isCraftSa && !c.ignoreLegendRule() && ai.isCardInPlay(c.getName())) continue;
                    nothingWillReturn = false;
                    break;
                }
                if (nothingWillReturn) {
                    return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
                }
            }
        }
        return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
    }

    @Override
    protected boolean checkPhaseRestrictions(Player ai, SpellAbility sa, PhaseHandler ph) {
        String aiLogic = sa.getParamOrDefault("AILogic", "");
        if (aiLogic.equals("SurvivalOfTheFittest")) {
            return ph.getNextTurn().equals(ai) && ph.is(PhaseType.END_OF_TURN);
        }
        if (aiLogic.equals("Main1") && ph.is(PhaseType.MAIN1, ai)) {
            return true;
        }
        if (aiLogic.equals("BeforeCombat")) {
            return !ai.getGame().getPhaseHandler().getPhase().isAfter(PhaseType.COMBAT_BEGIN);
        }
        if (sa.isHidden()) {
            return true;
        }
        ArrayList origin = Lists.newArrayList();
        if (sa.hasParam("Origin")) {
            origin.addAll(ZoneType.listValueOf((String)sa.getParam("Origin")));
        } else if (sa.hasParam("TgtZone")) {
            origin.addAll(ZoneType.listValueOf((String)sa.getParam("TgtZone")));
        }
        ZoneType destination = ZoneType.smartValueOf((String)sa.getParam("Destination"));
        if (destination.equals(ZoneType.Hand) && origin.contains(ZoneType.Graveyard)) {
            int handSize = ai.getCardsIn(ZoneType.Hand).size();
            if (ph.getPhase().isBefore(PhaseType.MAIN1)) {
                return false;
            }
            if (ph.getPhase().isBefore(PhaseType.MAIN2) && handSize > 1) {
                return false;
            }
            if (ph.isPlayerTurn(ai) && handSize >= ai.getMaxHandSize()) {
                return false;
            }
        }
        if (sa.isKeyword(Keyword.UNEARTH) && ph.getPhase().isAfter(PhaseType.COMBAT_DECLARE_ATTACKERS)) {
            return false;
        }
        if (destination.equals(ZoneType.Library) && origin.contains(ZoneType.Graveyard)) {
            if (ph.getPhase().isBefore(PhaseType.MAIN2)) {
                return false;
            }
            if (ComputerUtil.waitForBlocking(sa)) {
                return false;
            }
        }
        return super.checkPhaseRestrictions(ai, sa, ph);
    }

    private static AiAbilityDecision knownOriginPlayDrawbackAI(Player aiPlayer, SpellAbility sa) {
        if ("MimicVat".equals(sa.getParam("AILogic"))) {
            if (SpecialCardAi.MimicVat.considerExile(aiPlayer, sa)) {
                return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
            }
            return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
        }
        if (!sa.usesTargeting()) {
            return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
        }
        if (!ChangeZoneAi.isPreferredTarget(aiPlayer, sa, false, true)) {
            return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
        }
        return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
    }

    private static boolean isPreferredTarget(Player ai, SpellAbility sa, boolean mandatory, boolean immediately) {
        boolean doWithoutTarget;
        CardCollection newList;
        Card source = sa.getHostCard();
        ArrayList origin = Lists.newArrayList();
        if (sa.hasParam("Origin")) {
            origin.addAll(ZoneType.listValueOf((String)sa.getParam("Origin")));
        } else if (sa.hasParam("TgtZone")) {
            origin.addAll(ZoneType.listValueOf((String)sa.getParam("TgtZone")));
        }
        if (origin.contains(ZoneType.Stack) && ChangeZoneAi.doExileSpellLogic(ai, sa, mandatory)) {
            return true;
        }
        ZoneType destination = ZoneType.smartValueOf((String)sa.getParam("Destination"));
        Game game = ai.getGame();
        AbilitySub abSub = sa.getSubAbility();
        ApiType subApi = null;
        String subAffected = "";
        if (abSub != null) {
            subApi = abSub.getApi();
            if (abSub.hasParam("Defined")) {
                subAffected = abSub.getParam("Defined");
            }
        }
        sa.resetTargets();
        if ("X".equals(sa.getTargetRestrictions().getMinTargets()) && sa.getSVar("X").equals("Count$xPaid")) {
            ComputerUtilCost.setMaxXValue(sa, ai, sa.isTrigger());
        }
        CardCollection list = CardLists.getTargetableCards((Iterable)game.getCardsIn((Iterable)origin), (SpellAbility)sa);
        list = ComputerUtil.filterAITgts(sa, ai, list, true);
        if (source.isInZone(ZoneType.Hand)) {
            list = CardLists.filter((Iterable)list, (Predicate)CardPredicates.nameNotEquals((String)source.getName()));
        }
        if (sa.isSpell()) {
            list.remove(source);
        }
        if (sa.hasParam("AttachedTo")) {
            list = CardLists.filter((Iterable)list, c -> {
                for (Card card : game.getCardsIn(ZoneType.Battlefield)) {
                    if (!card.isValid(sa.getParam("AttachedTo"), ai, c, (CardTraitBase)sa)) continue;
                    return true;
                }
                return false;
            });
        }
        if (sa.hasParam("AttachAfter")) {
            list = CardLists.filter((Iterable)list, c -> {
                for (Card card : game.getCardsIn(ZoneType.Battlefield)) {
                    if (!card.isValid(sa.getParam("AttachAfter"), ai, c, (CardTraitBase)sa)) continue;
                    return true;
                }
                return false;
            });
        }
        if (list.size() < sa.getMinTargets()) {
            return false;
        }
        boolean bl = immediately = immediately || ComputerUtil.playImmediately(ai, sa);
        if (list.isEmpty() && immediately && sa.getMaxTargets() == 0) {
            return true;
        }
        if (origin.contains(ZoneType.Battlefield)) {
            boolean blink;
            if ("Polymorph".equals(sa.getParam("AILogic"))) {
                list = CardLists.getTargetableCards((Iterable)ai.getCardsIn(ZoneType.Battlefield), (SpellAbility)sa);
                if (list.isEmpty()) {
                    return false;
                }
                Card worst = ComputerUtilCard.getWorstAI((Iterable<Card>)list);
                if (worst.isCreature() && ComputerUtilCard.evaluateCreature(worst) >= 200) {
                    return false;
                }
                if (!worst.isCreature() && worst.getCMC() > 1) {
                    return false;
                }
                sa.getTargets().add((GameObject)worst);
                return true;
            }
            if (sa.getMinTargets() <= 1 && game.getPhaseHandler().is(PhaseType.COMBAT_DECLARE_BLOCKERS)) {
                Combat currCombat = game.getCombat();
                CardCollection attackers = currCombat.getAttackers();
                ComputerUtilCard.sortByEvaluateCreature(attackers);
                for (Card attacker : attackers) {
                    CardCollection blockers = currCombat.getBlockers(attacker);
                    if (attacker.getController().equals(ai) && attacker.getShieldCount() == 0 && ComputerUtilCombat.attackerWouldBeDestroyed(ai, attacker, currCombat) && !currCombat.getBlockers(attacker).isEmpty()) {
                        ComputerUtilCard.sortByEvaluateCreature(blockers);
                        Combat combat = new Combat(ai);
                        combat.addAttacker(attacker, (GameEntity)ai.getWeakestOpponent());
                        for (Card blocker : blockers) {
                            combat.addBlocker(attacker, blocker);
                        }
                        for (Card blocker : blockers) {
                            combat.removeFromCombat(blocker);
                            if (!ComputerUtilCombat.attackerWouldBeDestroyed(ai, attacker, (Combat)combat) && sa.canTarget((GameObject)blocker)) {
                                sa.getTargets().add((GameObject)blocker);
                                return true;
                            }
                            combat.addBlocker(attacker, blocker);
                        }
                    }
                    if (!attacker.getController().isOpponentOf(ai) || blockers.isEmpty()) continue;
                    for (Card blocker : blockers) {
                        if (!ComputerUtilCombat.blockerWouldBeDestroyed(ai, blocker, currCombat) || !sa.canTarget((GameObject)attacker)) continue;
                        sa.getTargets().add((GameObject)attacker);
                        return true;
                    }
                }
            }
            boolean bl2 = blink = destination.equals(ZoneType.Exile) && (subApi == ApiType.DelayedTrigger || "DelayedBlink".equals(sa.getParam("AILogic")) || subApi == ApiType.ChangeZone && subAffected.equals("Remembered"));
            if ((destination.equals(ZoneType.Hand) || blink) && sa.getMinTargets() <= 1) {
                CardCollection blinkTargets;
                Card tobounce = ChangeZoneAi.canBouncePermanent(ai, sa, (CardCollectionView)list);
                if (tobounce != null) {
                    boolean saheeliFelidarCombo;
                    if ("BounceOnce".equals(sa.getParam("AILogic")) && ChangeZoneAi.isBouncedThisTurn(ai, tobounce)) {
                        return false;
                    }
                    sa.getTargets().add((GameObject)tobounce);
                    boolean bl3 = saheeliFelidarCombo = ComputerUtilAbility.getAbilitySourceName(sa).equals("Felidar Guardian") && tobounce.getName().equals("Saheeli Rai") && CardLists.filter((Iterable)ai.getCardsIn(ZoneType.Battlefield), (Predicate)CardPredicates.nameEquals((String)"Felidar Guardian")).size() < CardLists.filter((Iterable)ai.getOpponents().getCardsIn(ZoneType.Battlefield), (Predicate)CardPredicates.CREATURES).size() + ai.getOpponentsGreatestLifeTotal() + 10;
                    if (!saheeliFelidarCombo) {
                        ChangeZoneAi.rememberBouncedThisTurn(ai, tobounce);
                    }
                    return true;
                }
                if (blink && !(blinkTargets = CardLists.filter((Iterable)list, c -> !c.isToken() && c.getOwner().equals(ai) && (c.getController().isOpponentOf(ai) || c.hasETBTrigger(false)))).isEmpty()) {
                    CardCollection opponentBlinkTargets = CardLists.filterControlledBy((Iterable)blinkTargets, (FCollectionView)ai.getOpponents());
                    if (immediately || sa.getParent() != null || sa.isTrigger() || !opponentBlinkTargets.isEmpty() || !game.getPhaseHandler().getPhase().isBefore(PhaseType.MAIN2)) {
                        while (!blinkTargets.isEmpty() && sa.canAddMoreTarget()) {
                            Object choice = null;
                            if (!opponentBlinkTargets.isEmpty()) {
                                choice = ComputerUtilCard.getBestAI((Iterable<Card>)opponentBlinkTargets);
                                opponentBlinkTargets.remove(choice);
                            } else {
                                choice = ComputerUtilCard.getBestAI((Iterable<Card>)blinkTargets);
                            }
                            sa.getTargets().add((GameObject)choice);
                            blinkTargets.remove(choice);
                        }
                        return true;
                    }
                }
                if (!CardLists.getNotType((Iterable)(list = CardLists.filterControlledBy((Iterable)list, (FCollectionView)ai.getOpponents())), (String)"Land").isEmpty()) {
                    list = CardLists.filter((Iterable)list, c -> {
                        Iterator iterator = c.getEnchantedBy().iterator();
                        if (iterator.hasNext()) {
                            Card aura = (Card)iterator.next();
                            return aura.getController().isOpponentOf(ai);
                        }
                        if (blink) {
                            return c.isToken();
                        }
                        return c.isToken() || c.getCMC() > 0;
                    });
                }
            }
        } else if (origin.contains(ZoneType.Graveyard)) {
            if (destination.equals(ZoneType.Exile) || destination.equals(ZoneType.Library)) {
                if (!immediately && game.getPhaseHandler().getPhase().isBefore(PhaseType.MAIN2) && !sa.hasParam("ActivationPhases") && !ComputerUtil.castSpellInMain1(ai, sa)) {
                    return false;
                }
                if (!(immediately || game.getPhaseHandler().getNextTurn().equals(ai) && !game.getPhaseHandler().getPhase().isBefore(PhaseType.END_OF_TURN) || sa.hasParam("PlayerTurn") || ChangeZoneAi.isSorcerySpeed(sa, ai) || ComputerUtil.activateForCost(sa, ai))) {
                    return false;
                }
            } else if (destination.equals(ZoneType.Hand)) {
                list = CardLists.filterControlledBy((Iterable)list, (Player)ai);
            } else if (sa.hasParam("AttachedTo")) {
                list = CardLists.filter((Iterable)list, c -> {
                    for (SpellAbility attach : c.getSpellAbilities()) {
                        if (!"Pump".equals(attach.getParam("AILogic"))) continue;
                        return true;
                    }
                    return false;
                });
            }
        }
        if (origin.contains(ZoneType.Battlefield) && destination.equals(ZoneType.Exile) && (subApi == ApiType.DelayedTrigger || subApi == ApiType.ChangeZone && subAffected.equals("Remembered")) && !game.getPhaseHandler().is(PhaseType.COMBAT_DECLARE_ATTACKERS) && !sa.isAbility()) {
            return false;
        }
        if (destination.equals(ZoneType.Exile) || origin.contains(ZoneType.Battlefield)) {
            if (!immediately && game.getPhaseHandler().getPhase().isBefore(PhaseType.MAIN2) && game.getPhaseHandler().isPlayerTurn(ai) && ai.getCreaturesInPlay().isEmpty()) {
                return false;
            }
            if (!sa.hasParam("AITgtOwnCards")) {
                list = CardLists.filterControlledBy((Iterable)list, (FCollectionView)ai.getOpponents());
                list = CardLists.filter((Iterable)list, c -> {
                    for (Card aura : c.getEnchantedBy()) {
                        if (!c.getOwner().isOpponentOf(ai) || !aura.getController().equals(ai)) continue;
                        return false;
                    }
                    return true;
                });
            }
            if (CardLists.getNotType((Iterable)list, (String)"Creature").isEmpty()) {
                list = ComputerUtilCard.prioritizeCreaturesWorthRemovingNow(ai, list, false);
            }
        }
        if (game.getPhaseHandler().inCombat() && origin.contains(ZoneType.Battlefield) && (!(newList = CardLists.getValidCards((Iterable)list, (String)"Card.attacking,Card.blocking", null, null, null)).isEmpty() || !sa.isTrigger())) {
            list = newList;
        }
        boolean bl4 = doWithoutTarget = sa.isPwAbility() && sa.usesTargeting() && sa.getMinTargets() == 0 && sa.getPayCosts().hasSpecificCostType(CostPutCounter.class);
        if (list.isEmpty() && !doWithoutTarget) {
            return false;
        }
        list.removeAll((Collection)ChangeZoneAi.getSafeTargetsIfUnlessCostPaid(ai, sa, (Iterable<Card>)list));
        if (!mandatory && list.size() < sa.getMinTargets()) {
            return false;
        }
        while (sa.canAddMoreTarget()) {
            Card choice = null;
            if (!list.isEmpty()) {
                if (destination.equals(ZoneType.Battlefield) || origin.contains(ZoneType.Battlefield)) {
                    CardCollection originalList = new CardCollection((Iterable)list);
                    boolean mustTargetFiltered = StaticAbilityMustTarget.filterMustTargetCards((Player)ai, (List)list, (SpellAbility)sa);
                    Card card = choice = origin.contains(ZoneType.Battlefield) ? ComputerUtilCard.getBestRemovalTargetAI(ai, (Iterable<Card>)list) : ComputerUtilCard.getMostExpensivePermanentAI((Iterable<Card>)list);
                    if (choice.isCreature() && origin.contains(ZoneType.Graveyard)) {
                        for (Card c2 : list) {
                            if (!"Karmic Guide".equals(c2.getName())) continue;
                            choice = c2;
                            break;
                        }
                    }
                    if (!immediately && sa.getMaxTargets() == 1 && !ComputerUtilCard.useRemovalNow(sa, choice, 0, destination)) {
                        return false;
                    }
                    if (mustTargetFiltered) {
                        list = originalList;
                    }
                } else if (destination.equals(ZoneType.Hand) || destination.equals(ZoneType.Library)) {
                    CardCollection nonLands = CardLists.getNotType((Iterable)list, (String)"Land");
                    choice = ChangeZoneAi.chooseCreature(ai, CardLists.filter((Iterable)nonLands, (Predicate)CardPredicates.CREATURES));
                    if (choice == null) {
                        if (ai.getLife() <= 5) {
                            CardLists.sortByCmcDesc((List)nonLands);
                            for (Card potentialCard : nonLands) {
                                if (!ComputerUtilMana.hasEnoughManaSourcesToCast(potentialCard.getFirstSpellAbility(), ai)) continue;
                                choice = potentialCard;
                                break;
                            }
                        } else {
                            choice = ComputerUtilCard.getBestAI((Iterable<Card>)nonLands);
                        }
                    }
                    if (choice == null) {
                        CardLists.shuffle((List)list);
                        choice = (Card)list.get(0);
                    }
                } else {
                    choice = ComputerUtilCard.getBestAI((Iterable<Card>)list);
                }
            }
            if (choice == null) {
                if (sa.getTargets().isEmpty() || !sa.isTargetNumberValid()) {
                    if (!mandatory) {
                        sa.resetTargets();
                    }
                    if (doWithoutTarget) break;
                    return false;
                }
                if (sa.isTrigger() || ComputerUtil.shouldCastLessThanMax(ai, source)) break;
                boolean aiTgtsOK = false;
                if (sa.hasParam("AIMinTgts")) {
                    int minTgts = Integer.parseInt(sa.getParam("AIMinTgts"));
                    if (sa.getTargets().size() >= minTgts) {
                        aiTgtsOK = true;
                    }
                }
                if (aiTgtsOK) break;
                return false;
            }
            list.remove(choice);
            if (!sa.canTarget(choice)) continue;
            sa.getTargets().add(choice);
        }
        return true;
    }

    private static Card canBouncePermanent(Player ai, SpellAbility sa, CardCollectionView list) {
        CardCollectionView saheeli;
        Game game = ai.getGame();
        CardCollection aiPermanents = CardLists.filterControlledBy((Iterable)list, (Player)ai);
        CardCollection aiPlaneswalkers = CardLists.filter((Iterable)aiPermanents, (Predicate)CardPredicates.PLANESWALKERS);
        if (sa.getHostCard().getName().equals("Felidar Guardian") && !(saheeli = ai.getCardsIn(ZoneType.Battlefield, "Saheeli Rai")).isEmpty()) {
            return (Card)saheeli.get(0);
        }
        aiPermanents = ComputerUtil.getSafeTargets(ai, sa, (CardCollectionView)aiPermanents);
        if (!game.getStack().isEmpty()) {
            List<GameObject> objects = ComputerUtil.predictThreatenedObjects(ai, sa);
            ArrayList threatenedTargets = Lists.newArrayList((Iterable)aiPermanents);
            threatenedTargets.retainAll(objects);
            if (!threatenedTargets.isEmpty()) {
                return ComputerUtilCard.getBestAI(threatenedTargets);
            }
        } else if (game.getPhaseHandler().is(PhaseType.COMBAT_DECLARE_BLOCKERS)) {
            Combat combat = game.getCombat();
            CardCollection combatants = CardLists.filter((Iterable)aiPermanents, (Predicate)CardPredicates.CREATURES);
            ComputerUtilCard.sortByEvaluateCreature(combatants);
            for (Card c : combatants) {
                if (c.getShieldCount() != 0 || !ComputerUtilCombat.combatantWouldBeDestroyed(ai, (Card)c, combat) || c.getOwner() != ai || c.isToken()) continue;
                return c;
            }
        } else if (!(aiPlaneswalkers.isEmpty() || !sa.getHostCard().isSorcery() && game.getPhaseHandler().isPlayerTurn(ai))) {
            int maxLoyaltyToConsider = AiProfileUtil.getIntProperty(ai, AiProps.BLINK_RELOAD_PLANESWALKER_MAX_LOYALTY);
            int loyaltyDiff = AiProfileUtil.getIntProperty(ai, AiProps.BLINK_RELOAD_PLANESWALKER_LOYALTY_DIFF);
            int chance = AiProfileUtil.getIntProperty(ai, AiProps.BLINK_RELOAD_PLANESWALKER_CHANCE);
            if (MyRandom.percentTrue((int)chance)) {
                aiPlaneswalkers.sort(CardPredicates.compareByCounterType((CounterType)CounterEnumType.LOYALTY));
                for (Card pw : aiPlaneswalkers) {
                    int curLoyalty = pw.getCounters((CounterType)CounterEnumType.LOYALTY);
                    int freshLoyalty = Integer.parseInt(pw.getCurrentState().getBaseLoyalty());
                    if (freshLoyalty - curLoyalty < loyaltyDiff || curLoyalty > maxLoyaltyToConsider) continue;
                    return pw;
                }
            }
        }
        Object bestChoice = null;
        int bestEval = 0;
        for (Card c : aiPermanents) {
            int eval;
            if (!c.isCreature()) continue;
            boolean hasValuableAttachments = false;
            boolean hasOppAttachments = false;
            int numNegativeCounters = 0;
            int numTotalCounters = 0;
            for (Card attached : c.getAttachedCards()) {
                if (!attached.isAura()) continue;
                if (attached.getController() == c.getController()) {
                    hasValuableAttachments = true;
                    continue;
                }
                if (!attached.getController().isOpponentOf(c.getController())) continue;
                hasOppAttachments = true;
            }
            for (Multiset.Entry e : c.getCounters().entrySet()) {
                if (ComputerUtil.isNegativeCounter((CounterType)e.getElement(), (Card)c)) {
                    numNegativeCounters += e.getCount();
                }
                numTotalCounters += e.getCount();
            }
            if (hasValuableAttachments || ComputerUtilCard.isUselessCreature(ai, (Card)c) && !hasOppAttachments) continue;
            Object considered = null;
            if ((c.hasKeyword(Keyword.PERSIST) || c.hasKeyword(Keyword.UNDYING)) && !ComputerUtilCard.hasActiveUndyingOrPersist((Card)c)) {
                considered = c;
            } else if (hasOppAttachments || numTotalCounters > 0 && numNegativeCounters > numTotalCounters / 2) {
                considered = c;
            }
            if (considered == null || (eval = ComputerUtilCard.evaluateCreature((Card)c)) <= bestEval) continue;
            bestEval = eval;
            bestChoice = considered;
        }
        return (Card)bestChoice;
    }

    private static boolean isUnpreferredTarget(Player ai, SpellAbility sa, boolean mandatory) {
        if (!mandatory && !"Always".equals(sa.getParam("AILogic"))) {
            return false;
        }
        Card source = sa.getHostCard();
        ZoneType destination = ZoneType.smartValueOf((String)sa.getParam("Destination"));
        TargetRestrictions tgt = sa.getTargetRestrictions();
        CardCollection list = CardUtil.getValidCardsToTarget((SpellAbility)sa);
        if (list.isEmpty()) {
            return false;
        }
        while (!sa.isMinTargetChosen()) {
            Card choice = null;
            if (!(list = CardLists.canSubsequentlyTarget((CardCollection)list, (SpellAbility)sa)).isEmpty()) {
                if (tgt.getZone().contains(ZoneType.Battlefield)) {
                    choice = ComputerUtilCard.getBestRemovalTargetAI(ai, (Iterable<Card>)list);
                } else if (destination.equals(ZoneType.Battlefield)) {
                    choice = ComputerUtilCard.getMostExpensivePermanentAI((Iterable<Card>)list);
                    if (choice.isCreature()) {
                        choice = ComputerUtilCard.getBestCreatureAI((Iterable<Card>)list);
                    }
                } else if (destination.equals(ZoneType.Hand) || destination.equals(ZoneType.Library)) {
                    CardCollection nonLands = CardLists.getNotType((Iterable)list, (String)"Land");
                    choice = ChangeZoneAi.chooseCreature(ai, CardLists.filter((Iterable)nonLands, (Predicate)CardPredicates.CREATURES));
                    if (choice == null) {
                        if (ai.getLife() <= 5) {
                            CardLists.sortByCmcDesc((List)nonLands);
                            for (Card potentialCard : nonLands) {
                                if (!ComputerUtilMana.hasEnoughManaSourcesToCast(potentialCard.getFirstSpellAbility(), ai)) continue;
                                choice = potentialCard;
                                break;
                            }
                        } else {
                            choice = ComputerUtilCard.getBestAI((Iterable<Card>)nonLands);
                        }
                    }
                    if (choice == null) {
                        CardLists.shuffle((List)list);
                        choice = (Card)list.get(0);
                    }
                } else {
                    choice = ComputerUtilCard.getBestAI((Iterable<Card>)list);
                }
            }
            if (choice == null) {
                if (sa.getTargets().isEmpty() || sa.getTargets().size() < sa.getMinTargets()) {
                    sa.resetTargets();
                    return false;
                }
                if (ComputerUtil.shouldCastLessThanMax(ai, source)) break;
                return false;
            }
            list.remove(choice);
            sa.getTargets().add((GameObject)choice);
        }
        return true;
    }

    private static AiAbilityDecision knownOriginTriggerAI(Player ai, SpellAbility sa, boolean mandatory) {
        String logic = sa.getParamOrDefault("AILogic", "");
        if ("DeathgorgeScavenger".equals(logic)) {
            if (SpecialCardAi.DeathgorgeScavenger.consider(ai, sa)) {
                return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
            }
            return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
        }
        if ("ExtraplanarLens".equals(logic)) {
            if (SpecialCardAi.ExtraplanarLens.consider(ai, sa)) {
                return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
            }
            return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
        }
        if ("ExileCombatThreat".equals(logic)) {
            return ChangeZoneAi.doExileCombatThreatLogic(ai, sa);
        }
        if (!sa.usesTargeting()) {
            CardCollection list;
            if (!mandatory && sa.hasParam("AttachedTo") && !(list = AbilityUtils.getDefinedCards((Card)sa.getHostCard(), (String)sa.getParam("AttachedTo"), (CardTraitBase)sa)).isEmpty()) {
                Card attachedTo = (Card)list.get(0);
                if (!attachedTo.getController().isOpponentOf(ai)) {
                    return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
                }
                return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
            }
        } else if (!ChangeZoneAi.isPreferredTarget(ai, sa, mandatory, true)) {
            if (ChangeZoneAi.isUnpreferredTarget(ai, sa, mandatory)) {
                return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
            }
            return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
        }
        return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
    }

    public static Card chooseCardToHiddenOriginChangeZone(ZoneType destination, List<ZoneType> origin, SpellAbility sa, CardCollection fetchList, Player player, Player decider) {
        Card c;
        if (fetchList.isEmpty()) {
            return null;
        }
        List keyCards = player.getRegisteredPlayer().getDeck().getKeyCards();
        String position = sa.getParamOrDefault("LibraryPosition", null);
        if (destination.equals(ZoneType.Battlefield) || destination.equals(ZoneType.Hand) || destination.equals(ZoneType.Library) && "0".equals(position)) {
            for (Card c2 : player.getCardsIn(new ZoneType[]{ZoneType.Hand, ZoneType.Battlefield})) {
                keyCards.remove(c2.getName());
            }
        }
        Card keycardFound = null;
        for (String keyName : (Iterable<String>)keyCards) {
            CardCollection withKeyCard = CardLists.filter((Iterable)fetchList, (Predicate)CardPredicates.nameEquals((String)keyName));
            if (withKeyCard.isEmpty()) continue;
            keycardFound = (Card)withKeyCard.getFirst();
            break;
        }
        if (sa.hasParam("AILogic")) {
            String logic = sa.getParamOrDefault("AILogic", "");
            if ("NeverBounceItself".equals(logic)) {
                Card source = sa.getHostCard();
                if (fetchList.contains(source) && (fetchList.size() > 1 || !sa.getRootAbility().isMandatory())) {
                    fetchList.remove(source);
                }
            } else {
                if ("WorstCard".equals(logic)) {
                    return ComputerUtilCard.getWorstAI((Iterable<Card>)fetchList);
                }
                if ("BestCard".equals(logic)) {
                    if (keycardFound != null) {
                        return keycardFound;
                    }
                    return ComputerUtilCard.getBestAI((Iterable<Card>)fetchList);
                }
                if ("Mairsil".equals(logic)) {
                    return SpecialCardAi.MairsilThePretender.considerCardFromList(fetchList, sa);
                }
                if ("SurvivalOfTheFittest".equals(logic)) {
                    return SpecialCardAi.SurvivalOfTheFittest.considerCardToGet(decider, sa);
                }
                if ("MazesEnd".equals(logic)) {
                    return SpecialCardAi.MazesEnd.considerCardToGet(decider, sa);
                }
                if ("Intuition".equals(logic)) {
                    if (!multipleCardsToChoose.isEmpty()) {
                        Card choice = (Card)multipleCardsToChoose.get(0);
                        multipleCardsToChoose.remove(0);
                        return choice;
                    }
                } else {
                    if (logic.startsWith("ExilePreference")) {
                        return ChangeZoneAi.doExilePreferenceLogic(decider, sa, fetchList);
                    }
                    if (logic.equals("BounceOwnTrigger")) {
                        return ChangeZoneAi.doBounceOwnTriggerLogic(decider, sa, fetchList);
                    }
                    if (logic.equals("ConsiderRamp") && (c = ChangeZoneAi.considerRamp(decider, sa, fetchList, keycardFound)) != null) {
                        return c;
                    }
                }
            }
        }
        if (fetchList.isEmpty()) {
            return null;
        }
        String type = sa.getParamOrDefault("ChangeType", "");
        c = null;
        Player activator = sa.getActivatingPlayer();
        CardLists.shuffle((List)fetchList);
        Card first = (Card)fetchList.get(0);
        if (ZoneType.Battlefield.equals(destination)) {
            fetchList = CardLists.filter((Iterable)fetchList, c1 -> {
                if (c1.getType().isLegendary()) {
                    return !decider.isCardInPlay(c1.getName());
                }
                return true;
            });
            if (player.isOpponentOf(decider) && sa.hasParam("GainControl") && activator.equals(decider)) {
                fetchList = CardLists.filter((Iterable)fetchList, c12 -> !ComputerUtilCard.isCardRemAIDeck(c12) && !ComputerUtilCard.isCardRemRandomDeck(c12));
            }
        }
        if (ZoneType.Exile.equals(destination) || origin.contains(ZoneType.Battlefield) || ZoneType.Library.equals(destination) && origin.contains(ZoneType.Hand)) {
            if (player.isOpponentOf(decider)) {
                c = ComputerUtilCard.getBestAI((Iterable<Card>)fetchList);
            } else {
                Card tobounce;
                if (!sa.hasParam("Mandatory") && origin.contains(ZoneType.Battlefield) && sa.hasParam("ChangeNum") && (fetchList = ChangeZoneAi.prefilterOwnListForBounceAnyNum(fetchList, decider)).isEmpty()) {
                    return null;
                }
                c = ComputerUtilCard.getWorstAI((Iterable<Card>)fetchList);
                if (ComputerUtilAbility.getAbilitySourceName(sa).equals("Temur Sabertooth") && (tobounce = ChangeZoneAi.canBouncePermanent(player, sa, (CardCollectionView)fetchList)) != null) {
                    c = tobounce;
                    ChangeZoneAi.rememberBouncedThisTurn(player, c);
                }
            }
        } else if (origin.contains(ZoneType.Library) && (type.contains("Basic") || ChangeZoneAi.areAllBasics(type))) {
            if (keycardFound != null) {
                return keycardFound;
            }
            c = ChangeZoneAi.basicManaFixing(decider, (List<Card>)fetchList);
        } else if (ZoneType.Hand.equals(destination) && CardLists.getNotType((Iterable)fetchList, (String)"Creature").isEmpty()) {
            if (keycardFound != null) {
                return keycardFound;
            }
            c = ChangeZoneAi.chooseCreature(decider, fetchList);
        } else if (ZoneType.Battlefield.equals(destination) || ZoneType.Graveyard.equals(destination)) {
            if (!activator.equals(decider) && sa.hasParam("GainControl")) {
                c = ComputerUtilCard.getWorstAI((Iterable<Card>)fetchList);
            } else {
                if (keycardFound != null) {
                    return keycardFound;
                }
                c = ComputerUtilCard.getBestAI((Iterable<Card>)fetchList);
            }
        } else {
            CardCollection sameNamed = CardLists.filter((Iterable)fetchList, (Predicate)CardPredicates.nameNotEquals((String)ComputerUtilAbility.getAbilitySourceName(sa)));
            if (origin.contains(ZoneType.Library) && !sameNamed.isEmpty()) {
                fetchList = sameNamed;
            }
            if (keycardFound != null) {
                return keycardFound;
            }
            CardCollectionView hand = decider.getCardsIn(ZoneType.Hand);
            if (!hand.anyMatch(CardPredicates.LANDS) && CardLists.count((Iterable)decider.getCardsIn(ZoneType.Battlefield), (Predicate)CardPredicates.LANDS) < 4 && !hand.anyMatch(crd -> ComputerUtilMana.hasEnoughManaSourcesToCast(crd.getFirstSpellAbility(), decider))) {
                c = ChangeZoneAi.basicManaFixing(decider, (List<Card>)fetchList);
            }
            if (c == null) {
                if (fetchList.allMatch(CardPredicates.LANDS)) {
                    c = ComputerUtilCard.getBestLandAI((Iterable<Card>)fetchList);
                } else {
                    fetchList = CardLists.getNotType((Iterable)fetchList, (String)"Land");
                    c = ChangeZoneAi.chooseCreature(decider, CardLists.filter((Iterable)fetchList, (Predicate)CardPredicates.CREATURES));
                }
            }
            if (c == null) {
                if (decider.getLife() <= 5) {
                    CardLists.sortByCmcDesc((List)fetchList);
                    for (Card potentialCard : fetchList) {
                        if (!ComputerUtilMana.hasEnoughManaSourcesToCast(potentialCard.getFirstSpellAbility(), decider)) continue;
                        c = potentialCard;
                        break;
                    }
                } else {
                    c = ComputerUtilCard.getBestAI((Iterable<Card>)fetchList);
                }
            }
        }
        if (c == null) {
            c = first;
        }
        return c;
    }

    private static CardCollection prefilterOwnListForBounceAnyNum(CardCollection fetchList, Player decider) {
        fetchList = CardLists.filter((Iterable)fetchList, card -> {
            if (card.isToken()) {
                return false;
            }
            if (card.isCreature() && ComputerUtilCard.isUselessCreature(decider, card)) {
                return true;
            }
            if (card.isEquipped()) {
                return false;
            }
            if (card.isEnchanted()) {
                for (Card enc : card.getEnchantedBy()) {
                    if (!enc.getOwner().isOpponentOf(decider)) continue;
                    return true;
                }
                return false;
            }
            if (card.hasCounters()) {
                if (card.isPlaneswalker()) {
                    int maxLoyaltyToConsider = AiProfileUtil.getIntProperty(decider, AiProps.BLINK_RELOAD_PLANESWALKER_MAX_LOYALTY);
                    int loyaltyDiff = AiProfileUtil.getIntProperty(decider, AiProps.BLINK_RELOAD_PLANESWALKER_LOYALTY_DIFF);
                    int chance = AiProfileUtil.getIntProperty(decider, AiProps.BLINK_RELOAD_PLANESWALKER_CHANCE);
                    if (MyRandom.percentTrue((int)chance)) {
                        int curLoyalty = card.getCounters((CounterType)CounterEnumType.LOYALTY);
                        int freshLoyalty = Integer.parseInt(card.getCurrentState().getBaseLoyalty());
                        if (freshLoyalty - curLoyalty >= loyaltyDiff && curLoyalty <= maxLoyaltyToConsider) {
                            return true;
                        }
                    }
                } else if (card.isCreature() && card.getCounters((CounterType)CounterEnumType.M1M1) > 0) {
                    return true;
                }
                return false;
            }
            return !card.isAura();
        });
        return fetchList;
    }

    @Override
    public boolean confirmAction(Player player, SpellAbility sa, PlayerActionConfirmMode mode, String message, Map<String, Object> params) {
        return true;
    }

    @Override
    public Card chooseSingleCard(Player ai, SpellAbility sa, Iterable<Card> options, boolean isOptional, Player targetedPlayer, Map<String, Object> params) {
        if (params.containsKey("Attach")) {
            return AttachAi.attachGeneralAI(ai, sa, (List)options, !isOptional, (Card)params.get("Attach"), sa.getParam("AILogic"));
        }
        return super.chooseSingleCard(ai, sa, options, isOptional, targetedPlayer, params);
    }

    @Override
    public Player chooseSinglePlayer(Player ai, SpellAbility sa, Iterable<Player> options, Map<String, Object> params) {
        if (params != null && params.containsKey("Attacker")) {
            return (Player)ComputerUtilCombat.addAttackerToCombat(sa, (Card)params.get("Attacker"), options);
        }
        return AttachAi.attachToPlayerAIPreferences(ai, sa, true, (List)options);
    }

    @Override
    protected GameEntity chooseSingleAttackableEntity(Player ai, SpellAbility sa, Iterable<GameEntity> options, Map<String, Object> params) {
        if (params != null && params.containsKey("Attacker")) {
            return ComputerUtilCombat.addAttackerToCombat(sa, (Card)params.get("Attacker"), options);
        }
        return super.chooseSingleAttackableEntity(ai, sa, options, params);
    }

    private AiAbilityDecision doSacAndReturnFromGraveLogic(Player ai, SpellAbility sa) {
        Card source = sa.getHostCard();
        String definedSac = StringUtils.split((String)source.getSVar("AIPreference"), (String)"$")[1];
        CardCollection listToSac = CardLists.getValidCards((Iterable)ai.getCardsIn(ZoneType.Battlefield), (String)definedSac, (Player)ai, (Card)source, (CardTraitBase)sa);
        listToSac.sort(CardLists.CmcComparator);
        CardCollection listToRet = CardLists.filter((Iterable)ai.getCardsIn(ZoneType.Graveyard), (Predicate)CardPredicates.CREATURES);
        listToRet.sort(CardLists.CmcComparatorInv);
        if (!listToSac.isEmpty() && !listToRet.isEmpty()) {
            Card worstSac = (Card)listToSac.getFirst();
            Card bestRet = (Card)listToRet.getFirst();
            if (bestRet.getCMC() > worstSac.getCMC() && ComputerUtilCard.evaluateCreature(bestRet) > ComputerUtilCard.evaluateCreature(worstSac)) {
                sa.resetTargets();
                sa.getTargets().add((GameObject)bestRet);
                source.setSVar("AIPreferenceOverride", "Creature.cmcEQ" + worstSac.getCMC());
                return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
            }
        }
        return new AiAbilityDecision(0, AiPlayDecision.TargetingFailed);
    }

    private AiAbilityDecision doSacAndUpgradeLogic(Player ai, SpellAbility sa) {
        Card source = sa.getHostCard();
        PhaseHandler ph = ai.getGame().getPhaseHandler();
        String logic = sa.getParam("AILogic");
        boolean sacWorst = logic.contains("SacWorst");
        if (!ph.is(PhaseType.MAIN2)) {
            return new AiAbilityDecision(0, AiPlayDecision.WaitForMain2);
        }
        String definedSac = StringUtils.split((String)source.getSVar("AIPreference"), (String)"$")[1];
        String definedGoal = sa.getParam("ChangeType");
        boolean anyCMC = !definedGoal.contains(".cmc");
        CardCollection listToSac = CardLists.getValidCards((Iterable)ai.getCardsIn(ZoneType.Battlefield), (String)definedSac, (Player)ai, (Card)source, (CardTraitBase)sa);
        listToSac.sort(!sacWorst ? CardLists.CmcComparatorInv : CardLists.CmcComparator);
        for (Card sacCandidate : listToSac) {
            int sacCMC = sacCandidate.getCMC();
            int goalCMC = source.hasSVar("X") ? AbilityUtils.calculateAmount((Card)source, (String)source.getSVar("X").replace("Sacrificed$CardManaCost", "Number$" + sacCMC), (CardTraitBase)sa) : sacCMC + 1;
            String curGoal = definedGoal;
            if (!anyCMC) {
                curGoal = definedGoal.replace("X", String.format("%d", goalCMC));
            }
            CardCollection listGoal = CardLists.getValidCards((Iterable)ai.getCardsIn(ZoneType.Library), (String)curGoal, (Player)ai, (Card)source, (CardTraitBase)sa);
            listGoal = !anyCMC ? CardLists.getValidCards((Iterable)listGoal, (String)curGoal, (Player)source.getController(), (Card)source, (CardTraitBase)sa) : CardLists.getValidCards((Iterable)listGoal, (String)(curGoal + (curGoal.contains(".") ? "+" : ".") + "cmcGE" + goalCMC), (Player)source.getController(), (Card)source, (CardTraitBase)sa);
            if ((listGoal = CardLists.filter((Iterable)listGoal, c -> {
                if (c.getType().isLegendary()) {
                    return !ai.isCardInPlay(c.getName());
                }
                return true;
            })).isEmpty()) continue;
            source.setSVar("AIPreferenceOverride", "Creature.cmcEQ" + sacCMC);
            return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
        }
        return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
    }

    public AiAbilityDecision doReturnCommanderLogic(SpellAbility sa, Player aiPlayer) {
        Card c;
        Map originalParams = (Map)sa.getReplacingObject(AbilityKey.OriginalParams);
        SpellAbility causeSa = (SpellAbility)originalParams.get(AbilityKey.Cause);
        AbilitySub causeSub = null;
        ZoneType destination = (ZoneType)originalParams.get(AbilityKey.Destination);
        if (ZoneType.Hand.equals(destination)) {
            return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
        }
        Object v = originalParams.get(AbilityKey.Affected);
        if (v instanceof Card && (c = (Card)v).getName().equals("Squee, the Immortal") && (destination == ZoneType.Graveyard || destination == ZoneType.Exile)) {
            return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
        }
        if (causeSa != null && (causeSub = causeSa.getSubAbility()) != null) {
            ApiType subApi = causeSub.getApi();
            if (subApi == ApiType.ChangeZone && "Exile".equals(causeSub.getParam("Origin")) && "Battlefield".equals(causeSub.getParam("Destination"))) {
                return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
            }
            if (subApi == ApiType.DelayedTrigger) {
                SpellAbility exec = causeSub.getAdditionalAbility("Execute");
                if (exec != null && exec.getApi() == ApiType.ChangeZone) {
                    if (!"Exile".equals(exec.getParam("Origin")) || !"Battlefield".equals(exec.getParam("Destination"))) {
                        return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
                    }
                    return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
                }
            } else {
                if (causeSa.getHostCard() == null || !causeSa.getHostCard().equals(sa.getReplacingObject(AbilityKey.Card)) || !causeSa.getActivatingPlayer().equals(aiPlayer)) {
                    return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
                }
                return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
            }
        }
        return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
    }

    public static AiAbilityDecision doExileCombatThreatLogic(Player aiPlayer, SpellAbility sa) {
        Combat combat = aiPlayer.getGame().getCombat();
        if (combat == null) {
            return new AiAbilityDecision(0, AiPlayDecision.AnotherTime);
        }
        Card choice = null;
        int highestEval = -1;
        if (combat.getAttackingPlayer().isOpponentOf(aiPlayer)) {
            for (Card attacker : combat.getAttackers()) {
                if (!sa.canTarget((GameObject)attacker)) continue;
                int eval = ComputerUtilCard.evaluateCreature(attacker);
                if (combat.isUnblocked(attacker)) {
                    eval += 100;
                }
                if (eval <= highestEval) continue;
                highestEval = eval;
                choice = attacker;
            }
        } else {
            for (Card blocker : combat.getAllBlockers()) {
                int eval;
                if (!sa.canTarget((GameObject)blocker) || !blocker.getController().isOpponentOf(aiPlayer) || (eval = ComputerUtilCard.evaluateCreature(blocker)) <= highestEval) continue;
                highestEval = eval;
                choice = blocker;
            }
        }
        if (choice != null) {
            sa.getTargets().add(choice);
            return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
        }
        return new AiAbilityDecision(0, AiPlayDecision.TargetingFailed);
    }

    public static Card doExilePreferenceLogic(Player aiPlayer, SpellAbility sa, CardCollection fetchList) {
        if (fetchList.isEmpty()) {
            return null;
        }
        Card host = sa.getHostCard();
        String logic = sa.getParamOrDefault("AILogic", "");
        String valid = logic.split(":")[1];
        boolean isCurse = logic.contains("Curse");
        boolean isOwnOnly = logic.contains("OwnOnly");
        boolean isWorstChoice = logic.contains("Worst");
        boolean isRandomChoice = logic.contains("Random");
        if (logic.endsWith("HighestCMC")) {
            return ComputerUtilCard.getMostExpensivePermanentAI((Iterable<Card>)fetchList);
        }
        if (logic.contains("MostProminent")) {
            CardCollection scanList = new CardCollection();
            if (logic.endsWith("OwnType")) {
                scanList.addAll((Collection)aiPlayer.getCardsIn(ZoneType.Library));
                scanList.addAll((Collection)aiPlayer.getCardsIn(ZoneType.Hand));
            } else if (logic.endsWith("OppType")) {
                scanList.addAll((Collection)aiPlayer.getOpponents().getCardsIn(ZoneType.Library));
                scanList.addAll((Collection)aiPlayer.getOpponents().getCardsIn(ZoneType.Hand));
            }
            if (logic.contains("NonLand")) {
                scanList = CardLists.filter((Iterable)scanList, (Predicate)CardPredicates.NON_LANDS);
            }
            if (logic.contains("NonExiled")) {
                CardCollection exiledBy = new CardCollection();
                for (Card exiled : aiPlayer.getGame().getCardsIn(ZoneType.Exile)) {
                    if (exiled.getExiledWith() == null || !exiled.getExiledWith().getName().equals(host.getName())) continue;
                    exiledBy.add(exiled);
                }
                scanList = CardLists.filter((Iterable)scanList, card -> {
                    if (exiledBy.isEmpty()) {
                        return true;
                    }
                    Iterator iterator = exiledBy.iterator();
                    if (iterator.hasNext()) {
                        Card c = (Card)iterator.next();
                        return !c.getType().sharesCardTypeWith(card.getType());
                    }
                    return true;
                });
            }
            Set presentTypes = aiPlayer.getGame().getCardsIn(ZoneType.Graveyard).stream().flatMap(inGrave -> inGrave.getType().getCoreTypes().stream()).collect(Collectors.toSet());
            CardType.CoreType determinedMaxType = scanList.stream().flatMap(c -> c.getType().getCoreTypes().stream()).filter(presentTypes::contains).collect(Collectors.groupingBy(ct -> ct, Collectors.counting())).entrySet().stream().max(Map.Entry.comparingByValue()).orElse(Map.entry(CardType.CoreType.Land, 0L)).getKey();
            CardCollection preferredList = CardLists.filter((Iterable)fetchList, card -> card.getType().hasType(determinedMaxType));
            CardCollection preferredOppList = CardLists.filter((Iterable)preferredList, (Predicate)CardPredicates.isControlledByAnyOf((FCollectionView)aiPlayer.getOpponents()));
            if (!preferredOppList.isEmpty()) {
                return (Card)Aggregates.random((Iterable)preferredOppList);
            }
            if (!preferredList.isEmpty()) {
                return (Card)Aggregates.random((Iterable)preferredList);
            }
            return (Card)Aggregates.random((Iterable)fetchList);
        }
        CardCollection preferredList = CardLists.filter((Iterable)fetchList, card -> {
            boolean playerPref = true;
            if (isCurse) {
                playerPref = card.getController().isOpponentOf(aiPlayer);
            } else if (isOwnOnly) {
                boolean bl = playerPref = card.getController().equals(aiPlayer) || !card.getController().isOpponentOf(aiPlayer);
            }
            if (!playerPref) {
                return false;
            }
            return card.isValid(valid, aiPlayer, host, (CardTraitBase)sa);
        });
        if (!preferredList.isEmpty()) {
            if (isRandomChoice) {
                return (Card)Aggregates.random((Iterable)preferredList);
            }
            return isWorstChoice ? ComputerUtilCard.getWorstAI((Iterable<Card>)preferredList) : ComputerUtilCard.getBestAI((Iterable<Card>)preferredList);
        }
        if (isRandomChoice) {
            return (Card)Aggregates.random((Iterable)preferredList);
        }
        return isWorstChoice ? ComputerUtilCard.getWorstAI((Iterable<Card>)fetchList) : ComputerUtilCard.getBestAI((Iterable<Card>)fetchList);
    }

    private static boolean doExileSpellLogic(Player ai, SpellAbility sa, boolean mandatory) {
        List<ApiType> dangerousApi = null;
        CardCollection spells = new CardCollection((Iterable)ai.getGame().getStackZone().getCards());
        Collections.reverse(spells);
        if (!mandatory && !spells.isEmpty()) {
            spells = spells.subList(0, 1);
            spells = ComputerUtil.filterAITgts(sa, ai, spells, true);
            dangerousApi = Arrays.asList(ApiType.DealDamage, ApiType.DamageAll, ApiType.Destroy, ApiType.DestroyAll, ApiType.Sacrifice, ApiType.SacrificeAll);
        }
        for (Card c : spells) {
            SpellAbility topSA = ai.getGame().getStack().getSpellMatchingHost(c);
            if (topSA == null || dangerousApi != null && (!dangerousApi.contains(topSA.getApi()) || !topSA.getActivatingPlayer().isOpponentOf(ai)) || !sa.canTarget((GameObject)topSA)) continue;
            sa.resetTargets();
            sa.getTargets().add((GameObject)topSA);
            return sa.isTargetNumberValid();
        }
        return false;
    }

    private static CardCollection getSafeTargetsIfUnlessCostPaid(Player ai, SpellAbility sa, Iterable<Card> potentialTgts) {
        Card source = sa.getHostCard();
        CardCollection canBeSaved = new CardCollection();
        for (Card potentialTgt : potentialTgts) {
            String unlessCost = sa.hasParam("UnlessCost") ? sa.getParam("UnlessCost").trim() : null;
            if (unlessCost == null || unlessCost.endsWith(">")) continue;
            Player opp = potentialTgt.getController();
            int usableManaSources = ComputerUtilMana.getAvailableManaEstimate(opp);
            int toPay = unlessCost.equals("X") && sa.getSVar(unlessCost).equals("Count$xPaid") ? ComputerUtilCost.setMaxXValue(sa, ai, true) : AbilityUtils.calculateAmount((Card)source, (String)unlessCost, (CardTraitBase)sa);
            if (toPay != 0 && toPay > usableManaSources) continue;
            canBeSaved.add(potentialTgt);
        }
        return canBeSaved;
    }

    private static void rememberBouncedThisTurn(Player ai, Card c) {
        AiCardMemory.rememberCard(ai, c, AiCardMemory.MemorySet.BOUNCED_THIS_TURN);
    }

    private static boolean isBouncedThisTurn(Player ai, Card c) {
        return AiCardMemory.isRememberedCard(ai, c, AiCardMemory.MemorySet.BOUNCED_THIS_TURN);
    }

    private static Card doBounceOwnTriggerLogic(Player ai, SpellAbility sa, CardCollection choices) {
        CardCollection unprefChoices = CardLists.filter((Iterable)choices, c -> !c.isToken() && c.getOwner().equals(ai));
        CardCollection prefChoices = CardLists.filter((Iterable)unprefChoices, c -> c.hasETBTrigger(false));
        if (!prefChoices.isEmpty()) {
            return ComputerUtilCard.getBestAI((Iterable<Card>)prefChoices);
        }
        if (!unprefChoices.isEmpty() && sa.getSubAbility() != null) {
            return ComputerUtilCard.getWorstAI((Iterable<Card>)unprefChoices);
        }
        return null;
    }

    private static Card considerRamp(Player ai, SpellAbility sa, CardCollection choices, Card keycardFound) {
        Card manaFixing;
        int manaProducers = 0;
        for (Card c : ai.getCardsIn(ZoneType.Battlefield)) {
            if (c.getManaAbilities().isEmpty()) continue;
            ++manaProducers;
        }
        int landsInHand = CardLists.filter((Iterable)ai.getCardsIn(ZoneType.Hand), (Predicate)CardPredicates.LANDS).size();
        int totalManaSources = manaProducers + landsInHand;
        int threshold = 4;
        if (keycardFound != null && keycardFound.getCMC() > totalManaSources + 1) {
            threshold = Math.max(threshold, keycardFound.getCMC() - 1);
        }
        if (totalManaSources < threshold && (manaFixing = ChangeZoneAi.basicManaFixing(ai, (List<Card>)choices)) != null) {
            return manaFixing;
        }
        return keycardFound;
    }

    @Override
    public boolean willPayUnlessCost(Player payer, SpellAbility sa, Cost cost, boolean alreadyPaid, FCollectionView<Player> payers) {
        Card host = sa.getHostCard();
        int lifeLoss = 0;
        if (cost.hasSpecificCostType(CostDamage.class)) {
            if (!payer.canLoseLife()) {
                return true;
            }
            CostDamage damageCost = (CostDamage)cost.getCostPartByType(CostDamage.class);
            lifeLoss = ComputerUtilCombat.predictDamageTo((GameEntity)payer, damageCost.getAbilityAmount(sa), host, false);
            if (lifeLoss == 0) {
                return true;
            }
        } else if (cost.hasSpecificCostType(CostPayLife.class)) {
            CostPayLife lifeCost = (CostPayLife)cost.getCostPartByType(CostPayLife.class);
            lifeLoss = lifeCost.getAbilityAmount(sa);
        }
        for (Card c : AbilityUtils.getDefinedCards((Card)host, (String)sa.getParam("Defined"), (CardTraitBase)sa)) {
            if (c.isToken()) {
                return false;
            }
            if (c.isCreature() && c.getBasePower() >= lifeLoss && payer.getLife() >= lifeLoss * 2) continue;
            return false;
        }
        return super.willPayUnlessCost(payer, sa, cost, alreadyPaid, payers);
    }

    private static boolean checkNearTermMana(int nearTermMana, Card c) {
        return c.getCMC() <= nearTermMana;
    }
}
