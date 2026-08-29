/*
 * Decompiled with CFR 0.152.
 * 
 * Could not load the following classes:
 *  com.google.common.collect.Iterables
 *  com.google.common.collect.Lists
 *  com.google.common.collect.Maps
 *  forge.StaticData
 *  forge.deck.CardPool
 *  forge.deck.Deck
 *  forge.game.CardTraitBase
 *  forge.game.Game
 *  forge.game.GameEntity
 *  forge.game.GameObject
 *  forge.game.ability.AbilityUtils
 *  forge.game.ability.ApiType
 *  forge.game.card.Card
 *  forge.game.card.CardCollection
 *  forge.game.card.CardCollectionView
 *  forge.game.card.CardCopyService
 *  forge.game.card.CardFactoryUtil
 *  forge.game.card.CardLists
 *  forge.game.card.CardPredicates
 *  forge.game.card.CounterEnumType
 *  forge.game.card.CounterType
 *  forge.game.combat.Combat
 *  forge.game.combat.CombatUtil
 *  forge.game.cost.Cost
 *  forge.game.cost.CostPayEnergy
 *  forge.game.cost.CostRemoveCounter
 *  forge.game.cost.CostSacrifice
 *  forge.game.cost.CostUntap
 *  forge.game.keyword.Keyword
 *  forge.game.keyword.KeywordCollection
 *  forge.game.keyword.KeywordInterface
 *  forge.game.phase.PhaseHandler
 *  forge.game.phase.PhaseType
 *  forge.game.player.Player
 *  forge.game.replacement.ReplacementEffect
 *  forge.game.replacement.ReplacementLayer
 *  forge.game.spellability.AbilitySub
 *  forge.game.spellability.SpellAbility
 *  forge.game.staticability.StaticAbility
 *  forge.game.staticability.StaticAbilityMode
 *  forge.game.trigger.Trigger
 *  forge.game.trigger.TriggerType
 *  forge.game.zone.MagicStack
 *  forge.game.zone.ZoneType
 *  forge.item.PaperCard
 *  forge.util.Aggregates
 *  forge.util.Expressions
 *  forge.util.IterableUtil
 *  forge.util.MyRandom
 *  forge.util.TextUtil
 *  org.apache.commons.lang3.StringUtils
 *  org.apache.commons.lang3.tuple.MutablePair
 *  org.apache.commons.lang3.tuple.Pair
 */
package forge.ai;

import com.google.common.collect.Iterables;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import forge.StaticData;
import forge.ai.AiAbilityDecision;
import forge.ai.AiAttackController;
import forge.ai.AiBlockController;
import forge.ai.AiCardMemory;
import forge.ai.AiController;
import forge.ai.AiPlayDecision;
import forge.ai.AiProfileUtil;
import forge.ai.AiProps;
import forge.ai.ComputerUtil;
import forge.ai.ComputerUtilAbility;
import forge.ai.ComputerUtilCombat;
import forge.ai.ComputerUtilCost;
import forge.ai.ComputerUtilMana;
import forge.ai.CreatureEvaluator;
import forge.ai.PlayerControllerAi;
import forge.ai.SpecialCardAi;
import forge.ai.SpellAbilityAi;
import forge.ai.simulation.GameStateEvaluator;
import forge.card.CardRules;
import forge.card.CardStateName;
import forge.card.CardType;
import forge.card.ColorSet;
import forge.card.MagicColor;
import forge.card.mana.ManaCost;
import forge.deck.CardPool;
import forge.deck.Deck;
import forge.game.CardTraitBase;
import forge.game.Game;
import forge.game.GameEntity;
import forge.game.GameObject;
import forge.game.ability.AbilityUtils;
import forge.game.ability.ApiType;
import forge.game.card.Card;
import forge.game.card.CardCollection;
import forge.game.card.CardCollectionView;
import forge.game.card.CardCopyService;
import forge.game.card.CardFactoryUtil;
import forge.game.card.CardLists;
import forge.game.card.CardPredicates;
import forge.game.card.CounterEnumType;
import forge.game.card.CounterType;
import forge.game.combat.Combat;
import forge.game.combat.CombatUtil;
import forge.game.cost.Cost;
import forge.game.cost.CostPayEnergy;
import forge.game.cost.CostRemoveCounter;
import forge.game.cost.CostSacrifice;
import forge.game.cost.CostUntap;
import forge.game.keyword.Keyword;
import forge.game.keyword.KeywordCollection;
import forge.game.keyword.KeywordInterface;
import forge.game.phase.PhaseHandler;
import forge.game.phase.PhaseType;
import forge.game.player.Player;
import forge.game.replacement.ReplacementEffect;
import forge.game.replacement.ReplacementLayer;
import forge.game.spellability.AbilitySub;
import forge.game.spellability.SpellAbility;
import forge.game.staticability.StaticAbility;
import forge.game.staticability.StaticAbilityMode;
import forge.game.trigger.Trigger;
import forge.game.trigger.TriggerType;
import forge.game.zone.MagicStack;
import forge.game.zone.ZoneType;
import forge.item.PaperCard;
import forge.util.Aggregates;
import forge.util.Expressions;
import forge.util.IterableUtil;
import forge.util.MyRandom;
import forge.util.TextUtil;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.HashMap;
import java.util.IdentityHashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;
import java.util.function.Predicate;
import java.util.stream.Collectors;
import java.util.stream.Stream;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.tuple.MutablePair;
import org.apache.commons.lang3.tuple.Pair;

public class ComputerUtilCard {
    public static final Comparator<SpellAbility> EvaluateCreatureSpellComparator = (a, b) -> ComputerUtilAbility.saEvaluator.compareEvaluator((SpellAbility)a, (SpellAbility)b, true);
    private static final CreatureEvaluator creatureEvaluator = new CreatureEvaluator();
    private static final LandEvaluator landEvaluator = new LandEvaluator();
    public static final Predicate<Deck> AI_KNOWS_HOW_TO_PLAY_ALL_CARDS = d -> {
        for (Map.Entry cp : d) {
            for (Map.Entry e : (CardPool)cp.getValue()) {
                if (!((PaperCard)e.getKey()).getRules().getAiHints().getRemAIDecks()) continue;
                return false;
            }
        }
        return true;
    };

    public static Card getMostExpensivePermanentAI(CardCollectionView list, SpellAbility spell, boolean targeted) {
        CardCollectionView all = list;
        if (targeted) {
            all = CardLists.filter((Iterable)all, c -> ((Card)c).canBeTargetedBy(spell));
        }
        return ComputerUtilCard.getMostExpensivePermanentAI((Iterable<Card>)all);
    }

    public static void sortByEvaluateCreature(CardCollection list) {
        list.sort(ComputerUtilCard.getCachedCreatureComparator().reversed());
    }

    public static Card getBestArtifactAI(List<Card> list) {
        return list.stream().filter(CardPredicates.ARTIFACTS).max(Comparator.comparing(Card::getCMC)).orElse(null);
    }

    public static Card getBestPlaneswalkerAI(List<Card> list) {
        return list.stream().filter(CardPredicates.PLANESWALKERS).max(Comparator.comparing(Card::getCMC)).orElse(null);
    }

    public static Card getWorstPlaneswalkerAI(List<Card> list) {
        return list.stream().filter(CardPredicates.PLANESWALKERS).min(Comparator.comparing(Card::getCMC)).orElse(null);
    }

    public static Card getBestPlaneswalkerToDamage(List<Card> pws) {
        Card bestTgt = null;
        int bestScore = 0;
        for (Card pw : pws) {
            int curLoyalty = pw.getCounters((CounterType)CounterEnumType.LOYALTY);
            int pwScore = curLoyalty * 10;
            for (SpellAbility sa : pw.getSpellAbilities()) {
                if (!sa.hasParam("Ultimate")) continue;
                Integer loyaltyCost = 0;
                CostRemoveCounter remLoyalty = (CostRemoveCounter)sa.getPayCosts().getCostPartByType(CostRemoveCounter.class);
                if (remLoyalty != null) {
                    loyaltyCost = remLoyalty.convertAmount();
                }
                if (loyaltyCost != null && loyaltyCost != 0 && loyaltyCost - curLoyalty <= 1) {
                    pwScore += 10000;
                }
                if (pwScore <= bestScore) continue;
                bestScore = pwScore;
                bestTgt = pw;
            }
        }
        return bestTgt;
    }

    public static Card getWorstPlaneswalkerToDamage(List<Card> pws) {
        Card bestTgt = null;
        int bestScore = Integer.MAX_VALUE;
        for (Card pw : pws) {
            int curLoyalty = pw.getCounters((CounterType)CounterEnumType.LOYALTY);
            if (curLoyalty >= bestScore) continue;
            bestScore = curLoyalty;
            bestTgt = pw;
        }
        return bestTgt;
    }

    public static Card getBestEnchantmentAI(List<Card> list, SpellAbility spell, boolean targeted) {
        Stream<Card> cardStream = list.stream().filter(CardPredicates.ENCHANTMENTS);
        if (targeted) {
            cardStream = cardStream.filter(c -> ((Card)c).canBeTargetedBy(spell));
        }
        return cardStream.max(Comparator.comparing(Card::getCMC)).orElse(null);
    }

    public static Card getBestLandAI(Iterable<Card> list) {
        CardCollection land = CardLists.filter(list, (Predicate)CardPredicates.LANDS);
        if (land.isEmpty()) {
            return null;
        }
        CardCollection nbLand = CardLists.filter((Iterable)land, (Predicate)CardPredicates.NONBASIC_LANDS);
        if (!nbLand.isEmpty()) {
            Card player = (Card)nbLand.get(0);
            CardCollectionView aiField = player.getController().getCardsIn(ZoneType.Battlefield);
            CardCollectionView aiHand = player.getController().getCardsIn(ZoneType.Hand);
            boolean hasMine = !CardLists.filter((Iterable)aiField, (Predicate)CardPredicates.nameEquals("Urza's Mine")).isEmpty() || !CardLists.filter((Iterable)aiHand, (Predicate)CardPredicates.nameEquals("Urza's Mine")).isEmpty();
            boolean hasTower = !CardLists.filter((Iterable)aiField, (Predicate)CardPredicates.nameEquals("Urza's Tower")).isEmpty() || !CardLists.filter((Iterable)aiHand, (Predicate)CardPredicates.nameEquals("Urza's Tower")).isEmpty();
            boolean hasPP = !CardLists.filter((Iterable)aiField, (Predicate)CardPredicates.nameEquals("Urza's Power Plant")).isEmpty() || !CardLists.filter((Iterable)aiHand, (Predicate)CardPredicates.nameEquals("Urza's Power Plant")).isEmpty();

            if (!hasMine && IterableUtil.any(list, (Predicate)CardPredicates.nameEquals("Urza's Mine"))) {
                return (Card)CardLists.filter((Iterable)nbLand, (Predicate)CardPredicates.nameEquals("Urza's Mine")).getFirst();
            }
            if (!hasTower && IterableUtil.any(list, (Predicate)CardPredicates.nameEquals("Urza's Tower"))) {
                return (Card)CardLists.filter((Iterable)nbLand, (Predicate)CardPredicates.nameEquals("Urza's Tower")).getFirst();
            }
            if (!hasPP && IterableUtil.any(list, (Predicate)CardPredicates.nameEquals("Urza's Power Plant"))) {
                return (Card)CardLists.filter((Iterable)nbLand, (Predicate)CardPredicates.nameEquals("Urza's Power Plant")).getFirst();
            }
            boolean fieldMine = !CardLists.filter((Iterable)aiField, (Predicate)CardPredicates.nameEquals("Urza's Mine")).isEmpty();
            boolean fieldTower = !CardLists.filter((Iterable)aiField, (Predicate)CardPredicates.nameEquals("Urza's Tower")).isEmpty();
            boolean fieldPP = !CardLists.filter((Iterable)aiField, (Predicate)CardPredicates.nameEquals("Urza's Power Plant")).isEmpty();
            if (!fieldMine && IterableUtil.any(list, (Predicate)CardPredicates.nameEquals("Urza's Mine"))) {
                return (Card)CardLists.filter((Iterable)nbLand, (Predicate)CardPredicates.nameEquals("Urza's Mine")).getFirst();
            }
            if (!fieldTower && IterableUtil.any(list, (Predicate)CardPredicates.nameEquals("Urza's Tower"))) {
                return (Card)CardLists.filter((Iterable)nbLand, (Predicate)CardPredicates.nameEquals("Urza's Tower")).getFirst();
            }
            if (!fieldPP && IterableUtil.any(list, (Predicate)CardPredicates.nameEquals("Urza's Power Plant"))) {
                return (Card)CardLists.filter((Iterable)nbLand, (Predicate)CardPredicates.nameEquals("Urza's Power Plant")).getFirst();
            }
            return (Card)nbLand.getFirst();
        }
        String sminBL = "";
        int iminBL = Integer.MAX_VALUE;
        int n = 0;
        for (String name : MagicColor.Constant.BASIC_LANDS) {
            n = CardLists.getType((Iterable)land, (String)name).size();
            if (n >= iminBL || n <= 0) continue;
            iminBL = n;
            sminBL = name;
        }
        if (iminBL == Integer.MAX_VALUE) {
            return land.stream().filter(CardPredicates.UNTAPPED).findFirst().orElse((Card)land.get(0));
        }
        CardCollection bLand = CardLists.getType((Iterable)land, (String)sminBL);
        return bLand.stream().filter(CardPredicates.UNTAPPED).findFirst().orElseGet(() -> ComputerUtilCard.lambda$getBestLandAI$2((List)bLand));
    }

    public static Card getBestLandToRemoveAI(Player ai, Iterable<Card> list, SpellAbility removal) {
        CardCollection lands = CardLists.filter(list, (Predicate)CardPredicates.LANDS);
        if (lands.isEmpty()) {
            return null;
        }
        return lands.stream().max(Comparator.comparingInt(c -> ComputerUtilCard.evaluateLandRemovalPriority(ai, c, removal))).orElse(null);
    }

    public static int evaluateLandRemovalPriority(Player ai, Card land, SpellAbility removal) {
        return ComputerUtilCard.evaluateLandRemovalPriority(ai, land, removal, true);
    }

    private static int evaluateLandRemovalPriority(Player ai, Card land, SpellAbility removal, boolean includeLandDestruction) {
        if (land == null || !land.isLand()) {
            return 0;
        }
        int score = Math.max(0, landEvaluator.apply(land) - 100);
        boolean hasAnimationAbility = false;
        for (SpellAbility ability : land.getNonManaAbilities()) {
            if (ability.isLandAbility()) continue;
            Cost cost = ability.getPayCosts();
            if (includeLandDestruction && ComputerUtilCard.isLandDestructionAbility(ability)) {
                if (!land.isTapped() || !ComputerUtilCard.aiHasHighPriorityLand(ai)) continue;
                score += 170;
                continue;
            }
            if (ComputerUtilCard.isHomewardPathAbility(ability)) {
                if (ai.getCreaturesInPlay().anyMatch(c -> c.getOwner() != ai)) {
                    score += 100;
                    continue;
                }
                score = Math.max(0, score - 50);
                continue;
            }
            if (ComputerUtilCard.isLandAnimationAbility(ability)) {
                hasAnimationAbility = true;
                score += ComputerUtilCard.isAttackingAi(land, ai) ? 140 : 70;
            } else if (cost != null && cost.hasSpecificCostType(CostSacrifice.class)) {
                score += 40;
            }
            if (ability.getApi() != ApiType.Mana && ability.findSubAbilityByType(ApiType.Mana) == null) continue;
            score += 100;
        }
        if (land.isCreature() && !hasAnimationAbility) {
            score += ComputerUtilCard.isAttackingAi(land, ai) ? 140 : 55;
        }
        if (land.hasSVar("AILandRemovalMinScore")) {
            score = Math.max(score, AbilityUtils.calculateAmount((Card)land, (String)land.getSVar("AILandRemovalMinScore"), null));
        }
        for (Card aura : land.getEnchantedBy()) {
            if (aura.getController().equals(land.getController()) && ComputerUtilCard.hasManaBoostingText(aura)) {
                score += 160;
            }
            if (!ComputerUtilCard.hasRemovedAiPermanent(ai, aura)) continue;
            score += 180;
        }
        return score;
    }

    private static boolean hasManaBoostingText(Card aura) {
        for (String value : aura.getSVars().values()) {
            if (!value.contains("DB$ Mana") && !value.contains("TapsForMana") && !value.contains("ManaReflected")) continue;
            return true;
        }
        for (Trigger trigger : aura.getTriggers()) {
            if (!TriggerType.TapsForMana.equals(trigger.getMode())) continue;
            return true;
        }
        return false;
    }

    private static boolean hasRemovedAiPermanent(Player ai, Card card) {
        for (Card exiled : card.getExiledCards()) {
            if (!exiled.getOwner().equals(ai) || !exiled.isPermanent()) continue;
            return true;
        }
        for (Object remembered : card.getRemembered()) {
            Card rememberedCard;
            if (!(remembered instanceof Card) || !(rememberedCard = (Card)remembered).getOwner().equals(ai) || !rememberedCard.isPermanent()) continue;
            return true;
        }
        return false;
    }

    private static boolean isLandDestructionAbility(SpellAbility ability) {
        if (ability.getApi() != ApiType.Destroy && ability.getApi() != ApiType.ChangeZone) {
            return false;
        }
        String valid = ability.getParamOrDefault("ValidTgts", "");
        if (valid.isEmpty()) {
            valid = ability.getParamOrDefault("ValidCards", "");
        }
        return valid.contains("Land");
    }

    private static boolean isHomewardPathAbility(SpellAbility ability) {
        return ability.getApi() == ApiType.GainControlVariant && "GainControlOwns".equals(ability.getParam("AILogic"));
    }

    private static boolean isLandAnimationAbility(SpellAbility ability) {
        if (ability.getApi() == ApiType.Animate) {
            return true;
        }
        String description = ability.getDescription();
        return description != null && description.contains("becomes") && description.contains("creature");
    }

    private static boolean isAttackingAi(Card land, Player ai) {
        Combat combat = land.getGame() == null ? null : land.getGame().getCombat();
        return combat != null && combat.isAttacking(land, (GameEntity)ai);
    }

    private static boolean aiHasHighPriorityLand(Player ai) {
        for (Card aiLand : ai.getLandsInPlay()) {
            if (ComputerUtilCard.evaluateLandRemovalPriority(ai, aiLand, null, false) < 150) continue;
            return true;
        }
        return false;
    }

    public static Card getWorstLand(List<Card> lands) {
        Card worstLand = null;
        int maxScore = Integer.MIN_VALUE;
        for (Card tmp : lands) {
            int score = tmp.isTapped() ? 2 : 0;
            score += tmp.isBasicLand() ? 1 : 0;
            score -= tmp.isCreature() ? 4 : 0;
            for (Card aura : tmp.getEnchantedBy()) {
                if (aura.getController().isOpponentOf(tmp.getController())) {
                    score += 5;
                    continue;
                }
                score -= 5;
            }
            if (score == maxScore && CardLists.count(lands, (Predicate)CardPredicates.sharesNameWith((Card)tmp)) > CardLists.count(lands, (Predicate)CardPredicates.sharesNameWith((Card)worstLand))) {
                worstLand = tmp;
            }
            if (score <= maxScore) continue;
            worstLand = tmp;
            maxScore = score;
        }
        return worstLand;
    }

    public static Card getBestLandToAnimate(Iterable<Card> lands) {
        Card land = null;
        int maxScore = Integer.MIN_VALUE;
        for (Card tmp : lands) {
            int score = tmp.isTapped() ? 0 : 2;
            score += tmp.isBasicLand() ? 2 : 0;
            score -= tmp.isCreature() ? 4 : 0;
            if ((score -= 5 * tmp.getEnchantedBy().size()) == maxScore && CardLists.count(lands, (Predicate)CardPredicates.sharesNameWith((Card)tmp)) > CardLists.count(lands, (Predicate)CardPredicates.sharesNameWith((Card)land))) {
                land = tmp;
            }
            if (score <= maxScore) continue;
            land = tmp;
            maxScore = score;
        }
        return land;
    }

    public static Card getCheapestPermanentAI(Iterable<Card> all, SpellAbility spell, boolean targeted) {
        if (targeted) {
            all = CardLists.filter(all, c -> ((Card)c).canBeTargetedBy(spell));
        }
        if (Iterables.isEmpty(all)) {
            return null;
        }
        Card cheapest = null;
        for (Card c2 : all) {
            if (cheapest != null && c2.getManaCost().getCMC() > cheapest.getManaCost().getCMC()) continue;
            cheapest = c2;
        }
        return cheapest;
    }

    public static Card getBestAI(Iterable<Card> list) {
        if (IterableUtil.all(list, (Predicate)CardPredicates.CREATURES)) {
            return ComputerUtilCard.getBestCreatureAI(list);
        }
        if (IterableUtil.all(list, (Predicate)CardPredicates.LANDS)) {
            return ComputerUtilCard.getBestLandAI(list);
        }
        return ComputerUtilCard.getMostExpensivePermanentAI(list);
    }

    public static Card getBestRemovalTargetAI(Player ai, Iterable<Card> list) {
        if (Iterables.isEmpty(list)) {
            return null;
        }
        return (Card)Aggregates.itemWithMax(list, c -> ComputerUtilCard.evaluateRemovalTargetPriority(ai, c));
    }

    private static int evaluateRemovalTargetPriority(Player ai, Card c) {
        int value;
        if (c.isCreature()) {
            value = ComputerUtilCard.evaluateCreature(c);
        } else if (c.isLand()) {
            value = ComputerUtilCard.evaluateLandRemovalPriority(ai, c, null, false);
        } else {
            value = 50 + 30 * c.getCMC();
            if (c.isPlaneswalker()) {
                value += c.getCounters((CounterType)CounterEnumType.LOYALTY) * 10;
            }
        }
        if (c.isToken()) {
            value += 30;
        }
        if (c.getController().isOpponentOf(ai)) {
            value += ComputerUtil.evaluateBoardPosition(ai, c.getController()) / 4;
        }
        return value;
    }

    public static Card getBestCreatureAI(Iterable<Card> list) {
        if (Iterables.size(list) == 1) {
            return (Card)Iterables.get(list, (int)0);
        }
        return (Card)Aggregates.itemWithMax((Iterable)IterableUtil.filter(list, (Predicate)CardPredicates.CREATURES), (Function)creatureEvaluator);
    }

    public static Card getBestLandToPlayAI(Iterable<Card> list) {
        if (Iterables.size(list) == 1) {
            return (Card)Iterables.get(list, (int)0);
        }
        return (Card)Aggregates.itemWithMax((Iterable)IterableUtil.filter(list, Card::hasPlayableLandFace), (Function)landEvaluator);
    }

    public static Card getWorstCreatureAI(Iterable<Card> list) {
        if (Iterables.size(list) == 1) {
            return (Card)Iterables.get(list, (int)0);
        }
        return (Card)Aggregates.itemWithMin((Iterable)IterableUtil.filter(list, (Predicate)CardPredicates.CREATURES), (Function)creatureEvaluator);
    }

    public static Card getBestCreatureToAttackNextTurnAI(Player aiPlayer, Iterable<Card> list) {
        AiController aic = ((PlayerControllerAi)aiPlayer.getController()).getAi();
        for (Card card : list) {
            if (!aic.getPredictedCombatNextTurn().isAttacking(card)) continue;
            return card;
        }
        return null;
    }

    public static Card getWorstAI(Iterable<Card> list) {
        return ComputerUtilCard.getWorstPermanentAI(list, false, false, false, false);
    }

    public static Card getWorstPermanentAI(Iterable<Card> list, boolean biasEnch, boolean biasLand, boolean biasArt, boolean biasCreature) {
        if (Iterables.isEmpty(list)) {
            return null;
        }
        boolean hasEnchantmants = IterableUtil.any(list, (Predicate)CardPredicates.ENCHANTMENTS);
        if (biasEnch && hasEnchantmants) {
            return ComputerUtilCard.getCheapestPermanentAI((Iterable<Card>)CardLists.filter(list, (Predicate)CardPredicates.ENCHANTMENTS), null, false);
        }
        boolean hasArtifacts = IterableUtil.any(list, (Predicate)CardPredicates.ARTIFACTS);
        if (biasArt && hasArtifacts) {
            return ComputerUtilCard.getCheapestPermanentAI((Iterable<Card>)CardLists.filter(list, (Predicate)CardPredicates.ARTIFACTS), null, false);
        }
        if (biasLand && IterableUtil.any(list, (Predicate)CardPredicates.LANDS)) {
            return ComputerUtilCard.getWorstLand((List<Card>)CardLists.filter(list, (Predicate)CardPredicates.LANDS));
        }
        boolean hasCreatures = IterableUtil.any(list, (Predicate)CardPredicates.CREATURES);
        if (biasCreature && hasCreatures) {
            return ComputerUtilCard.getWorstCreatureAI((Iterable<Card>)CardLists.filter(list, (Predicate)CardPredicates.CREATURES));
        }
        CardCollection lands = CardLists.filter(list, (Predicate)CardPredicates.LANDS);
        if (lands.size() > 6 || lands.size() == Iterables.size(list)) {
            return ComputerUtilCard.getWorstLand((List<Card>)lands);
        }
        if (hasEnchantmants || hasArtifacts) {
            CardCollection ae = CardLists.filter(list, CardPredicates.ARTIFACTS.or(CardPredicates.ENCHANTMENTS).and(card -> !card.hasSVar("DoNotDiscardIfAble")));
            return ComputerUtilCard.getCheapestPermanentAI((Iterable<Card>)ae, null, false);
        }
        if (hasCreatures) {
            return ComputerUtilCard.getWorstCreatureAI((Iterable<Card>)CardLists.filter(list, (Predicate)CardPredicates.CREATURES));
        }
        return ComputerUtilCard.getCheapestPermanentAI(list, null, false);
    }

    public static final Card getCheapestSpellAI(Iterable<Card> list) {
        if (!Iterables.isEmpty(list)) {
            CardCollection cc = CardLists.filter(list, (Predicate)CardPredicates.INSTANTS_AND_SORCERIES);
            if (cc.isEmpty()) {
                return null;
            }
            cc.sort(CardLists.CmcComparatorInv);
            Card cheapest = (Card)cc.getLast();
            if (cheapest.hasSVar("DoNotDiscardIfAble")) {
                for (int i = cc.size() - 1; i >= 0; --i) {
                    if (((Card)cc.get(i)).hasSVar("DoNotDiscardIfAble")) continue;
                    cheapest = (Card)cc.get(i);
                    break;
                }
            }
            return cheapest;
        }
        return null;
    }

    public static Comparator<Card> getCachedCreatureComparator() {
        IdentityHashMap cache = new IdentityHashMap();
        return Comparator.comparingInt(c -> (Integer)cache.computeIfAbsent((Card)c, creatureEvaluator));
    }

    public static int evaluateCreature(Card c) {
        return creatureEvaluator.evaluateCreature(c);
    }

    public static int evaluateCreature(Card c, boolean considerPT, boolean considerCMC) {
        return creatureEvaluator.evaluateCreature(c, considerPT, considerCMC);
    }

    public static int evaluateCreature(SpellAbility sa) {
        CardStateName currentState;
        Card host = sa.getHostCard();
        if (sa.getApi() != ApiType.PermanentCreature) {
            System.err.println("Warning: tried to evaluate a non-creature spell with evaluateCreature for card " + String.valueOf(host) + " via SA " + String.valueOf(sa));
            return 0;
        }
        CardStateName cardStateName = currentState = sa.getCardState() != null && host.getCurrentStateName() != sa.getCardStateName() && !host.isInPlay() ? host.getCurrentStateName() : null;
        if (currentState != null) {
            host.setState(sa.getCardStateName(), false);
        }
        int eval = ComputerUtilCard.evaluateCreature(host, true, false);
        if (currentState != null) {
            host.setState(currentState, false);
        }
        return eval;
    }

    public static int evaluatePermanentList(CardCollectionView list) {
        int value = 0;
        for (int i = 0; i < list.size(); ++i) {
            value += ((Card)list.get(i)).getCMC() + 1;
        }
        return value;
    }

    public static int evaluateCreatureList(CardCollectionView list) {
        return Aggregates.sum((Iterable)list, (Function)creatureEvaluator);
    }

    public static Map<String, Integer> evaluateCreatureListByName(CardCollectionView list) {
        return list.stream().collect(Collectors.groupingBy(Card::getName, Collectors.summingInt(c -> ComputerUtilCard.evaluateCreature(c))));
    }

    public static boolean doesCreatureAttackAI(Player aiPlayer, Card card) {
        AiController aic = ((PlayerControllerAi)aiPlayer.getController()).getAi();
        return aic.getPredictedCombat().isAttacking(card);
    }

    public static boolean doesSpecifiedCreatureAttackAI(Player ai, Card card) {
        AiAttackController aiAtk = new AiAttackController(ai, card);
        Combat combat = new Combat(ai);
        aiAtk.declareAttackers(combat);
        return combat.isAttacking(card);
    }

    public static CardCollectionView getLikelyBlockers(Player ai, CardCollectionView blockers) {
        AiBlockController aiBlk = new AiBlockController(ai, false);
        Player opp = AiAttackController.choosePreferredDefenderPlayer(ai);
        Combat combat = new Combat(opp);
        Combat currentCombat = ai.getGame().getCombat();
        if (currentCombat != null && currentCombat.getAttackingPlayer() != ai) {
            for (Card c : currentCombat.getAttackers()) {
                combat.addAttacker(c, (GameEntity)ai);
            }
        } else {
            for (Card c : opp.getCreaturesInPlay()) {
                if (!ComputerUtilCombat.canAttackNextTurn(c, (GameEntity)ai)) continue;
                combat.addAttacker(c, (GameEntity)ai);
            }
        }
        if (blockers == null || blockers.isEmpty()) {
            aiBlk.assignBlockersForCombat(combat);
        } else {
            aiBlk.assignAdditionalBlockers(combat, blockers);
        }
        return combat.getAllBlockers();
    }

    public static boolean doesSpecifiedCreatureBlock(Player ai, Card blocker) {
        return ComputerUtilCard.getLikelyBlockers(ai, (CardCollectionView)new CardCollection(blocker)).contains(blocker);
    }

    public static boolean canBeBlockedProfitably(Player ai, Card attacker, boolean checkingOther) {
        AiBlockController aiBlk = new AiBlockController(ai, checkingOther);
        Combat combat = new Combat(ai);
        attacker.setCombatLKI(null);
        combat.addAttacker(attacker, (GameEntity)ai);
        ArrayList attackers = Lists.newArrayList((Object[])new Card[]{attacker});
        aiBlk.assignBlockersGivenAttackers(combat, attackers);
        return ComputerUtilCombat.attackerWouldBeDestroyed(ai, attacker, combat);
    }

    public static boolean canBeKilledByRoyalAssassin(Player ai, Card card) {
        boolean wasTapped = card.isTapped();
        for (Player opp : ai.getOpponents()) {
            for (Card c : opp.getCardsIn(ZoneType.Battlefield)) {
                for (SpellAbility sa : c.getSpellAbilities()) {
                    if (sa.getApi() != ApiType.Destroy || !ComputerUtilCost.canPayCost(sa, opp, sa.isTrigger())) continue;
                    sa.setActivatingPlayer(opp);
                    if (sa.canTarget((GameObject)card)) continue;
                    card.setTapped(true);
                    if (!sa.canTarget((GameObject)card)) {
                        card.setTapped(wasTapped);
                        continue;
                    }
                    card.setTapped(wasTapped);
                    return true;
                }
            }
        }
        return false;
    }

    public static Card getMostExpensivePermanentAI(Iterable<Card> all) {
        Card biggest = null;
        int bigCMC = -1;
        for (Card card : all) {
            int curCMC = card.getCMC();
            if (card.isEnchanted()) {
                CardCollection auras = CardLists.filterControlledBy((Iterable)card.getEnchantedBy(), (Player)card.getController());
                curCMC += Aggregates.sum((Iterable<Card>)auras, (java.util.function.Function<Card, Integer>)Card::getCMC) + auras.size();
            }
            if (curCMC < bigCMC) continue;
            bigCMC = curCMC;
            biggest = card;
        }
        return biggest;
    }

    public static String getMostProminentCardName(CardCollectionView list) {
        if (list.size() == 0) {
            return "";
        }
        return list.stream().collect(Collectors.groupingBy(Card::getName, Collectors.counting())).entrySet().stream().max(Map.Entry.comparingByValue()).orElse(Map.entry("", 0L)).getKey();
    }

    public static String getMostProminentType(CardCollectionView list, Collection<String> valid) {
        return ComputerUtilCard.getMostProminentType(list, valid, true);
    }

    public static String getMostProminentType(CardCollectionView list, Collection<String> valid, boolean includeTokens) {
        if (list.isEmpty()) {
            return "";
        }
        HashMap typesInDeck = Maps.newHashMap();
        for (Card c : list) {
            if (!includeTokens && c.isToken() || c.getType().hasAllCreatureTypes()) continue;
            boolean isClone = false;
            for (ReplacementEffect re : c.getReplacementEffects()) {
                if (re.getLayer() != ReplacementLayer.Copy) continue;
                isClone = true;
                break;
            }
            if (isClone) continue;
            int weight = 1;
            if (c.isInZone(ZoneType.Hand) || c.isRealCommander()) {
                weight = 2;
            }
            Set<String> cardCreatureTypes = c.getType().getCreatureTypes();
            for (String type : cardCreatureTypes) {
                typesInDeck.merge(type, weight, (a, b) -> (Integer)a + (Integer)b);
            }
            if (!includeTokens) continue;
            if (c.getRules() != null) {
                for (String token : c.getRules().getTokens()) {
                    CardRules tokenCR = StaticData.instance().getAllTokens().getToken(token).getRules();
                    if (tokenCR == null) continue;
                    for (String type : tokenCR.getType().getCreatureTypes()) {
                        typesInDeck.merge(type, 1, (a, b) -> (Integer)a + (Integer)b);
                    }
                }
            }
            if (!c.hasKeyword(Keyword.FABRICATE)) continue;
            typesInDeck.merge("Servo", weight, (a, b) -> (Integer)a + (Integer)b);
        }
        int max = 0;
        String maxType = "";
        for (Map.Entry entry : (Iterable<Map.Entry>)typesInDeck.entrySet()) {
            String type = (String)entry.getKey();
            if (!valid.isEmpty() && !valid.contains(type) || max >= (Integer)entry.getValue()) continue;
            max = (Integer)entry.getValue();
            maxType = type;
        }
        return maxType;
    }

    public static CardType.CoreType getMostProminentCardType(CardCollectionView list, Collection<CardType.CoreType> valid) {
        if (list.isEmpty() || valid.isEmpty()) {
            return null;
        }
        Map.Entry result = list.stream().flatMap(c -> c.getType().getCoreTypes().stream()).filter(valid::contains).collect(Collectors.groupingBy(s -> s, Collectors.counting())).entrySet().stream().max(Map.Entry.comparingByValue()).orElse(null);
        return result == null ? null : (CardType.CoreType)(result.getKey());
    }

    public static String getMostProminentColor(Iterable<Card> list) {
        byte colors = CardFactoryUtil.getMostProminentColors(list);
        for (byte c : MagicColor.WUBRG) {
            if ((colors & c) == 0) continue;
            return MagicColor.toLongString(c);
        }
        return "white";
    }

    public static String getMostProminentColor(CardCollectionView list, Iterable<String> restrictedToColors) {
        byte colors = CardFactoryUtil.getMostProminentColorsFromList((CardCollectionView)list, restrictedToColors);
        for (byte c : MagicColor.WUBRG) {
            if ((colors & c) == 0) continue;
            return MagicColor.toLongString(c);
        }
        return (String)Iterables.get(restrictedToColors, (int)0);
    }

    public static List<String> getColorByProminence(List<Card> list) {
        int cntColors = MagicColor.WUBRG.length;
        ArrayList<Object> map = new ArrayList<Object>();
        for (int i = 0; i < cntColors; ++i) {
            map.add(MutablePair.of(MagicColor.WUBRG[i], 0));
        }
        for (Card crd : list) {
            ColorSet colorSet = crd.getColor();
            if (colorSet.hasWhite()) {
                ((Pair)map.get(0)).setValue(((Integer)((Pair)map.get(0)).getValue() + 1));
            }
            if (colorSet.hasBlue()) {
                ((Pair)map.get(1)).setValue(((Integer)((Pair)map.get(1)).getValue() + 1));
            }
            if (colorSet.hasBlack()) {
                ((Pair)map.get(2)).setValue(((Integer)((Pair)map.get(2)).getValue() + 1));
            }
            if (colorSet.hasRed()) {
                ((Pair)map.get(3)).setValue(((Integer)((Pair)map.get(3)).getValue() + 1));
            }
            if (!colorSet.hasGreen()) continue;
            ((Pair)map.get(4)).setValue(((Integer)((Pair)map.get(4)).getValue() + 1));
        }
        map.sort((p1, p2) -> Integer.compare(((Pair<Card, Integer>)p2).getValue(), ((Pair<Card, Integer>)p1).getValue()));
        ArrayList<String> result = new ArrayList<String>(cntColors);
        for (Object pairObj : map) { Pair pair = (Pair)pairObj;
            result.add(MagicColor.toLongString((Byte)(Object)pair.getKey()));
        }
        return result;
    }

    public static List<String> chooseColor(SpellAbility sa, int min, int max, List<String> colorChoices) {
        ArrayList<String> chosen = new ArrayList<String>();
        Player ai = sa.getActivatingPlayer();
        Game game = ai.getGame();
        Player opp = ai.getStrongestOpponent();
        if (sa.hasParam("AILogic")) {
            String logic = sa.getParam("AILogic");
            if (logic.equals("MostProminentInHumanDeck")) {
                chosen.add(ComputerUtilCard.getMostProminentColor((CardCollectionView)CardLists.filterControlledBy((Iterable)game.getCardsInGame(), (Player)opp), colorChoices));
            } else if (logic.equals("MostProminentInComputerDeck")) {
                chosen.add(ComputerUtilCard.getMostProminentColor((CardCollectionView)CardLists.filterControlledBy((Iterable)game.getCardsInGame(), (Player)ai), colorChoices));
            } else if (logic.equals("MostProminentDualInComputerDeck")) {
                List<String> prominence = ComputerUtilCard.getColorByProminence((List<Card>)CardLists.filterControlledBy((Iterable)game.getCardsInGame(), (Player)ai));
                chosen.add(prominence.get(0));
                chosen.add(prominence.get(1));
            } else if (logic.equals("MostProminentInGame")) {
                chosen.add(ComputerUtilCard.getMostProminentColor(game.getCardsInGame(), colorChoices));
            } else if (logic.equals("MostProminentHumanCreatures")) {
                CardCollection list = opp.getCreaturesInPlay();
                if (list.isEmpty()) {
                    list = CardLists.filter((Iterable)CardLists.filterControlledBy((Iterable)game.getCardsInGame(), (Player)opp), (Predicate)CardPredicates.CREATURES);
                }
                chosen.add(ComputerUtilCard.getMostProminentColor((CardCollectionView)list, colorChoices));
            } else if (logic.equals("MostProminentComputerControls")) {
                chosen.add(ComputerUtilCard.getMostProminentColor(ai.getCardsIn(ZoneType.Battlefield), colorChoices));
            } else if (logic.equals("MostProminentHumanControls")) {
                chosen.add(ComputerUtilCard.getMostProminentColor(opp.getCardsIn(ZoneType.Battlefield), colorChoices));
            } else if (logic.equals("MostProminentPermanent")) {
                chosen.add(ComputerUtilCard.getMostProminentColor(game.getCardsIn(ZoneType.Battlefield), colorChoices));
            } else if (logic.equals("MostProminentAttackers") && game.getPhaseHandler().inCombat()) {
                chosen.add(ComputerUtilCard.getMostProminentColor((CardCollectionView)game.getCombat().getAttackers(), colorChoices));
            } else if (logic.equals("MostProminentInActivePlayerHand")) {
                chosen.add(ComputerUtilCard.getMostProminentColor(game.getPhaseHandler().getPlayerTurn().getCardsIn(ZoneType.Hand), colorChoices));
            } else if (logic.equals("MostProminentInComputerDeckButGreen")) {
                List<String> prominence = ComputerUtilCard.getColorByProminence((List<Card>)CardLists.filterControlledBy((Iterable)game.getCardsInGame(), (Player)ai));
                if (prominence.get(0).equals("green")) {
                    chosen.add(prominence.get(1));
                } else {
                    chosen.add(prominence.get(0));
                }
            } else if (logic.equals("MostExcessOpponentControls")) {
                int maxExcess = 0;
                String bestColor = "green";
                for (byte color : MagicColor.WUBRG) {
                    CardCollectionView ailist = ai.getColoredCardsInPlay(color);
                    CardCollectionView opplist = opp.getColoredCardsInPlay(color);
                    int excess = ComputerUtilCard.evaluatePermanentList(opplist) - ComputerUtilCard.evaluatePermanentList(ailist);
                    if (excess <= maxExcess) continue;
                    maxExcess = excess;
                    bestColor = MagicColor.toLongString(color);
                }
                chosen.add(bestColor);
            } else if (logic.equals("MostProminentKeywordInComputerDeck")) {
                CardCollectionView list = ai.getAllCards();
                int m1 = 0;
                String chosenColor = "white";
                for (String c : MagicColor.Constant.ONLY_COLORS) {
                    int cmp = CardLists.filter((Iterable)list, (Predicate)CardPredicates.containsKeyword((String)c)).size();
                    if (cmp <= m1) continue;
                    m1 = cmp;
                    chosenColor = c;
                }
                chosen.add(chosenColor);
            } else if (logic.equals("HighestDevotionToColor")) {
                int curDevotion = 0;
                String chosenColor = "white";
                CardCollectionView hand = ai.getCardsIn(ZoneType.Hand);
                for (byte c : MagicColor.WUBRG) {
                    String devotionCode = "Count$Devotion." + MagicColor.toLongString(c);
                    int devotion = AbilityUtils.calculateAmount((Card)sa.getHostCard(), (String)devotionCode, (CardTraitBase)sa);
                    if (devotion <= curDevotion || !hand.anyMatch(CardPredicates.isColor((byte)c))) continue;
                    curDevotion = devotion;
                    chosenColor = MagicColor.toLongString(c);
                }
                chosen.add(chosenColor);
            }
        }
        if (chosen.isEmpty()) {
            chosen.add(ComputerUtilCard.getMostProminentColor(ai.getAllCards(), colorChoices));
        }
        return chosen;
    }

    public static boolean useRemovalNow(SpellAbility sa, Card c, int dmg, ZoneType destination) {
        float valueNow;
        float threat;
        float valueTempo;
        int costTarget;
        Player opp;
        block40: {
            block42: {
                Player ai;
                block41: {
                    block39: {
                        SpellAbility topStack;
                        MagicStack stack;
                        Combat combat;
                        Combat currCombat;
                        ai = sa.getActivatingPlayer();
                        Game game = ai.getGame();
                        PhaseHandler ph = game.getPhaseHandler();
                        PhaseType phaseType = ph.getPhase();
                        opp = ph.getPlayerTurn().isOpponentOf(ai) ? ph.getPlayerTurn() : ai.getStrongestOpponent();
                        int costRemoval = sa.getHostCard().getCMC();
                        costTarget = c.getCMC();
                        if (!sa.isSpell()) {
                            return true;
                        }
                        if (phaseType == PhaseType.MAIN1 && ComputerUtil.castSpellInMain1(ai, sa)) {
                            return true;
                        }
                        if (ph.is(PhaseType.MAIN1) && ph.isPlayerTurn(ai) && c.isCreature()) {
                            AiAttackController aiAtk = new AiAttackController(ai);
                            Combat combat2 = new Combat(ai);
                            aiAtk.removeBlocker(c);
                            aiAtk.declareAttackers((Combat)combat2);
                            if (!combat2.getAttackers().isEmpty()) {
                                AiAttackController aiAtk2 = new AiAttackController(ai);
                                Combat combat22 = new Combat(ai);
                                aiAtk2.declareAttackers(combat22);
                                if (combat2.getAttackers().size() > combat22.getAttackers().size()) {
                                    return true;
                                }
                            }
                        }
                        if (ph.is(PhaseType.COMBAT_DECLARE_BLOCKERS) && !ph.isPlayerTurn(ai) && (currCombat = game.getCombat()) != null && !currCombat.getAllBlockers().isEmpty() && currCombat.getAllBlockers().contains(c)) {
                            for (Card attacker : currCombat.getAttackersBlockedBy(c)) {
                                if (attacker.getShieldCount() != 0 || !ComputerUtilCombat.attackerWouldBeDestroyed(ai, attacker, currCombat)) continue;
                                CardCollection blockers = currCombat.getBlockers(attacker);
                                ComputerUtilCard.sortByEvaluateCreature(blockers);
                                combat = new Combat(ai);
                                combat.addAttacker(attacker, (GameEntity)opp);
                                for (Card blocker : blockers) {
                                    if (blocker == c) continue;
                                    combat.addBlocker(attacker, blocker);
                                }
                                if (ComputerUtilCombat.attackerWouldBeDestroyed(ai, attacker, combat)) continue;
                                return true;
                            }
                        }
                        if (c.isEnchanted()) {
                            boolean myEnchants = false;
                            for (Card enc : c.getEnchantedBy()) {
                                if (!enc.getOwner().equals(ai)) continue;
                                myEnchants = true;
                                break;
                            }
                            if (!myEnchants) {
                                return true;
                            }
                        }
                        if (!(stack = game.getStack()).isEmpty() && (topStack = stack.peekAbility()).getActivatingPlayer().equals(opp) && c.equals(topStack.getTargetCard()) && topStack.isSpell()) {
                            return true;
                        }
                        float valueBurn = 0.0f;
                        if (dmg > 0) {
                            if (sa.getDescription().contains("would die, exile it instead")) {
                                destination = ZoneType.Exile;
                            }
                            valueBurn = 1.0f * (float)c.getNetToughness() / (float)dmg;
                            valueBurn *= valueBurn;
                            if (sa.getTargetRestrictions().canTgtPlayer()) {
                                valueBurn /= 2.0f;
                            }
                            if ((double)valueBurn >= 0.8 && phaseType.isBefore(PhaseType.COMBAT_END)) {
                                return true;
                            }
                        }
                        valueTempo = Math.max(0.1f * (float)costTarget / (float)costRemoval, valueBurn);
                        if (c.isEquipped()) {
                            valueTempo *= 2.0f;
                        }
                        if (SpellAbilityAi.isSorcerySpeed(sa, ai)) {
                            valueTempo *= 2.0f;
                        }
                        if (!c.canBeDestroyed()) {
                            valueTempo *= 2.0f;
                        }
                        if (!destination.equals(ZoneType.Graveyard) && c.hasKeyword(Keyword.PERSIST) || c.hasKeyword(Keyword.UNDYING) || c.hasKeyword(Keyword.MODULAR)) {
                            valueTempo *= 2.0f;
                        }
                        if (destination.equals(ZoneType.Hand) && !c.isToken()) {
                            valueTempo /= 2.0f;
                        }
                        if (c.isLand()) {
                            valueTempo += 0.5f / (float)opp.getLandsInPlay().size();
                            if ("Land".equals(sa.getParam("ValidTgts")) && ph.getPhase().isAfter(PhaseType.COMBAT_END)) {
                                valueTempo = (float)((double)valueTempo + 0.5);
                            }
                        }
                        if (!ph.isPlayerTurn(ai) && ph.getPhase().equals(PhaseType.END_OF_TURN)) {
                            valueTempo *= 2.0f;
                        }
                        if ((double)valueTempo >= 0.8 && ph.getPhase().isBefore(PhaseType.COMBAT_END)) {
                            return true;
                        }
                        threat = 0.0f;
                        if (!c.isCreature()) break block39;
                        threat += (-1.0f + 1.0f * (float)ComputerUtilCard.evaluateCreature(c) / 100.0f) / (float)costRemoval;
                        if (ai.getLife() > 0 && ComputerUtilCombat.canAttackNextTurn(c)) {
                            combat = game.getCombat();
                            threat += 1.0f * (float)ComputerUtilCombat.damageIfUnblocked(c, (GameEntity)ai, combat, true) / (float)ai.getLife();
                        }
                        if (ph.isPlayerTurn(ai) && phaseType.isAfter(PhaseType.COMBAT_DECLARE_BLOCKERS)) {
                            threat *= 0.1f;
                        }
                        if (!ph.isPlayerTurn(ai) && (phaseType.isBefore(PhaseType.COMBAT_BEGIN) || phaseType.isAfter(PhaseType.COMBAT_DECLARE_BLOCKERS))) {
                            threat *= 0.1f;
                        }
                        break block40;
                    }
                    if (!c.isPlaneswalker()) break block41;
                    threat = 1.0f;
                    break block40;
                }
                if (!AiProfileUtil.getBoolProperty(ai, AiProps.ACTIVELY_DESTROY_ARTS_AND_NONAURA_ENCHS) || (!c.isArtifact() || c.isCreature()) && (!c.isEnchantment() || c.isAura())) break block42;
                boolean priority = false;
                if (!c.getOwner().isOpponentOf(ai) || !c.getController().isOpponentOf(ai)) break block40;
                for (StaticAbility stAb : c.getStaticAbilities()) {
                    if (!stAb.checkMode(StaticAbilityMode.Continuous) || !stAb.isIntrinsic()) continue;
                    priority = true;
                    break;
                }
                if (!priority) {
                    for (Trigger t : c.getTriggers()) {
                        if (!t.isIntrinsic()) continue;
                        priority = true;
                        break;
                    }
                }
                if (!priority) {
                    for (String value : c.getSVars().values()) {
                        if (!value.contains("AILogic$ Curse")) continue;
                        priority = true;
                        break;
                    }
                }
                if (!priority) break block40;
                threat = 1.0f;
                break block40;
            }
            for (StaticAbility stAb : c.getStaticAbilities()) {
                String kws;
                if (!stAb.checkMode(StaticAbilityMode.Continuous) || !"Creature.YouCtrl".equals(stAb.getParam("Affected"))) continue;
                int bonusPT = 0;
                if (stAb.hasParam("AddPower")) {
                    bonusPT += AbilityUtils.calculateAmount((Card)c, (String)stAb.getParam("AddPower"), (CardTraitBase)stAb);
                }
                if (stAb.hasParam("AddToughness")) {
                    bonusPT += AbilityUtils.calculateAmount((Card)c, (String)stAb.getParam("AddPower"), (CardTraitBase)stAb);
                }
                if ((kws = stAb.getParam("AddKeyword")) != null) {
                    bonusPT += 4 * (1 + StringUtils.countMatches((CharSequence)kws, (CharSequence)"&"));
                }
                if (bonusPT <= 0) continue;
                threat = (float)(bonusPT * (1 + opp.getCreaturesInPlay().size())) / 10.0f;
            }
        }
        if (!c.getManaAbilities().isEmpty() && !ComputerUtilCard.landGrantingRemoval(sa)) {
            threat += 0.5f * (float)costTarget / (float)opp.getLandsInPlay().size();
        }
        if ((double)(valueNow = Math.max(valueTempo, threat)) < 0.2) {
            return false;
        }
        float chance = MyRandom.getRandom().nextFloat();
        return chance < valueNow;
    }

    private static boolean landGrantingRemoval(SpellAbility sa) {
        for (AbilitySub sub = sa.getSubAbility(); sub != null; sub = sub.getSubAbility()) {
            if (!ApiType.ChangeZone.equals(sub.getApi()) || !"Library".equals(sub.getParamOrDefault("Origin", "")) || !"Battlefield".equals(sub.getParamOrDefault("Destination", "")) || !sub.getParamOrDefault("ChangeType", "").contains("Land.Basic") || !"TargetedController".equals(sub.getParamOrDefault("DefinedPlayer", ""))) continue;
            return true;
        }
        return false;
    }

    public static boolean shouldPumpCard(Player ai, SpellAbility sa, Card c, int toughness, int power, List<String> keywords) {
        return ComputerUtilCard.shouldPumpCard(ai, sa, c, toughness, power, keywords, false);
    }

    public static boolean shouldPumpCard(Player ai, SpellAbility sa, Card c, int toughness, int power, List<String> keywords, boolean immediately) {
        boolean isHeldCombatTrick;
        boolean wantToHoldTrick;
        AiController aic;
        Game game = ai.getGame();
        PhaseHandler phase = game.getPhaseHandler();
        Combat combat = phase.getCombat();
        boolean main1Preferred = "Main1IfAble".equals(sa.getParam("AILogic")) && phase.is(PhaseType.MAIN1, ai);
        boolean isBerserk = "Berserk".equals(sa.getParam("AILogic"));
        boolean loseCardAtEOT = "Sacrifice".equals(sa.getParam("AtEOT")) || "Exile".equals(sa.getParam("AtEOT")) || "Destroy".equals(sa.getParam("AtEOT")) || "ExileCombat".equals(sa.getParam("AtEOT"));
        boolean combatTrick = false;
        boolean holdCombatTricks = false;
        int chanceToHoldCombatTricks = -1;
        boolean simAI = false;
        if (ai.getController().isAI() && !(simAI = (aic = ((PlayerControllerAi)ai.getController()).getAi()).usesFullSimulation())) {
            holdCombatTricks = aic.getBoolProperty(AiProps.TRY_TO_HOLD_COMBAT_TRICKS_UNTIL_BLOCK);
            chanceToHoldCombatTricks = aic.getIntProperty(AiProps.CHANCE_TO_HOLD_COMBAT_TRICKS_UNTIL_BLOCK);
        }
        if (!c.canBeTargetedBy(sa)) {
            return false;
        }
        if (c.getNetToughness() + toughness <= 0) {
            return false;
        }
        if (sa.getHostCard().equals(c) && ComputerUtilCost.isSacrificeSelfCost(sa.getPayCosts())) {
            return false;
        }
        if (phase.getPhase().isBefore(PhaseType.COMBAT_DECLARE_ATTACKERS) && phase.isPlayerTurn(ai) && (SpellAbilityAi.isSorcerySpeed(sa, ai) || main1Preferred) && power > 0 && ComputerUtilCard.doesCreatureAttackAI(ai, c)) {
            return true;
        }
        if (immediately && phase.getPhase().isBefore(PhaseType.COMBAT_DECLARE_BLOCKERS) && !loseCardAtEOT && (phase.isPlayerTurn(ai) ? CombatUtil.canAttack((Card)c) || phase.inCombat() && c.isAttacking() : CombatUtil.canBlock((Card)c))) {
            return true;
        }
        if (keywords.contains("Banding") && !c.hasKeyword(Keyword.BANDING)) {
            if (phase.is(PhaseType.COMBAT_BEGIN) && phase.isPlayerTurn(ai) && !ComputerUtilCard.doesCreatureAttackAI(ai, c)) {
                Card bandingCard = ComputerUtilCard.getPumpedCreature(ai, sa, c, toughness, power, keywords);
                AiAttackController aiAtk = new AiAttackController(ai);
                Combat predicted = new Combat(ai);
                aiAtk.declareAttackers(predicted);
                aiAtk.reinforceWithBanding(predicted, (Card)bandingCard);
                if (predicted.isAttacking((Card)bandingCard) && predicted.getBandOfAttacker((Card)bandingCard).getAttackers().size() > 1) {
                    return true;
                }
            } else if (phase.is(PhaseType.COMBAT_DECLARE_BLOCKERS) && combat != null) {
                for (Card atk : combat.getAttackers()) {
                    if (!atk.getController().isOpponentOf(ai)) continue;
                    CardCollection blockers = combat.getBlockers(atk);
                    boolean hasBanding = false;
                    for (Object blocker : blockers) {
                        if (!((Card)blocker).hasKeyword(Keyword.BANDING)) continue;
                        hasBanding = true;
                        break;
                    }
                    if (hasBanding || (!blockers.contains(c) || blockers.size() <= 1) && !atk.hasKeyword(Keyword.TRAMPLE)) continue;
                    return true;
                }
            }
        }
        Player opp = ai.getWeakestOpponent();
        Card pumped = ComputerUtilCard.getPumpedCreature(ai, sa, c, toughness, power, keywords);
        CardCollection oppCreatures = opp.getCreaturesInPlay();
        float chance = 0.0f;
        if (phase.getPhase().isBefore(PhaseType.COMBAT_DECLARE_ATTACKERS) && phase.isPlayerTurn(ai) && opp.getLife() > 0) {
            if (!ComputerUtilCard.doesCreatureAttackAI(ai, c) && ComputerUtilCard.doesSpecifiedCreatureAttackAI(ai, pumped)) {
                float threat = 1.0f * (float)ComputerUtilCombat.damageIfUnblocked(pumped, (GameEntity)opp, combat, true) / (float)opp.getLife();
                if (oppCreatures.stream().noneMatch(CardPredicates.possibleBlockers((Card)pumped))) {
                    threat *= 2.0f;
                }
                if (c.getNetPower() == 0 && c == sa.getHostCard() && power > 0) {
                    threat *= 4.0f;
                }
                chance += threat;
                if (holdCombatTricks && sa.getApi() == ApiType.Pump && sa.hasParam("NumAtt") && sa.getHostCard() != null && sa.getHostCard().isInZone(ZoneType.Hand) && c.getNetPower() > 0 && sa.getHostCard().isInstant() && ComputerUtilMana.hasEnoughManaSourcesToCast(sa, ai)) {
                    combatTrick = true;
                    for (String kw : keywords) {
                        if (kw.equals("Trample") || kw.equals("First Strike") || kw.equals("Double Strike")) continue;
                        combatTrick = false;
                        break;
                    }
                }
            }
            if (keywords.contains("Haste") && c.hasSickness() && !c.isTapped()) {
                double nonCombatChance = 0.0;
                double combatChance = 0.0;
                if (c.isAbilitySick()) {
                    for (SpellAbility ab : c.getSpellAbilities()) {
                        Cost abCost = ab.getPayCosts();
                        if (abCost == null || !abCost.hasTapCost() && !abCost.hasSpecificCostType(CostUntap.class) || abCost.hasManaCost() && !ComputerUtilMana.canPayManaCost(ab, ai, sa.getPayCosts().getTotalMana().getCMC(), false)) continue;
                        nonCombatChance += 0.5;
                        break;
                    }
                }
                if (ComputerUtilCard.doesSpecifiedCreatureAttackAI(ai, pumped)) {
                    combatChance += (double)(0.5f + 0.5f * (float)ComputerUtilCombat.damageIfUnblocked(pumped, (GameEntity)opp, combat, true) / (float)opp.getLife());
                }
                chance = (float)((double)chance + (nonCombatChance + combatChance));
            }
            if (oppCreatures.stream().anyMatch(CardPredicates.possibleBlockers((Card)c)) && oppCreatures.stream().noneMatch(CardPredicates.possibleBlockers((Card)pumped)) && ComputerUtilCard.doesSpecifiedCreatureAttackAI(ai, pumped)) {
                chance += 0.5f * (float)ComputerUtilCombat.damageIfUnblocked(pumped, (GameEntity)opp, combat, true) / (float)opp.getLife();
            }
        }
        if (phase.is(PhaseType.COMBAT_DECLARE_BLOCKERS)) {
            Combat pumpedCombat = new Combat(phase.isPlayerTurn(ai) ? ai : opp);
            CardCollection opposing = null;
            boolean pumpedWillDie = false;
            boolean isAttacking = combat.isAttacking(c);
            if (isBerserk && isAttacking || loseCardAtEOT) {
                pumpedWillDie = true;
            }
            if (isAttacking) {
                pumpedCombat.addAttacker(pumped, (GameEntity)opp);
                opposing = combat.getBlockers(c);
                for (Card b : opposing) {
                    pumpedCombat.addBlocker(pumped, b);
                }
                if (ComputerUtilCombat.attackerWouldBeDestroyed(ai, pumped, pumpedCombat)) {
                    pumpedWillDie = true;
                }
            } else {
                opposing = combat.getAttackersBlockedBy(c);
                for (Object a : opposing) {
                    pumpedCombat.addAttacker((Card)a, (GameEntity)ai);
                    pumpedCombat.addBlocker((Card)a, pumped);
                }
                if (ComputerUtilCombat.blockerWouldBeDestroyed(ai, pumped, pumpedCombat)) {
                    pumpedWillDie = true;
                }
            }
            if (ComputerUtilCombat.combatantWouldBeDestroyed(ai, c, combat) && !pumpedWillDie && !c.hasKeyword(Keyword.INDESTRUCTIBLE)) {
                return true;
            }
            boolean survivor = false;
            for (Card o : opposing) {
                if (ComputerUtilCombat.combatantWouldBeDestroyed(opp, o, combat)) continue;
                survivor = true;
                break;
            }
            if (survivor) {
                for (Card o : opposing) {
                    if (ComputerUtilCombat.combatantWouldBeDestroyed(opp, o, combat) || o.hasSVar("SacMe") && Integer.parseInt(o.getSVar("SacMe")) > 2 || !(isAttacking ? ComputerUtilCombat.blockerWouldBeDestroyed(opp, o, pumpedCombat) : ComputerUtilCombat.attackerWouldBeDestroyed(opp, o, pumpedCombat))) continue;
                    return true;
                }
            }
            if (combat.isAttacking(c) && opp.getLife() > 0) {
                int dmg = ComputerUtilCombat.damageIfUnblocked(c, (GameEntity)opp, combat, true);
                int pumpedDmg = ComputerUtilCombat.damageIfUnblocked(pumped, (GameEntity)opp, pumpedCombat, true);
                int poisonOrig = ComputerUtilCombat.poisonIfUnblocked(c, ai);
                int poisonPumped = ComputerUtilCombat.poisonIfUnblocked(pumped, ai);
                if (pumpedDmg == 0 && c.hasKeyword(Keyword.INFECT) && poisonPumped > poisonOrig) {
                    pumpedDmg = poisonPumped;
                }
                if (combat.isBlocked(c)) {
                    if (!c.hasKeyword(Keyword.TRAMPLE)) {
                        dmg = 0;
                    }
                    if (c.hasKeyword(Keyword.TRAMPLE) || keywords.contains("Trample")) {
                        for (Object b : combat.getBlockers(c)) {
                            pumpedDmg -= ComputerUtilCombat.getDamageToKill((Card)b, false);
                        }
                    } else {
                        pumpedDmg = 0;
                    }
                }
                if (pumpedDmg > dmg) {
                    if (!c.hasKeyword(Keyword.INFECT) && pumpedDmg >= opp.getLife() || c.hasKeyword(Keyword.INFECT) && opp.canReceiveCounters((CounterType)CounterEnumType.POISON) && pumpedDmg >= opp.getPoisonCounters() || "PumpForTrample".equals(sa.getParam("AILogic"))) {
                        return true;
                    }
                    if (phase.is(PhaseType.COMBAT_DECLARE_BLOCKERS)) {
                        int totalPowerUnblocked = 0;
                        for (Card atk : combat.getAttackers()) {
                            if (combat.isBlocked(atk) && !atk.hasKeyword(Keyword.TRAMPLE)) continue;
                            if (atk == c) {
                                totalPowerUnblocked += pumpedDmg;
                                continue;
                            }
                            totalPowerUnblocked += ComputerUtilCombat.damageIfUnblocked(atk, (GameEntity)opp, combat, true);
                            if (!combat.isBlocked(atk)) continue;
                            for (Card blk : combat.getBlockers(atk)) {
                                totalPowerUnblocked -= ComputerUtilCombat.getDamageToKill(blk, false);
                            }
                        }
                        if (totalPowerUnblocked >= opp.getLife()) {
                            return true;
                        }
                        if (totalPowerUnblocked > dmg && sa.getHostCard() != null && sa.getHostCard().isInPlay() && sa.getPayCosts().hasNoManaCost()) {
                            return true;
                        }
                    }
                }
                float value = pumpedDmg - dmg;
                if (c == sa.getHostCard() && power > 0) {
                    int divisor = sa.getPayCosts().getTotalMana().getCMC();
                    if (divisor <= 0) {
                        divisor = 1;
                    }
                    value *= (float)power / (float)divisor;
                } else {
                    value /= (float)opp.getLife();
                }
                chance += value;
            }
            if (ai.canGainLife() && ai.getLife() > 0 && !c.hasKeyword(Keyword.LIFELINK) && keywords.contains("Lifelink") && (combat.isAttacking(c) || combat.isBlocking(c))) {
                int dmg = pumped.getNetCombatDamage();
                chance += 1.0f * (float)dmg / (float)ai.getLife();
            }
            if (combat.isBlocking(c) && toughness > 0) {
                CardCollection blockedBy = combat.getAttackersBlockedBy(c);
                boolean attackerHasTrample = false;
                for (Card b : blockedBy) {
                    attackerHasTrample |= b.hasKeyword(Keyword.TRAMPLE);
                }
                if (attackerHasTrample && (sa.isAbility() || ComputerUtilCombat.lifeInDanger(ai, combat))) {
                    return true;
                }
            }
        }
        if ("UntapCombatTrick".equals(sa.getParam("AILogic")) && c.isTapped()) {
            if (phase.is(PhaseType.COMBAT_DECLARE_ATTACKERS) && phase.getPlayerTurn().isOpponentOf(ai)) {
                chance += 0.5f;
            } else if (phase.is(PhaseType.COMBAT_DECLARE_BLOCKERS, ai)) {
                chance += 1.0f;
            }
        }
        if (isBerserk && ai.getController() instanceof PlayerControllerAi) {
            boolean aggr;
            boolean bl = aggr = ((PlayerControllerAi)ai.getController()).getAi().getBoolProperty(AiProps.USE_BERSERK_AGGRESSIVELY) || sa.hasParam("AtEOT");
            if (!aggr) {
                return false;
            }
        }
        boolean bl = wantToHoldTrick = holdCombatTricks && !ai.getCardsIn(ZoneType.Hand).isEmpty();
        wantToHoldTrick = chanceToHoldCombatTricks >= 0 ? (wantToHoldTrick &= MyRandom.percentTrue((int)chanceToHoldCombatTricks)) : (wantToHoldTrick &= MyRandom.getRandom().nextFloat() < chance);
        boolean bl2 = isHeldCombatTrick = combatTrick && wantToHoldTrick;
        if (isHeldCombatTrick) {
            if (AiCardMemory.isMemorySetEmpty(ai, AiCardMemory.MemorySet.TRICK_ATTACKERS)) {
                boolean reserved = false;
                if (ai.getController().isAI() && (reserved = ((PlayerControllerAi)ai.getController()).getAi().reserveManaSources(sa, PhaseType.COMBAT_DECLARE_BLOCKERS, false))) {
                    AiCardMemory.rememberCard(ai, c, AiCardMemory.MemorySet.MANDATORY_ATTACKERS);
                    AiCardMemory.rememberCard(ai, c, AiCardMemory.MemorySet.TRICK_ATTACKERS);
                    return false;
                }
            } else {
                return false;
            }
        }
        return simAI || MyRandom.getRandom().nextFloat() < chance;
    }

    public static Card getPumpedCreature(Player ai, SpellAbility sa, Card c, int toughness, int power, List<String> keywords) {
        Card pumped = new CardCopyService(c).copyCard(false);
        pumped.setSickness(c.hasSickness());
        long timestamp = c.getGame().getNextTimestamp();
        ArrayList kws = Lists.newArrayList();
        ArrayList hiddenKws = Lists.newArrayList();
        for (String kw : keywords) {
            if (kw.startsWith("HIDDEN")) {
                hiddenKws.add(kw.substring(7));
                continue;
            }
            kws.add(kw);
        }
        boolean isBerserk = "Berserk".equals(sa.getParam("AILogic"));
        int berserkPower = 0;
        if (isBerserk && sa.hasSVar("X")) {
            berserkPower = "Targeted$CardPower".equals(sa.getSVar("X")) ? c.getCurrentPower() : AbilityUtils.calculateAmount((Card)sa.getHostCard(), (String)"X", (CardTraitBase)sa);
        }
        for (SpellAbility ab : c.getSpellAbilities()) {
            if (!"Pummeler".equals(ab.getParam("AILogic"))) continue;
            Pair<Integer, Integer> newPT = SpecialCardAi.ElectrostaticPummeler.getPumpedPT(ai, power, toughness);
            power = (Integer)newPT.getLeft();
            toughness = (Integer)newPT.getRight();
        }
        pumped.addNewPT(Integer.valueOf(c.getCurrentPower()), Integer.valueOf(c.getCurrentToughness()), timestamp, 0L);
        pumped.setPTBoost(c.getPTBoostTable());
        pumped.addPTBoost(power + berserkPower, toughness, timestamp, 0L);
        if (!kws.isEmpty()) {
            pumped.addChangedCardKeywords((List)kws, null, false, timestamp, null, false);
        }
        if (!hiddenKws.isEmpty()) {
            pumped.addHiddenExtrinsicKeywords(timestamp, 0L, (Iterable)hiddenKws);
        }
        pumped.setCounters(c.getCounters());
        if (c.isTapped()) {
            pumped.setTapped(true);
        }
        KeywordCollection copiedKeywords = new KeywordCollection();
        copiedKeywords.insertAll((Iterable)pumped.getKeywords());
        ArrayList toCopy = Lists.newArrayList();
        for (KeywordInterface k : c.getUnhiddenKeywords()) {
            KeywordInterface copiedKI = k.copy(c, true);
            if (copiedKeywords.contains(copiedKI.getOriginal())) continue;
            toCopy.add(copiedKI);
        }
        long timestamp2 = c.getGame().getNextTimestamp();
        pumped.addChangedCardKeywordsInternal((Collection)toCopy, null, false, timestamp2, null, false);
        pumped.updateKeywordsCache();
        ComputerUtilCard.applyStaticContPT(ai.getGame(), pumped, (CardCollectionView)new CardCollection(c));
        return pumped;
    }

    public static void applyStaticContPT(Game game, Card vCard, CardCollectionView exclude) {
        if (!vCard.isCreature()) {
            return;
        }
        CardCollection list = new CardCollection((Iterable)game.getCardsIn(ZoneType.Battlefield));
        list.addAll((Collection)game.getCardsIn(ZoneType.Command));
        if (exclude != null) {
            list.removeAll((Collection)exclude);
        }
        list.add(vCard);
        for (Card c : list) {
            for (StaticAbility stAb : c.getStaticAbilities()) {
                vCard.removePTBoost(c.getLayerTimestamp(), (long)stAb.getId());
                if (!stAb.checkMode(StaticAbilityMode.Continuous) || !stAb.hasParam("Affected") || !stAb.hasParam("AddPower") && !stAb.hasParam("AddToughness") || !stAb.matchesValidParam("Affected", vCard)) continue;
                int att = 0;
                if (stAb.hasParam("AddPower")) {
                    String addP = stAb.getParam("AddPower");
                    att = AbilityUtils.calculateAmount((Card)(addP.contains("Affected") ? vCard : c), (String)addP, (CardTraitBase)stAb, (boolean)true);
                }
                int def = 0;
                if (stAb.hasParam("AddToughness")) {
                    String addT = stAb.getParam("AddToughness");
                    def = AbilityUtils.calculateAmount((Card)(addT.contains("Affected") ? vCard : c), (String)addT, (CardTraitBase)stAb, (boolean)true);
                }
                vCard.addPTBoost(att, def, c.getLayerTimestamp(), (long)stAb.getId());
            }
        }
    }

    public static AiAbilityDecision canPumpAgainstRemoval(Player ai, SpellAbility sa) {
        List<GameObject> objects = ComputerUtil.predictThreatenedObjects(sa.getActivatingPlayer(), sa, true);
        if (!sa.usesTargeting()) {
            CardCollection cards = AbilityUtils.getDefinedCards((Card)sa.getHostCard(), (String)sa.getParam("Defined"), (CardTraitBase)sa);
            for (Card card : cards) {
                if (!objects.contains(card)) continue;
                return new AiAbilityDecision(100, AiPlayDecision.ResponseToStackResolve);
            }
            return new AiAbilityDecision(0, AiPlayDecision.TargetingFailed);
        }
        CardCollection threatenedTargets = CardLists.getTargetableCards((Iterable)ai.getCardsIn(ZoneType.Battlefield), (SpellAbility)sa);
        threatenedTargets = ComputerUtil.getSafeTargets(ai, sa, (CardCollectionView)threatenedTargets);
        threatenedTargets.retainAll(objects);
        if (!threatenedTargets.isEmpty()) {
            ComputerUtilCard.sortByEvaluateCreature(threatenedTargets);
            for (Card c : threatenedTargets) {
                if (!sa.canAddMoreTarget()) continue;
                sa.getTargets().add((GameObject)c);
                if (sa.canAddMoreTarget()) continue;
                break;
            }
            if (!sa.isTargetNumberValid()) {
                sa.resetTargets();
                return new AiAbilityDecision(0, AiPlayDecision.TargetingFailed);
            }
            return new AiAbilityDecision(100, AiPlayDecision.ResponseToStackResolve);
        }
        return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
    }

    public static boolean isUselessCreature(Player ai, Card c) {
        if (c == null) {
            return true;
        }
        if (!c.isCreature()) {
            return false;
        }
        if (c.isDetained()) {
            return true;
        }
        if (c.hasKeyword("CARDNAME can't attack or block.")) {
            return true;
        }
        if (c.getOwner() == ai && ai.getOpponents().contains(c.getController())) {
            return true;
        }
        return c.isTapped() && !c.canUntap(ai, true);
    }

    public static boolean hasActiveUndyingOrPersist(Card c) {
        if (c.isToken()) {
            return false;
        }
        if (c.hasKeyword(Keyword.UNDYING) && c.getCounters((CounterType)CounterEnumType.P1P1) == 0) {
            return true;
        }
        return c.hasKeyword(Keyword.PERSIST) && c.getCounters((CounterType)CounterEnumType.M1M1) == 0;
    }

    public static int getMaxSAEnergyCostOnBattlefield(Player ai) {
        int maxEnergyCost = 0;
        for (Card c : ai.getCardsIn(ZoneType.Battlefield)) {
            for (SpellAbility sa : c.getSpellAbilities()) {
                int amount;
                CostPayEnergy energyCost = sa.getPayCosts().getCostEnergy();
                if (energyCost == null || (amount = energyCost.convertAmount().intValue()) <= maxEnergyCost) continue;
                maxEnergyCost = amount;
            }
        }
        return maxEnergyCost;
    }

    public static CardCollection prioritizeCreaturesWorthRemovingNow(Player ai, CardCollection oppCards, boolean temporary) {
        if (!CardLists.getNotType((Iterable)oppCards, (String)"Creature").isEmpty()) {
            return oppCards;
        }
        boolean enablePriorityRemoval = AiProfileUtil.getBoolProperty(ai, AiProps.ACTIVELY_DESTROY_IMMEDIATELY_UNBLOCKABLE);
        int priorityRemovalThreshold = AiProfileUtil.getIntProperty(ai, AiProps.DESTROY_IMMEDIATELY_UNBLOCKABLE_THRESHOLD);
        boolean priorityRemovalOnlyInDanger = AiProfileUtil.getBoolProperty(ai, AiProps.DESTROY_IMMEDIATELY_UNBLOCKABLE_ONLY_IN_DNGR);
        int lifeInDanger = AiProfileUtil.getIntProperty(ai, AiProps.DESTROY_IMMEDIATELY_UNBLOCKABLE_LIFE_IN_DNGR);
        if (!enablePriorityRemoval) {
            return oppCards;
        }
        CardCollection aiCreats = ai.getCreaturesInPlay();
        if (temporary) {
            oppCards = CardLists.filter((Iterable)oppCards, (Predicate)CardPredicates.UNTAPPED);
        }
        CardCollection priorityCards = new CardCollection();
        for (Card atk : oppCards) {
            boolean threat;
            boolean canBeBlocked = false;
            if (ComputerUtilCard.isUselessCreature(atk.getController(), atk)) continue;
            for (Card blk : aiCreats) {
                if (!CombatUtil.canBlock((Card)atk, (Card)blk, (boolean)true)) continue;
                canBeBlocked = true;
                break;
            }
            if (canBeBlocked) continue;
            boolean bl = threat = ComputerUtilCombat.getAttack(atk) >= ai.getLife() - lifeInDanger;
            if (priorityRemovalOnlyInDanger && !threat) continue;
            priorityCards.add(atk);
        }
        if (!priorityCards.isEmpty() && priorityCards.size() <= priorityRemovalThreshold) {
            return priorityCards;
        }
        return oppCards;
    }

    public static AiPlayDecision checkNeedsToPlayReqs(Card card, SpellAbility sa) {
        String needsToPlay;
        Game game = card.getGame();
        String needsToPlayName = "NeedsToPlay";
        String needsToPlayVarName = "NeedsToPlayVar";
        if (sa != null) {
            if (sa.isEvoke()) {
                if (card.hasSVar("NeedsToPlayEvoked")) {
                    needsToPlayName = "NeedsToPlayEvoked";
                }
                if (card.hasSVar("NeedsToPlayEvokedVar")) {
                    needsToPlayVarName = "NeedsToPlayEvokedVar";
                }
            } else if (sa.isKicked()) {
                needsToPlayName = card.hasSVar("NeedsToPlayKicked") ? "NeedsToPlayKicked" : "UNUSED";
                needsToPlayVarName = card.hasSVar("NeedsToPlayKickedVar") ? "NeedsToPlayKickedVar" : "UNUSED";
            }
        }
        if (card.hasSVar(needsToPlayName)) {
            needsToPlay = card.getSVar(needsToPlayName);
            if (needsToPlay.equalsIgnoreCase("WillAttack")) {
                if (sa != null && game.getPhaseHandler().isPlayerTurn(sa.getActivatingPlayer())) {
                    return ComputerUtilCard.doesSpecifiedCreatureAttackAI(sa.getActivatingPlayer(), card) ? AiPlayDecision.WillPlay : AiPlayDecision.BadEtbEffects;
                }
                return AiPlayDecision.WillPlay;
            }
            CardCollectionView list = game.getCardsIn(ZoneType.Battlefield);
            if ((list = CardLists.getValidCards((Iterable)list, (String)needsToPlay, (Player)card.getController(), (Card)card, (CardTraitBase)sa)).isEmpty()) {
                return AiPlayDecision.MissingNeededCards;
            }
        }
        if (card.getSVar(needsToPlayVarName).length() > 0) {
            int y;
            needsToPlay = card.getSVar(needsToPlayVarName);
            String sVar = needsToPlay.split(" ")[0];
            String comparator = needsToPlay.split(" ")[1];
            String compareTo = comparator.substring(2);
            int x = AbilityUtils.calculateAmount((Card)card, (String)sVar, (CardTraitBase)sa);
            if (!Expressions.compare((int)x, (String)comparator, (int)(y = AbilityUtils.calculateAmount((Card)card, (String)compareTo, (CardTraitBase)sa)))) {
                return AiPlayDecision.NeedsToPlayCriteriaNotMet;
            }
        }
        return AiPlayDecision.WillPlay;
    }

    public static Cost getTotalWardCost(Card c) {
        Cost totalCost = new Cost(ManaCost.NO_COST, false);
        for (KeywordInterface inst : c.getKeywords(Keyword.WARD)) {
            String keyword = inst.getOriginal();
            String[] k = keyword.split(":");
            Cost wardCost = new Cost(k[1], false);
            totalCost = totalCost.add(wardCost);
        }
        return totalCost;
    }

    public static boolean willUntap(Player ai, Card tapped) {
        for (Card card : ai.getGame().getCardsIn(ZoneType.Battlefield)) {
            boolean untapsEachTurn = card.hasSVar("UntapsEachTurn");
            boolean untapsEachOtherTurn = card.hasSVar("UntapsEachOtherPlayerTurn");
            if (!untapsEachTurn && !untapsEachOtherTurn) continue;
            String affected = untapsEachTurn ? card.getSVar("UntapsEachTurn") : card.getSVar("UntapsEachOtherPlayerTurn");
            for (String aff : TextUtil.split((CharSequence)affected, (char)',')) {
                if (!tapped.isValid(aff, ai, tapped, null) || !untapsEachTurn && (!untapsEachOtherTurn || !ai.equals(card.getController()))) continue;
                return true;
            }
        }
        return false;
    }

    public static boolean isNonDisabledCardInPlay(Player ai, String cardName) {
        for (Card card : ai.getCardsIn(ZoneType.Battlefield, cardName)) {
            boolean disabledByEnemy = false;
            for (Card card2 : card.getEnchantedBy()) {
                if (card2.getOwner() == ai) continue;
                disabledByEnemy = true;
                break;
            }
            if (disabledByEnemy) continue;
            return true;
        }
        return false;
    }

    public static CardCollection dedupeCards(CardCollection cc) {
        if (cc.size() <= 1) {
            return cc;
        }
        CardCollection deduped = new CardCollection();
        for (Card c : cc) {
            boolean unique = true;
            if (c.isInZone(ZoneType.Hand) && !c.hasPerpetual()) {
                for (Card d : deduped) {
                    if (!d.isInZone(ZoneType.Hand) || !d.getOwner().equals(c.getOwner()) || !d.getName().equals(c.getName())) continue;
                    unique = false;
                    break;
                }
            }
            if (!unique) continue;
            deduped.add(c);
        }
        return deduped;
    }

    public static boolean isCardRemAIDeck(Card card) {
        return card.getRules() != null && card.getRules().getAiHints().getRemAIDecks();
    }

    public static boolean isCardRemRandomDeck(Card card) {
        return card.getRules() != null && card.getRules().getAiHints().getRemRandomDecks();
    }

    public static boolean isCardRemNonCommanderDeck(Card card) {
        return card.getRules() != null && card.getRules().getAiHints().getRemNonCommanderDecks();
    }

    private static /* synthetic */ Card lambda$getBestLandAI$2(List bLand) {
        return (Card)Aggregates.random((Iterable)bLand);
    }

    static class LandEvaluator
    implements Function<Card, Integer> {
        LandEvaluator() {
        }

        @Override
        public Integer apply(Card card) {
            return GameStateEvaluator.evaluateLand(card);
        }
    }
}
