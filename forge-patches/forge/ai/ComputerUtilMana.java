/*
 * Decompiled with CFR 0.152.
 * 
 * Could not load the following classes:
 *  com.google.common.collect.ArrayListMultimap
 *  com.google.common.collect.ListMultimap
 *  com.google.common.collect.Lists
 *  com.google.common.collect.Maps
 *  com.google.common.collect.Multimap
 *  com.google.common.collect.MultimapBuilder
 *  forge.card.ColorSet
 *  forge.card.MagicColor
 *  forge.card.MagicColor$Color
 *  forge.card.mana.ManaAtom
 *  forge.card.mana.ManaCost
 *  forge.card.mana.ManaCostShard
 *  forge.game.CardTraitBase
 *  forge.game.CardTraitPredicates
 *  forge.game.Game
 *  forge.game.GameActionUtil
 *  forge.game.GameEntity
 *  forge.game.GameObject
 *  forge.game.ability.AbilityKey
 *  forge.game.ability.AbilityUtils
 *  forge.game.ability.ApiType
 *  forge.game.card.Card
 *  forge.game.card.CardCollection
 *  forge.game.card.CardCollectionView
 *  forge.game.card.CardLists
 *  forge.game.card.CardPlayOption
 *  forge.game.card.CardPredicates
 *  forge.game.card.CardUtil
 *  forge.game.card.CounterEnumType
 *  forge.game.card.CounterType
 *  forge.game.combat.Combat
 *  forge.game.combat.CombatUtil
 *  forge.game.cost.Cost
 *  forge.game.cost.CostAdjustment
 *  forge.game.cost.CostDecisionMakerBase
 *  forge.game.cost.CostPart
 *  forge.game.cost.CostPartMana
 *  forge.game.cost.CostPayEnergy
 *  forge.game.cost.CostPayment
 *  forge.game.cost.CostSacrifice
 *  forge.game.keyword.Keyword
 *  forge.game.mana.ManaConversionMatrix
 *  forge.game.mana.ManaCostBeingPaid
 *  forge.game.mana.ManaPool
 *  forge.game.phase.PhaseType
 *  forge.game.player.Player
 *  forge.game.player.PlayerPredicates
 *  forge.game.replacement.ReplacementEffect
 *  forge.game.replacement.ReplacementLayer
 *  forge.game.replacement.ReplacementType
 *  forge.game.spellability.AbilityManaPart
 *  forge.game.spellability.AbilitySub
 *  forge.game.spellability.SpellAbility
 *  forge.game.staticability.StaticAbilityManaConvert
 *  forge.game.trigger.Trigger
 *  forge.game.trigger.TriggerType
 *  forge.game.zone.Zone
 *  forge.game.zone.ZoneType
 *  forge.util.MyRandom
 *  forge.util.TextUtil
 *  org.apache.commons.lang3.StringUtils
 */
package forge.ai;

import com.google.common.collect.ArrayListMultimap;
import com.google.common.collect.ListMultimap;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import com.google.common.collect.Multimap;
import com.google.common.collect.MultimapBuilder;
import forge.ai.AiCardMemory;
import forge.ai.AiController;
import forge.ai.AiCostDecision;
import forge.ai.AiDeckStatistics;
import forge.ai.AiProps;
import forge.ai.ComputerUtilAbility;
import forge.ai.ComputerUtilCard;
import forge.ai.ComputerUtilCost;
import forge.ai.PlayerControllerAi;
import forge.ai.SpecialCardAi;
import forge.ai.SpellApiToAi;
import forge.ai.ability.AnimateAi;
import forge.card.ColorSet;
import forge.card.MagicColor;
import forge.card.mana.ManaAtom;
import forge.card.mana.ManaCost;
import forge.card.mana.ManaCostShard;
import forge.game.CardTraitBase;
import forge.game.CardTraitPredicates;
import forge.game.Game;
import forge.game.GameActionUtil;
import forge.game.GameEntity;
import forge.game.GameObject;
import forge.game.ability.AbilityKey;
import forge.game.ability.AbilityUtils;
import forge.game.ability.ApiType;
import forge.game.card.Card;
import forge.game.card.CardCollection;
import forge.game.card.CardCollectionView;
import forge.game.card.CardLists;
import forge.game.card.CardPlayOption;
import forge.game.card.CardPredicates;
import forge.game.card.CardUtil;
import forge.game.card.CounterEnumType;
import forge.game.card.CounterType;
import forge.game.combat.Combat;
import forge.game.combat.CombatUtil;
import forge.game.cost.Cost;
import forge.game.cost.CostAdjustment;
import forge.game.cost.CostDecisionMakerBase;
import forge.game.cost.CostPart;
import forge.game.cost.CostPartMana;
import forge.game.cost.CostPayEnergy;
import forge.game.cost.CostPayment;
import forge.game.cost.CostSacrifice;
import forge.game.keyword.Keyword;
import forge.game.mana.ManaConversionMatrix;
import forge.game.mana.ManaCostBeingPaid;
import forge.game.mana.ManaPool;
import forge.game.phase.PhaseType;
import forge.game.player.Player;
import forge.game.player.PlayerPredicates;
import forge.game.replacement.ReplacementEffect;
import forge.game.replacement.ReplacementLayer;
import forge.game.replacement.ReplacementType;
import forge.game.spellability.AbilityManaPart;
import forge.game.spellability.AbilitySub;
import forge.game.spellability.SpellAbility;
import forge.game.staticability.StaticAbilityManaConvert;
import forge.game.trigger.Trigger;
import forge.game.trigger.TriggerType;
import forge.game.zone.Zone;
import forge.game.zone.ZoneType;
import forge.util.MyRandom;
import forge.util.TextUtil;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import org.apache.commons.lang3.StringUtils;

public class ComputerUtilMana {
    private static final boolean DEBUG_MANA_PAYMENT = false;

    public static boolean canPayManaCost(ManaCostBeingPaid cost, SpellAbility sa, Player ai, boolean effect) {
        return ComputerUtilMana.payManaCost(cost = new ManaCostBeingPaid(cost), sa, ai, true, true, effect) != null;
    }

    public static boolean canPayManaCost(SpellAbility sa, Player ai, int extraMana, boolean effect) {
        return ComputerUtilMana.canPayManaCost(sa.getPayCosts(), sa, ai, extraMana, effect);
    }

    public static boolean canPayManaCost(Cost cost, SpellAbility sa, Player ai, int extraMana, boolean effect) {
        return ComputerUtilMana.payManaCost(cost, sa, ai, true, extraMana, true, effect);
    }

    public static boolean payManaCost(ManaCostBeingPaid cost, SpellAbility sa, Player ai, boolean effect) {
        return ComputerUtilMana.payManaCost(cost, sa, ai, false, true, effect) != null;
    }

    public static boolean payManaCost(Cost cost, Player ai, SpellAbility sa, boolean effect) {
        return ComputerUtilMana.payManaCost(cost, sa, ai, false, 0, true, effect);
    }

    private static boolean payManaCost(Cost cost, SpellAbility sa, Player ai, boolean test, int extraMana, boolean checkPlayable, boolean effect) {
        ManaCostBeingPaid manaCost = ComputerUtilMana.calculateManaCost(cost, sa, ai, test, extraMana, effect);
        return ComputerUtilMana.payManaCost(manaCost, sa, ai, test, checkPlayable, effect) != null;
    }

    public static int getConvergeCount(SpellAbility sa, Player ai) {
        ManaCostBeingPaid cost = ComputerUtilMana.calculateManaCost(sa.getPayCosts(), sa, ai, true, 0, false);
        if (ComputerUtilMana.payManaCost(cost, sa, ai, true, true, false) != null) {
            return cost.getSunburst();
        }
        return 0;
    }

    public static boolean hasEnoughManaSourcesToCast(SpellAbility sa, Player ai) {
        if (ai == null || sa == null) {
            return false;
        }
        sa.setActivatingPlayer(ai);
        return ComputerUtilMana.payManaCost(sa.getPayCosts(), sa, ai, true, 0, false, false);
    }

    public static CardCollection getManaSourcesToPayCost(ManaCostBeingPaid cost, SpellAbility sa, Player ai, boolean effect) {
        List<SpellAbility> payment = ComputerUtilMana.payManaCost(cost, sa, ai, true, true, effect);
        if (payment == null) {
            return null;
        }
        return new CardCollection(payment.stream().map(s -> s.getHostCard()));
    }

    private static Integer scoreManaProducingCard(Card card) {
        int score = 0;
        for (SpellAbility ability : card.getSpellAbilities()) {
            ability.setActivatingPlayer(card.getController());
            if (ability.isManaAbility()) {
                score += ability.calculateScoreForManaAbility();
                continue;
            }
            if (ability.isTrigger() || !ability.isPossible()) continue;
            score += 13;
        }
        if (card.isCreature()) {
            if (CombatUtil.canAttack((Card)card)) {
                score += 13;
            }
            if (CombatUtil.canBlock((Card)card)) {
                score += 13;
            }
        }
        return score;
    }

    private static void sortManaAbilities(ListMultimap<ManaCostShard, SpellAbility> sourcesForShards, ListMultimap<Integer, SpellAbility> manaAbilityMap, SpellAbility sa) {
        List<Integer> colorsMostCommon;
        Map<Card, Integer> manaCardMap = Maps.newHashMap();
        List<Card> orderedCards = Lists.newArrayList();
        for (ManaCostShard shard : sourcesForShards.keySet()) {
            for (SpellAbility ability : sourcesForShards.get(shard)) {
                Card hostCard = ability.getHostCard();
                if (manaCardMap.containsKey(hostCard)) continue;
                manaCardMap.put(hostCard, ComputerUtilMana.scoreManaProducingCard(hostCard));
                orderedCards.add(hostCard);
            }
        }
        orderedCards.sort(Comparator.comparingInt(manaCardMap::get));
        if (sourcesForShards.keySet().stream().anyMatch(ManaCostShard::isGeneric)) {
            CardCollection hand = new CardCollection(sa.getActivatingPlayer().getCardsIn(ZoneType.Hand));
            hand.remove(sa.getHostCard());
            AiDeckStatistics stats = AiDeckStatistics.fromCards((Iterable<Card>)hand);
            Integer[] orderedColorsIdx = new Integer[]{0, 1, 2, 3, 4};
            colorsMostCommon = Arrays.stream(orderedColorsIdx).sorted(Comparator.comparingInt(o -> stats.maxPips[(Integer)o]).reversed()).filter(idx -> stats.maxPips[idx] > 0).map(idx -> (int)MagicColor.WUBRG[idx]).collect(Collectors.toList());
        } else {
            colorsMostCommon = null;
        }
        for (ManaCostShard shard : sourcesForShards.keySet()) {
            int preferredShardAmount;
            List<SpellAbility> abilities = sourcesForShards.get(shard);
            List<SpellAbility> newAbilities = new ArrayList<>(abilities);
            newAbilities.sort((SpellAbility ability1, SpellAbility ability2) -> {
                int preOrder = orderedCards.indexOf(ability1.getHostCard()) - orderedCards.indexOf(ability2.getHostCard());
                if (preOrder != 0) {
                    if (shard.isGeneric() && ((Integer)manaCardMap.get(ability1.getHostCard())).equals(manaCardMap.get(ability2.getHostCard()))) {
                        for (Integer col : colorsMostCommon) {
                            boolean fromCommonColorSource1 = manaAbilityMap.get(col).stream().anyMatch(ma -> ma.getHostCard().equals(ability1.getHostCard()));
                            boolean fromCommonColorSource2 = manaAbilityMap.get(col).stream().anyMatch(ma -> ma.getHostCard().equals(ability2.getHostCard()));
                            if (fromCommonColorSource1 && !fromCommonColorSource2) {
                                return 1;
                            }
                            if (fromCommonColorSource1 || !fromCommonColorSource2) continue;
                            return -1;
                        }
                    }
                    return preOrder;
                }
                String shardMana = shard.toShortString();
                boolean payWithAb1 = ability1.getManaPart().mana(ability1).contains(shardMana);
                boolean payWithAb2 = ability2.getManaPart().mana(ability2).contains(shardMana);
                if (payWithAb1 && !payWithAb2) {
                    return -1;
                }
                if (payWithAb2 && !payWithAb1) {
                    return 1;
                }
                return ability1.compareTo(ability2);
            });
            sourcesForShards.replaceValues(shard, newAbilities);
            String manaPref = sa.getParamOrDefault("AIManaPref", "");
            if (manaPref.isEmpty() && sa.getHostCard() != null && sa.getHostCard().hasSVar("AIManaPref")) {
                manaPref = sa.getHostCard().getSVar("AIManaPref");
            }
            if (manaPref.isEmpty()) continue;
            String[] prefShardInfo = manaPref.split(":");
            String preferredShard = prefShardInfo[0];
            int n = preferredShardAmount = prefShardInfo.length > 1 ? Integer.parseInt(prefShardInfo[1]) : 3;
            if (preferredShard.isEmpty()) continue;
            List<SpellAbility> prefSortedAbilities = new ArrayList<>(newAbilities);
            List<SpellAbility> otherSortedAbilities = new ArrayList<>(newAbilities);
            prefSortedAbilities.sort((ability1, ability2) -> {
                if (ability1.getManaPart().mana(ability1).contains(preferredShard)) {
                    return -1;
                }
                if (ability2.getManaPart().mana(ability2).contains(preferredShard)) {
                    return 1;
                }
                return 0;
            });
            otherSortedAbilities.sort((ability1, ability2) -> {
                if (ability1.getManaPart().mana(ability1).contains(preferredShard)) {
                    return 1;
                }
                if (ability2.getManaPart().mana(ability2).contains(preferredShard)) {
                    return -1;
                }
                return 0;
            });
            ArrayList<SpellAbility> finalAbilities = new ArrayList<SpellAbility>();
            for (int i = 0; i < preferredShardAmount && i < prefSortedAbilities.size(); ++i) {
                finalAbilities.add((SpellAbility)prefSortedAbilities.get(i));
            }
            for (SpellAbility ab : otherSortedAbilities) {
                if (finalAbilities.contains(ab)) continue;
                finalAbilities.add(ab);
            }
            sourcesForShards.replaceValues(shard, finalAbilities);
        }
    }

    public static SpellAbility chooseManaAbility(ManaCostBeingPaid cost, SpellAbility sa, Player ai, ManaCostShard toPay, Collection<SpellAbility> maList, boolean checkCosts) {
        Card saHost = sa.getHostCard();
        String manaSourceType = "";
        if (saHost.hasSVar("AIPreference")) {
            String condition = saHost.getSVar("AIPreference");
            if (condition.startsWith("ManaFrom")) {
                manaSourceType = TextUtil.split((CharSequence)condition, (char)'$')[1];
            }
        } else if (sa.hasParam("AIManaPref")) {
            manaSourceType = sa.getParam("AIManaPref");
        }
        if (manaSourceType != "") {
            List<SpellAbility> filteredList = Lists.newArrayList(maList);
            switch (manaSourceType) {
                case "Snow": {
                    filteredList.sort((ab1, ab2) -> ab1.getHostCard() != null && ab1.getHostCard().isSnow() && ab2.getHostCard() != null && !ab2.getHostCard().isSnow() ? -1 : 1);
                    maList = filteredList;
                    break;
                }
                case "Treasure": {
                    filteredList.sort((ab1, ab2) -> ab1.getHostCard() != null && ab1.getHostCard().getType().hasSubtype("Treasure") && ab2.getHostCard() != null && !ab2.getHostCard().getType().hasSubtype("Treasure") ? -1 : 1);
                    SpellAbility first = (SpellAbility)filteredList.get(0);
                    if (first.getHostCard() == null || !first.getHostCard().getType().hasSubtype("Treasure")) break;
                    maList.remove(first);
                    ArrayList updatedList = Lists.newArrayList();
                    updatedList.add(first);
                    updatedList.addAll(maList);
                    maList = updatedList;
                    break;
                }
                case "TreasureMax": {
                    filteredList.sort((ab1, ab2) -> ab1.getHostCard() != null && ab1.getHostCard().getType().hasSubtype("Treasure") && ab2.getHostCard() != null && !ab2.getHostCard().getType().hasSubtype("Treasure") ? -1 : 1);
                    maList = filteredList;
                    break;
                }
                case "NotSameCard": {
                    String hostName = sa.getHostCard().getName();
                    maList = filteredList.stream().filter(saPay -> !saPay.getHostCard().getName().equals(hostName)).collect(Collectors.toList());
                    break;
                }
            }
        }
        for (SpellAbility ma : maList) {
            int amount;
            if (ma.getHostCard() == saHost || ma.getPayCosts().hasTapCost() && AiCardMemory.isRememberedCard(ai, ma.getHostCard(), AiCardMemory.MemorySet.PAYS_TAP_COST) || (amount = ma.hasParam("Amount") ? AbilityUtils.calculateAmount((Card)ma.getHostCard(), (String)ma.getParam("Amount"), (CardTraitBase)ma) : 1) <= 0 || (sa.getApi() == ApiType.Animate ? saHost.isAura() && "Enchanted".equals(sa.getParam("Defined")) && ma.getHostCard() == saHost.getEnchantingCard() && ma.getPayCosts().hasTapCost() || saHost.isLand() && ma.getHostCard().isLand() && ai.getController().isAI() && AnimateAi.isAnimatedThisTurn(ai, ma.getHostCard()) : (sa.getApi() == ApiType.Pump ? (saHost.isInstant() || saHost.isSorcery()) && ma.getHostCard().isCreature() && ai.getController().isAI() && ma.getPayCosts().hasTapCost() && sa.getTargets().getTargetCards().contains(ma.getHostCard()) : sa.getApi() == ApiType.Attach && "AvoidPayingWithAttachTarget".equals(saHost.getSVar("AIPaymentPreference")) && ma.getHostCard().equals(sa.getTargetCard()) && CardLists.count(ai.getCardsIn(ZoneType.Battlefield), CardPredicates.nameEquals((String)ma.getHostCard().getName()).and(CardPredicates.UNTAPPED)) > 1))) continue;
            SpellAbility paymentChoice = ma;
            if (ComputerUtilAbility.getAbilitySourceName(ma).equals("Cavern of Souls") && saHost.getType().hasCreatureType(ma.getHostCard().getChosenType())) {
                if (toPay == ManaCostShard.COLORLESS && cost.getUnpaidShards().contains(ManaCostShard.GENERIC)) continue;
                if (toPay == ManaCostShard.GENERIC || toPay == ManaCostShard.X) {
                    for (SpellAbility ab : maList) {
                        if (!ab.isManaAbility() || !ab.getManaPart().isAnyMana() || !ab.hasParam("AddsNoCounter") || ab.getHostCard().isTapped()) continue;
                        paymentChoice = ab;
                        break;
                    }
                }
            }
            if (!ComputerUtilMana.canPayShardWithSpellAbility(toPay, ai, paymentChoice, sa, cost, checkCosts, cost.getXManaCostPaidByColor()) || !ComputerUtilCost.checkForManaSacrificeCost(ai, ma.getPayCosts(), ma, ma.isTrigger()) || !ComputerUtilCost.checkTapTypeCost(ai, ma.getPayCosts(), ma.getHostCard(), sa, AiCardMemory.getMemorySet(ai, AiCardMemory.MemorySet.PAYS_TAP_COST))) continue;
            return paymentChoice;
        }
        return null;
    }

    public static String predictManaReplacement(SpellAbility saPayment, Player ai, ManaCostShard toPay) {
        Card hostCard = saPayment.getHostCard();
        Game game = hostCard.getGame();
        String manaProduced = toPay.isSnow() && hostCard.isSnow() ? "S" : GameActionUtil.generatedTotalMana((SpellAbility)saPayment);
        Map<AbilityKey, Object> repParams = AbilityKey.mapFromAffected((GameEntity)hostCard);
        repParams.put(AbilityKey.Mana, manaProduced);
        repParams.put(AbilityKey.Activator, ai);
        repParams.put(AbilityKey.AbilityMana, saPayment);
        List<ReplacementEffect> reList = game.getReplacementHandler().getReplacementList(ReplacementType.ProduceMana, repParams, ReplacementLayer.Other);
        ArrayList<SpellAbility> replaceMana = Lists.newArrayList();
        ArrayList replaceType = Lists.newArrayList();
        ArrayList<SpellAbility> replaceAmount = Lists.newArrayList();
        for (ReplacementEffect re : reList) {
            SpellAbility o = re.getOverridingAbility();
            if (o == null || o.getApi() != ApiType.ReplaceMana) continue;
            if (o.hasParam("ReplaceMana")) {
                replaceMana.add(o);
                continue;
            }
            if (o.hasParam("ReplaceType") || o.hasParam("ReplaceColor")) {
                replaceType.add(o);
                continue;
            }
            if (!o.hasParam("ReplaceAmount")) continue;
            replaceAmount.add(o);
        }
        if (!replaceMana.isEmpty()) {
            for (SpellAbility saMana : replaceMana) {
                String m = saMana.getParam("ReplaceMana");
                if ("Any".equals(m)) {
                    byte rs = 16;
                    for (byte by : MagicColor.WUBRGC) {
                        if (!toPay.canBePaidWithManaOfColor(by)) continue;
                        rs = by;
                        break;
                    }
                    manaProduced = MagicColor.toShortString((byte)rs);
                    continue;
                }
                manaProduced = m;
            }
        }
        if (!replaceType.isEmpty()) {
            for (SpellAbility saMana : replaceAmount) {
                String color;
                Card card = saMana.getHostCard();
                if (saMana.hasParam("ReplaceType")) {
                    color = saMana.getParam("ReplaceType");
                    if ("Any".equals(color)) {
                        byte rs = 16;
                        byte[] byArray = MagicColor.WUBRGC;
                        int n = byArray.length;
                        for (int i = 0; i < n; ++i) {
                            byte c2 = byArray[i];
                            if (!toPay.canBePaidWithManaOfColor(c2)) continue;
                            rs = c2;
                            break;
                        }
                        color = MagicColor.toShortString((byte)rs);
                    }
                    for (int i : MagicColor.WUBRGC) {
                        String s = MagicColor.toShortString((byte)i);
                        manaProduced = manaProduced.replace(s, color);
                    }
                    continue;
                }
                if (!saMana.hasParam("ReplaceColor")) continue;
                color = saMana.getParam("ReplaceColor");
                if ("Chosen".equals(color) && card.hasChosenColor()) {
                    color = MagicColor.toShortString((String)card.getChosenColor());
                }
                if (saMana.hasParam("ReplaceOnly")) {
                    manaProduced = manaProduced.replace(saMana.getParam("ReplaceOnly"), color);
                    continue;
                }
                for (int i : MagicColor.WUBRG) {
                    String s = MagicColor.toShortString((byte)i);
                    manaProduced = manaProduced.replace(s, color);
                }
            }
        }
        if (!replaceAmount.isEmpty()) {
            int totalAmount = 1;
            for (SpellAbility saMana : replaceAmount) {
                totalAmount *= Integer.parseInt(saMana.getParam("ReplaceAmount"));
            }
            manaProduced = StringUtils.repeat((String)manaProduced, (String)" ", (int)totalAmount);
        }
        return manaProduced;
    }

    public static String predictManafromSpellAbility(SpellAbility saPayment, Player ai, ManaCostShard toPay) {
        Card hostCard = saPayment.getHostCard();
        StringBuilder manaProduced = new StringBuilder(ComputerUtilMana.predictManaReplacement(saPayment, ai, toPay));
        String originalProduced = manaProduced.toString();
        if (originalProduced.isEmpty()) {
            return originalProduced;
        }
        Map runParams = AbilityKey.mapFromCard((Card)hostCard);
        runParams.put(AbilityKey.Activator, ai);
        runParams.put(AbilityKey.AbilityMana, saPayment);
        runParams.put(AbilityKey.Produced, originalProduced);
        block0: for (Object trObj : ai.getGame().getTriggerHandler().getActiveTrigger(TriggerType.TapsForMana, runParams)) {
            SpellAbility trSA = ((forge.game.trigger.Trigger)trObj).ensureAbility();
            if (trSA == null) continue;
            if (ApiType.Mana.equals(trSA.getApi())) {
                int pAmount = AbilityUtils.calculateAmount((Card)trSA.getHostCard(), (String)trSA.getParamOrDefault("Amount", "1"), (CardTraitBase)trSA);
                String produced = trSA.getParam("Produced");
                if (produced.equals("Chosen")) {
                    produced = MagicColor.toShortString((String)trSA.getHostCard().getChosenColor());
                }
                manaProduced.append(" ").append(StringUtils.repeat((String)produced, (String)" ", (int)pAmount));
                continue;
            }
            if (!ApiType.ManaReflected.equals(trSA.getApi())) continue;
            String colorOrType = trSA.getParamOrDefault("ColorOrType", "Color");
            String reflectProperty = trSA.getParam("ReflectProperty");
            if (!reflectProperty.equals("Produced") || originalProduced.isEmpty()) continue;
            if (toPay.equals(ManaCostShard.COLORLESS) && colorOrType.equals("Type") && originalProduced.contains("C")) {
                manaProduced.append(" C");
                continue;
            }
            if (originalProduced.length() == 1) {
                if (!colorOrType.equals("Type") && originalProduced.equals("C")) continue;
                manaProduced.append(" ").append(originalProduced);
                continue;
            }
            boolean found = false;
            for (String s : originalProduced.split(" ")) {
                if (!colorOrType.equals("Type") && (s.equals("C") || !toPay.canBePaidWithManaOfColor(MagicColor.fromName((String)s)))) continue;
                found = true;
                manaProduced.append(" ").append(s);
                break;
            }
            if (found) continue;
            for (String s : originalProduced.split(" ")) {
                if (!colorOrType.equals("Type") && s.equals("C")) continue;
                manaProduced.append(" ").append(s);
                continue block0;
            }
        }
        return manaProduced.toString();
    }

    private static List<SpellAbility> payManaCost(ManaCostBeingPaid cost, SpellAbility sa, Player ai, boolean test, boolean checkPlayable, boolean effect) {
        if (sa.isOffering() && sa.getSacrificedAsOffering() == null || sa.isEmerge() && sa.getSacrificedAsEmerge() == null) {
            return null;
        }
        AiCardMemory.clearMemorySet(ai, AiCardMemory.MemorySet.PAYS_TAP_COST);
        AiCardMemory.clearMemorySet(ai, AiCardMemory.MemorySet.PAYS_SAC_COST);
        ComputerUtilMana.adjustManaCostToAvoidNegEffects(cost, sa.getHostCard(), ai);
        List manaSpentToPay = test ? new ArrayList() : sa.getPayingMana();
        ArrayList paymentList = Lists.newArrayList();
        ManaPool manapool = ai.getManaPool();
        if (ai.getControllingPlayer() == null) {
            manapool.restoreColorReplacements();
            CardPlayOption mayPlay = sa.getMayPlayOption();
            if (!effect) {
                if (sa.isSpell() && mayPlay != null) {
                    mayPlay.applyManaConvert((ManaConversionMatrix)manapool);
                } else if (sa.isActivatedAbility() && sa.getGrantorStatic() != null && sa.getGrantorStatic().hasParam("ManaConversion")) {
                    AbilityUtils.applyManaColorConversion((ManaConversionMatrix)manapool, (String)sa.getGrantorStatic().getParam("ManaConversion"));
                }
            }
            if (sa.hasParam("ManaConversion")) {
                AbilityUtils.applyManaColorConversion((ManaConversionMatrix)manapool, (String)sa.getParam("ManaConversion"));
            }
            StaticAbilityManaConvert.manaConvert((ManaConversionMatrix)manapool, (Player)ai, (Card)sa.getHostCard(), (SpellAbility)(effect && !sa.isCastFromPlayEffect() ? null : sa));
        }
        if (manapool.payManaCostFromPool(cost, sa, test, manaSpentToPay)) {
            CostPayment.handleOfferings((SpellAbility)sa, (boolean)test, (boolean)cost.isPaid());
            return paymentList;
        }
        int phyLifeToPay = 2;
        boolean purePhyrexian = cost.containsOnlyPhyrexianMana();
        boolean hasConverge = sa.getHostCard().hasConverge();
        ListMultimap<ManaCostShard, SpellAbility> sourcesForShards = ComputerUtilMana.getSourcesForShards(cost, sa, ai, test, checkPlayable, hasConverge);
        int testEnergyPool = ai.getCounters((CounterType)CounterEnumType.ENERGY);
        ManaCostShard toPay = null;
        ArrayList<SpellAbility> saExcludeList = new ArrayList<SpellAbility>();
        while (!cost.isPaid()) {
            SpellAbility saPayment = null;
            while (!cost.isPaid() && !manapool.isEmpty()) {
                boolean found = false;
                for (byte color : ManaAtom.MANATYPES) {
                    if (!manapool.tryPayCostWithColor(color, sa, cost, manaSpentToPay)) continue;
                    found = true;
                    break;
                }
                if (found) continue;
                break;
            }
            if (cost.isPaid() || sourcesForShards == null && !purePhyrexian) break;
            toPay = ComputerUtilMana.getNextShardToPay(cost, sourcesForShards);
            List saList = null;
            if (hasConverge && (toPay == ManaCostShard.GENERIC || toPay == ManaCostShard.X)) {
                int unpaidColors = cost.getUnpaidColors() + cost.getColorsPaid() ^ 0x1F;
                for (MagicColor.Color b : ColorSet.fromMask((int)unpaidColors)) {
                    ManaCostShard shard = ManaCostShard.valueOf((int)b.getColorMask());
                    saList = sourcesForShards.get(shard);
                    if (saList == null || saList.isEmpty()) continue;
                    toPay = shard;
                    break;
                }
                if (saList == null || saList.isEmpty()) {
                    saList = sourcesForShards.get(toPay);
                    hasConverge = false;
                }
            } else {
                saList = sourcesForShards == null && purePhyrexian ? Lists.newArrayList() : sourcesForShards.get(toPay);
            }
            saList.removeAll(saExcludeList);
            SpellAbility spellAbility = saList.isEmpty() ? null : (saPayment = ComputerUtilMana.chooseManaAbility(cost, sa, ai, toPay, saList, checkPlayable || !test));
            if (saPayment != null && ComputerUtilCost.isSacrificeSelfCost(saPayment.getPayCosts()) && sa.isTargeting((GameObject)saPayment.getHostCard())) {
                saExcludeList.add(saPayment);
                continue;
            }
            if (saPayment != null && "BlackLotus".equals(saPayment.getParam("AILogic")) && !SpecialCardAi.BlackLotus.consider(ai, sa, cost)) {
                saExcludeList.add(saPayment);
                continue;
            }
            if (saPayment == null) {
                boolean lifeInsteadOfBlack;
                boolean bl = lifeInsteadOfBlack = toPay.isBlack() && ai.hasKeyword("PayLifeInsteadOf:B");
                if (!toPay.isPhyrexian() && !lifeInsteadOfBlack || !ai.canPayLife(phyLifeToPay, false, sa) || ai.getLife() <= phyLifeToPay && !ai.cantLoseForZeroOrLessLife()) break;
                if (test) {
                    phyLifeToPay += 2;
                }
                if (sa.hasParam("AIPhyrexianPayment")) {
                    if ("Never".equals(sa.getParam("AIPhyrexianPayment"))) break;
                    if (sa.getParam("AIPhyrexianPayment").startsWith("OnFatalDamage.")) {
                        int dmg = Integer.parseInt(sa.getParam("AIPhyrexianPayment").substring(14));
                        if (ai.getOpponents().stream().noneMatch(PlayerPredicates.lifeLessOrEqualTo((int)dmg))) break;
                    }
                }
                if (toPay.isPhyrexian()) {
                    cost.payPhyrexian();
                    if (!test) {
                        sa.setSpendPhyrexianMana(true);
                    }
                } else if (lifeInsteadOfBlack) {
                    cost.decreaseShard(ManaCostShard.BLACK, 1);
                }
                if (test) continue;
                ai.payLife(2, sa, false);
                continue;
            }
            paymentList.add(saPayment);
            if (saPayment.getPayCosts().hasTapCost()) {
                AiCardMemory.rememberCard(ai, saPayment.getHostCard(), AiCardMemory.MemorySet.PAYS_TAP_COST);
            }
            if (test) {
                CostPayEnergy energyCost = saPayment.getPayCosts().getCostEnergy();
                if (energyCost != null && (testEnergyPool -= Integer.parseInt(energyCost.getAmount())) < 0) break;
                if (saPayment.getPayCosts().hasManaCost()) {
                    cost.increaseGenericMana(saPayment.getPayCosts().getCostMana().getMana().getCMC());
                }
                String manaProduced = ComputerUtilMana.predictManafromSpellAbility(saPayment, ai, toPay);
                ComputerUtilMana.payMultipleMana(cost, manaProduced, ai);
                sourcesForShards.values().removeIf(CardTraitPredicates.isHostCard((Card)saPayment.getHostCard()));
                continue;
            }
            CostPayment pay = new CostPayment(saPayment.getPayCosts(), saPayment);
            if (!pay.payComputerCosts((CostDecisionMakerBase)new AiCostDecision(ai, saPayment, effect, true))) {
                saList.remove(saPayment);
                continue;
            }
            ai.getGame().getStack().addAndUnfreeze(saPayment);
            manapool.payManaFromAbility(sa, cost, saPayment);
            if (hasConverge) {
                sourcesForShards.values().removeIf(CardTraitPredicates.isHostCard((Card)saPayment.getHostCard()));
                continue;
            }
            if (cost.isPaid() || !saPayment.isActivatedAbility() || saPayment.canPlay()) continue;
            SpellAbility saPaymentFinal = saPayment;
            sourcesForShards.values().removeIf(s -> s == saPaymentFinal || s.getHostCard().equals(saPaymentFinal.getHostCard()) && !s.canPlay());
        }
        CostPayment.handleOfferings((SpellAbility)sa, (boolean)test, (boolean)cost.isPaid());
        if (!cost.isPaid()) {
            manapool.refundMana(manaSpentToPay);
            if (test) {
                ComputerUtilMana.resetPayment(paymentList);
            } else {
                System.out.println("ComputerUtilMana: payManaCost() cost was not paid for " + String.valueOf(sa) + " (" + sa.getHostCard().getName() + "). Didn't find what to pay for " + String.valueOf(toPay));
                sa.setSkip(true);
            }
            return null;
        }
        if (test) {
            manapool.refundMana(manaSpentToPay);
            ComputerUtilMana.resetPayment(paymentList);
        }
        return paymentList;
    }

    private static void resetPayment(List<SpellAbility> payments) {
        for (SpellAbility sa : payments) {
            sa.getManaPart().clearExpressChoice();
        }
    }

    private static ListMultimap<ManaCostShard, SpellAbility> getSourcesForShards(ManaCostBeingPaid cost, SpellAbility sa, Player ai, boolean test, boolean checkPlayable, boolean hasConverge) {
        ListMultimap<Integer, SpellAbility> manaAbilityMap = ComputerUtilMana.groupSourcesByManaColor(ai, checkPlayable);
        if (manaAbilityMap.isEmpty()) {
            return null;
        }
        ListMultimap<ManaCostShard, SpellAbility> sourcesForShards = ComputerUtilMana.groupAndOrderToPayShards(ai, manaAbilityMap, cost);
        if (hasConverge) {
            int unpaidColors = cost.getUnpaidColors() + cost.getColorsPaid() ^ 0x1F;
            for (MagicColor.Color color : ColorSet.fromMask((int)unpaidColors)) {
                byte b = color.getColorMask();
                ManaCostShard shard = ManaCostShard.valueOf((int)b);
                if (sourcesForShards.containsKey(shard) || !ai.getManaPool().canPayForShardWithColor(shard, b)) continue;
                for (SpellAbility saMana : manaAbilityMap.get((int)b)) {
                    sourcesForShards.get(shard).add(saMana);
                }
            }
        }
        ComputerUtilMana.sortManaAbilities(sourcesForShards, manaAbilityMap, sa);
        return sourcesForShards;
    }

    private static void setComboManaChoice(Player ai, SpellAbility manaAb, ManaCostBeingPaid cost) {
        StringBuilder choiceString = new StringBuilder();
        AbilityManaPart comboMana = manaAb.getManaPart();
        int amount = manaAb.hasParam("Amount") ? AbilityUtils.calculateAmount((Card)manaAb.getHostCard(), (String)manaAb.getParam("Amount"), (CardTraitBase)manaAb) : 1;
        ManaCostBeingPaid testCost = new ManaCostBeingPaid(cost);
        String[] comboColors = comboMana.getComboColors(manaAb).split(" ");
        for (int nMana = 1; nMana <= amount; ++nMana) {
            String commonColor;
            String choice = "";
            if (!comboMana.getExpressChoice().isEmpty()) {
                choice = comboMana.getExpressChoice();
                comboMana.clearExpressChoice();
                byte colorMask = ManaAtom.fromName((String)choice);
                if (manaAb.canProduce(choice) && ComputerUtilMana.satisfiesColorChoice(comboMana, choiceString, choice) && testCost.isAnyPartPayableWith(colorMask, ai.getManaPool())) {
                    choiceString.append(choice);
                    ComputerUtilMana.payMultipleMana(testCost, choice, ai);
                    continue;
                }
            }
            if (!testCost.isPaid()) {
                for (String color : comboColors) {
                    if (!ComputerUtilMana.satisfiesColorChoice(comboMana, choiceString, choice) || !testCost.needsColor(ManaAtom.fromName((String)color), ai.getManaPool())) continue;
                    ComputerUtilMana.payMultipleMana(testCost, color, ai);
                    if (nMana != 1) {
                        choiceString.append(" ");
                    }
                    choiceString.append(color);
                    choice = color;
                    break;
                }
                if (!choice.isEmpty()) continue;
            }
            if (!(commonColor = ComputerUtilCard.getMostProminentColor((Iterable<Card>)ai.getCardsIn(ZoneType.Hand))).isEmpty() && ComputerUtilMana.satisfiesColorChoice(comboMana, choiceString, MagicColor.toShortString((String)commonColor)) && comboMana.getComboColors(manaAb).contains(MagicColor.toShortString((String)commonColor))) {
                choice = MagicColor.toShortString((String)commonColor);
            } else {
                for (String c : comboColors) {
                    if (!ComputerUtilMana.satisfiesColorChoice(comboMana, choiceString, c)) continue;
                    choice = c;
                    break;
                }
            }
            if (nMana != 1) {
                choiceString.append(" ");
            }
            choiceString.append(choice);
        }
        if (choiceString.toString().isEmpty()) {
            choiceString.append("0");
        }
        comboMana.setExpressChoice(choiceString.toString());
    }

    private static boolean satisfiesColorChoice(AbilityManaPart abMana, StringBuilder choices, String choice) {
        return !abMana.getOrigProduced().contains("Different") || !choices.toString().contains(choice);
    }

    private static boolean canPayShardWithSpellAbility(ManaCostShard toPay, Player ai, SpellAbility ma, SpellAbility sa, ManaCostBeingPaid cost, boolean checkCosts, Map<String, Integer> xManaCostPaidByColor) {
        Card sourceCard = ma.getHostCard();
        if (ComputerUtilMana.isManaSourceReserved(ai, sourceCard)) {
            return false;
        }
        if (toPay.isSnow() && !sourceCard.isSnow()) {
            return false;
        }
        AbilityManaPart m = ma.getManaPart();
        if (!m.meetsManaRestrictions(sa)) {
            return false;
        }
        if (checkCosts) {
            ma.setActivatingPlayer(ai);
            if (!CostPayment.canPayAdditionalCosts((Cost)ma.getPayCosts(), (SpellAbility)ma, (boolean)false)) {
                return false;
            }
            if (ma.getRestrictions() != null && ma.getRestrictions().isInstantSpeed()) {
                return false;
            }
        }
        if (m.isComboMana()) {
            for (String s : m.getComboColors(ma).split(" ")) {
                if (toPay == ManaCostShard.COLORED_X && !ManaCostBeingPaid.canColoredXShardBePaidByColor((String)s, xManaCostPaidByColor) || !sa.allowsPayingWithShard(sourceCard, ManaAtom.fromName((String)s)) || !ai.getManaPool().canPayForShardWithColor(toPay, ManaAtom.fromName((String)s))) continue;
                ColorSet shared = ColorSet.fromMask((int)toPay.getColorMask()).getSharedColors(ColorSet.fromNames((String[])m.getComboColors(ma).split(" ")));
                if (!shared.isColorless()) {
                    m.setExpressChoice(((MagicColor.Color)shared.iterator().next()).getShortName());
                }
                ComputerUtilMana.setComboManaChoice(ai, ma, cost);
                return true;
            }
            return false;
        }
        if (ma.getApi() == ApiType.ManaReflected) {
            Set reflected = CardUtil.getReflectableManaColors((SpellAbility)ma);
            for (byte c : MagicColor.WUBRGC) {
                if (toPay == ManaCostShard.COLORED_X && !ManaCostBeingPaid.canColoredXShardBePaidByColor((String)MagicColor.toShortString((byte)c), xManaCostPaidByColor) || !sa.allowsPayingWithShard(sourceCard, c) || !ai.getManaPool().canPayForShardWithColor(toPay, c) || !reflected.contains(MagicColor.toLongString((byte)c))) continue;
                m.setExpressChoice(MagicColor.toShortString((byte)c));
                return true;
            }
            return false;
        }
        if (!sa.allowsPayingWithShard(sourceCard, MagicColor.fromName((String)m.getOrigProduced()))) {
            return false;
        }
        if (toPay == ManaCostShard.COLORED_X) {
            for (String s : m.mana(ma).split(" ")) {
                if (!ManaCostBeingPaid.canColoredXShardBePaidByColor((String)s, xManaCostPaidByColor)) continue;
                return true;
            }
            return false;
        }
        if (m.isAnyMana()) {
            byte colorChoice = 0;
            if (toPay.isOr2Generic()) {
                colorChoice = toPay.getColorMask();
            } else {
                for (byte c : MagicColor.WUBRG) {
                    if (!ai.getManaPool().canPayForShardWithColor(toPay, c)) continue;
                    colorChoice = c;
                    break;
                }
            }
            m.setExpressChoice(MagicColor.toShortString((byte)colorChoice));
        }
        return true;
    }

    private static boolean isManaSourceReserved(Player ai, Card sourceCard) {
        if (!(ai.getController() instanceof PlayerControllerAi)) {
            return false;
        }
        if (AiCardMemory.isRememberedCard(ai, sourceCard, AiCardMemory.MemorySet.HELD_MANA_SOURCES_FOR_NEXT_SPELL)) {
            return true;
        }
        PhaseType curPhase = ai.getGame().getPhaseHandler().getPhase();
        AiController aic = ((PlayerControllerAi)ai.getController()).getAi();
        if (curPhase == PhaseType.COMBAT_DECLARE_BLOCKERS || curPhase == PhaseType.CLEANUP) {
            if (ai.getGame().getPhaseHandler().isPlayerTurn(ai)) {
                AiCardMemory.clearMemorySet(ai, AiCardMemory.MemorySet.HELD_MANA_SOURCES_FOR_DECLBLK);
            } else {
                AiCardMemory.clearMemorySet(ai, AiCardMemory.MemorySet.HELD_MANA_SOURCES_FOR_ENEMY_DECLBLK);
                AiCardMemory.clearMemorySet(ai, AiCardMemory.MemorySet.CHOSEN_FOG_EFFECT);
            }
        } else if (AiCardMemory.isRememberedCard(ai, sourceCard, AiCardMemory.MemorySet.HELD_MANA_SOURCES_FOR_DECLBLK) || AiCardMemory.isRememberedCard(ai, sourceCard, AiCardMemory.MemorySet.HELD_MANA_SOURCES_FOR_ENEMY_DECLBLK)) {
            return true;
        }
        int chanceToReserve = aic.getIntProperty(AiProps.RESERVE_MANA_FOR_MAIN2_CHANCE);
        if (chanceToReserve == 0 || !MyRandom.percentTrue((int)chanceToReserve)) {
            return false;
        }
        if (curPhase == PhaseType.MAIN2 || curPhase == PhaseType.CLEANUP) {
            AiCardMemory.clearMemorySet(ai, AiCardMemory.MemorySet.HELD_MANA_SOURCES_FOR_MAIN2);
        } else if (AiCardMemory.isRememberedCard(ai, sourceCard, AiCardMemory.MemorySet.HELD_MANA_SOURCES_FOR_MAIN2)) {
            return true;
        }
        return false;
    }

    private static ManaCostShard getNextShardToPay(ManaCostBeingPaid cost, Multimap<ManaCostShard, SpellAbility> sourcesForShards) {
        ArrayList shardsToPay = Lists.newArrayList(cost.getDistinctShards());
        shardsToPay.sort((Object shard1, Object shard2) -> Integer.compare(sourcesForShards.get((ManaCostShard)shard1).size(), sourcesForShards.get((ManaCostShard)shard2).size()));
        return cost.getShardToPayByPriority(shardsToPay, ColorSet.WUBRG.getColor());
    }

    private static void adjustManaCostToAvoidNegEffects(ManaCostBeingPaid cost, Card card, Player ai) {
        for (String manaPart : card.getSVar("ManaNeededToAvoidNegativeEffect").split(",")) {
            byte mask;
            if (manaPart.isEmpty() || cost.needsColor(mask = ManaAtom.fromName((String)manaPart), ai.getManaPool()) || cost.getGenericManaAmount() <= 0) continue;
            ManaCostShard shard = ManaCostShard.valueOf((int)mask);
            cost.increaseShard(shard, 1);
            cost.decreaseGenericMana(1);
        }
    }

    private static String payMultipleMana(ManaCostBeingPaid testCost, String mana, Player p) {
        ArrayList<String> unused = new ArrayList<String>(4);
        block0: for (String manaPart : TextUtil.split((CharSequence)mana, (char)' ')) {
            boolean wasNeeded;
            if (StringUtils.isNumeric((CharSequence)manaPart)) {
                for (int i = Integer.parseInt(manaPart); i > 0; --i) {
                    wasNeeded = testCost.ai_payMana("1", p.getManaPool());
                    if (wasNeeded) continue;
                    unused.add(Integer.toString(i));
                    continue block0;
                }
                continue;
            }
            String color = MagicColor.toShortString((String)manaPart);
            wasNeeded = testCost.ai_payMana(color, p.getManaPool());
            if (wasNeeded) continue;
            unused.add(color);
        }
        return unused.isEmpty() ? null : StringUtils.join(unused, (char)' ');
    }

    private static ListMultimap<ManaCostShard, SpellAbility> groupAndOrderToPayShards(Player ai, ListMultimap<Integer, SpellAbility> manaAbilityMap, ManaCostBeingPaid cost) {
        ListMultimap res = MultimapBuilder.enumKeys(ManaCostShard.class).arrayListValues().build();
        if ((cost.getGenericManaAmount() > 0 || cost.hasAnyKind(512)) && manaAbilityMap.containsKey(64)) {
            res.putAll(ManaCostShard.GENERIC, manaAbilityMap.get(64));
        }
        for (ManaCostShard shard : cost.getDistinctShards()) {
            if (shard == ManaCostShard.S) {
                res.putAll(shard, manaAbilityMap.get(2048));
                continue;
            }
            if (shard.isOr2Generic()) {
                int colorKey = shard.getColorMask();
                if (manaAbilityMap.containsKey(colorKey)) {
                    res.putAll(shard, manaAbilityMap.get(colorKey));
                }
                if (!manaAbilityMap.containsKey(64)) continue;
                res.putAll(shard, manaAbilityMap.get(64));
                continue;
            }
            if (shard == ManaCostShard.GENERIC) continue;
            for (Integer colorint : manaAbilityMap.keySet()) {
                if (!ai.getManaPool().canPayForShardWithColor(shard, colorint.byteValue())) continue;
                for (SpellAbility sa : manaAbilityMap.get(colorint)) {
                    if (res.get(shard).contains(sa)) continue;
                    res.put(shard, sa);
                }
            }
        }
        return res;
    }

    public static ManaCostBeingPaid calculateManaCost(Cost cost, SpellAbility sa, Player payer, boolean test, int extraMana, boolean effect) {
        CostPartMana manapart;
        Cost payCosts;
        Card host = sa.getHostCard();
        Zone castFromBackup = null;
        if (test && sa.isSpell() && !host.isInZone(ZoneType.Stack)) {
            castFromBackup = host.getCastFrom();
            host.setCastFrom(host.getZone() != null ? host.getZone() : null);
        }
        if (test) {
            payCosts = CostAdjustment.adjust((Cost)cost, (SpellAbility)sa, (boolean)effect);
            if (!payer.getController().isAI()) {
                sa.setMaxWaterbend(null);
            }
        } else {
            payCosts = cost;
        }
        CostPartMana costPartMana = manapart = payCosts != null ? payCosts.getCostMana() : null;
        ManaCost mana = payCosts != null ? (manapart == null ? ManaCost.ZERO : manapart.getManaCostFor(sa)) : ManaCost.NO_COST;
        ManaCostBeingPaid manaCost = new ManaCostBeingPaid(mana);
        if (manaCost.getXcounter() > 0 || extraMana > 0) {
            String xColor;
            int manaToAdd = 0;
            int xCounter = manaCost.getXcounter();
            if (test && extraMana > 0) {
                int multiplicator = Math.max(xCounter, 1);
                manaToAdd = extraMana * multiplicator;
            } else {
                manaToAdd = AbilityUtils.calculateAmount((Card)host, (String)sa.getParamOrDefault("XAlternative", "X"), (CardTraitBase)sa) * xCounter;
            }
            if (manaToAdd < 1 && payCosts != null && payCosts.getCostMana().getXMin() > 0) {
                manaToAdd = 1;
            }
            if ((xColor = sa.getXColor()) == null) {
                xColor = "1";
            }
            if (host.hasKeyword("Spend only colored mana on X. No more than one mana of each color may be spent this way.")) {
                xColor = "WUBRGX";
            }
            if (xCounter > 0) {
                manaCost.setXManaCostPaid(manaToAdd / xCounter, xColor);
            } else {
                manaCost.increaseShard(ManaCostShard.parseNonGeneric((String)xColor), manaToAdd);
            }
            if (!test) {
                sa.setXManaCostPaid(Integer.valueOf(manaToAdd / xCounter));
            }
        }
        CostAdjustment.adjust((ManaCostBeingPaid)manaCost, (SpellAbility)sa, (Player)payer, null, (boolean)test, (boolean)effect);
        if ("NumTimes".equals(sa.getParam("Announce"))) {
            ManaCost mkCost = sa.getPayCosts().getTotalMana();
            ManaCost mCost = ManaCost.ZERO;
            for (int i = 0; i < 10; ++i) {
                ManaCostBeingPaid mcbp = new ManaCostBeingPaid(mCost = ManaCost.combine((ManaCost)mCost, (ManaCost)mkCost));
                if (ComputerUtilMana.canPayManaCost(mcbp, sa, sa.getActivatingPlayer(), true)) continue;
                host.setSVar("NumTimes", "Number$" + i);
                break;
            }
        }
        if (test && sa.isSpell() && !host.isInZone(ZoneType.Stack)) {
            host.setCastFrom(castFromBackup);
        }
        return manaCost;
    }

    public static int getAvailableManaEstimate(Player p) {
        return ComputerUtilMana.getAvailableManaEstimate(p, true);
    }

    public static int getAvailableManaEstimate(Player p, boolean checkPlayable) {
        int availableMana = 0;
        CardCollection srcs = CardLists.filter(p.getCardsIn(ZoneType.Battlefield), c -> !c.getManaAbilities().isEmpty());
        int maxProduced = 0;
        int producedWithCost = 0;
        boolean hasSourcesWithNoManaCost = false;
        for (Card src : srcs) {
            maxProduced = 0;
            for (SpellAbility ma : src.getManaAbilities()) {
                ma.setActivatingPlayer(p);
                if (checkPlayable && !ma.canPlay()) continue;
                int costsToActivate = ma.getPayCosts().getCostMana() != null ? ma.getPayCosts().getCostMana().convertAmount() : 0;
                int producedMana = ma.getParamOrDefault("Produced", "").split(" ").length;
                int producedAmount = AbilityUtils.calculateAmount((Card)src, (String)ma.getParamOrDefault("Amount", "1"), (CardTraitBase)ma);
                int producedTotal = producedMana * producedAmount - costsToActivate;
                if (costsToActivate > 0) {
                    producedWithCost += producedTotal;
                } else if (!hasSourcesWithNoManaCost) {
                    hasSourcesWithNoManaCost = true;
                }
                if (producedTotal <= maxProduced) continue;
                maxProduced = producedTotal;
            }
            availableMana += maxProduced;
        }
        availableMana += p.getManaPool().totalMana();
        if (producedWithCost > 0 && !hasSourcesWithNoManaCost) {
            availableMana -= producedWithCost;
        }
        return availableMana;
    }

    public static CardCollection getAvailableManaSources(Player ai, boolean checkPlayable) {
        CardCollectionView list = CardCollection.combine((CardCollectionView[])new CardCollectionView[]{ai.getCardsIn(ZoneType.Battlefield), ai.getCardsIn(ZoneType.Hand)});
        CardCollection manaSources = CardLists.filter(list, c -> {
            for (SpellAbility am : ComputerUtilMana.getAIPlayableMana(c)) {
                am.setActivatingPlayer(ai);
                if (checkPlayable && (!am.canPlay() || !am.checkRestrictions(ai))) continue;
                return true;
            }
            return false;
        });
        CardCollection sortedManaSources = new CardCollection();
        if (manaSources.isEmpty()) {
            return sortedManaSources;
        }
        CardCollection otherManaSources = new CardCollection();
        CardCollection useLastManaSources = new CardCollection();
        CardCollection colorlessManaSources = new CardCollection();
        CardCollection oneManaSources = new CardCollection();
        CardCollection twoManaSources = new CardCollection();
        CardCollection threeManaSources = new CardCollection();
        CardCollection fourManaSources = new CardCollection();
        CardCollection fiveManaSources = new CardCollection();
        CardCollection anyColorManaSources = new CardCollection();
        boolean canDieToTapDamage = ai.canLoseLife() && !ai.cantLoseForZeroOrLessLife();
        for (Card card : manaSources) {
            Combat combat;
            if (card.isCreature() && card.getGame().getPhaseHandler().is(PhaseType.COMBAT_DECLARE_ATTACKERS, ai) && (combat = card.getGame().getCombat()).getAttackers().indexOf(card) != -1 && !card.hasKeyword(Keyword.VIGILANCE)) continue;
            if (canDieToTapDamage) {
                boolean dealsLethalOnTap = false;
                for (Trigger t : card.getTriggers()) {
                    SpellAbility trigSa;
                    if (t.getMode() != TriggerType.Taps && t.getMode() != TriggerType.TapsForMana || (trigSa = t.getOverridingAbility()).getApi() != ApiType.DealDamage || !trigSa.getParamOrDefault("Defined", "").equals("You")) continue;
                    int numDamage = AbilityUtils.calculateAmount((Card)card, (String)trigSa.getParam("NumDmg"), null);
                    numDamage = ai.staticReplaceDamage(numDamage, card, false);
                    if (ai.getLife() > numDamage) continue;
                    dealsLethalOnTap = true;
                    break;
                }
                if (dealsLethalOnTap) continue;
            }
            if (card.isCreature() || card.isEnchanted()) {
                otherManaSources.add(card);
                continue;
            }
            int usableManaAbilities = 0;
            boolean needsLimitedResources = false;
            boolean unpreferredCost = false;
            boolean producesAnyColor = false;
            List<SpellAbility> manaAbilities = ComputerUtilMana.getAIPlayableMana(card);
            for (SpellAbility m : manaAbilities) {
                AbilitySub sub;
                Cost cost;
                if (m.getManaPart().isAnyMana()) {
                    producesAnyColor = true;
                }
                if ((cost = m.getPayCosts()) != null) {
                    m.setActivatingPlayer(ai);
                    if (!CostPayment.canPayAdditionalCosts((Cost)m.getPayCosts(), (SpellAbility)m, (boolean)false)) continue;
                    if (!cost.isReusuableResource()) {
                        for (CostPart part : cost.getCostParts()) {
                            if (!(part instanceof CostSacrifice) || part.payCostFromSource()) continue;
                            unpreferredCost = true;
                        }
                        boolean bl = needsLimitedResources = !unpreferredCost;
                    }
                }
                if ((sub = m.getSubAbility()) != null && !card.getName().equals("Pristine Talisman") && !card.getName().equals("Zhur-Taa Druid")) {
                    if (!SpellApiToAi.Converter.get((SpellAbility)sub).chkDrawbackWithSubs(ai, sub).willingToPlay()) continue;
                    needsLimitedResources = true;
                }
                ++usableManaAbilities;
            }
            if (unpreferredCost) {
                useLastManaSources.add(card);
                continue;
            }
            if (needsLimitedResources) {
                otherManaSources.add(card);
                continue;
            }
            if (producesAnyColor) {
                anyColorManaSources.add(card);
                continue;
            }
            if (usableManaAbilities == 1) {
                if (manaAbilities.get(0).getManaPart().mana(manaAbilities.get(0)).equals("C")) {
                    colorlessManaSources.add(card);
                    continue;
                }
                oneManaSources.add(card);
                continue;
            }
            if (usableManaAbilities == 2) {
                twoManaSources.add(card);
                continue;
            }
            if (usableManaAbilities == 3) {
                threeManaSources.add(card);
                continue;
            }
            if (usableManaAbilities == 4) {
                fourManaSources.add(card);
                continue;
            }
            fiveManaSources.add(card);
        }
        sortedManaSources.addAll(sortedManaSources.size(), colorlessManaSources);
        sortedManaSources.addAll(sortedManaSources.size(), oneManaSources);
        sortedManaSources.addAll(sortedManaSources.size(), twoManaSources);
        sortedManaSources.addAll(sortedManaSources.size(), threeManaSources);
        sortedManaSources.addAll(sortedManaSources.size(), fourManaSources);
        sortedManaSources.addAll(sortedManaSources.size(), fiveManaSources);
        sortedManaSources.addAll(sortedManaSources.size(), anyColorManaSources);
        ComputerUtilCard.sortByEvaluateCreature(otherManaSources);
        Collections.reverse(otherManaSources);
        sortedManaSources.addAll(sortedManaSources.size(), otherManaSources);
        ComputerUtilCard.sortByEvaluateCreature(useLastManaSources);
        Collections.reverse(useLastManaSources);
        sortedManaSources.addAll(sortedManaSources.size(), useLastManaSources);
        return sortedManaSources;
    }

    private static ListMultimap<Integer, SpellAbility> groupSourcesByManaColor(Player ai, boolean checkPlayable) {
        ArrayListMultimap manaMap = ArrayListMultimap.create();
        Game game = ai.getGame();
        for (Card sourceCard : ComputerUtilMana.getAvailableManaSources(ai, checkPlayable)) {
            for (SpellAbility m : ComputerUtilMana.getAIPlayableMana(sourceCard)) {
                AbilitySub sub;
                Cost abCost;
                m.setActivatingPlayer(ai);
                if (checkPlayable && !m.canPlay() || !ComputerUtilCost.checkLifeCost(ai, abCost = m.getPayCosts(), sourceCard, 1, m) || (sub = m.getSubAbility()) != null && !SpellApiToAi.Converter.get((SpellAbility)sub).chkDrawbackWithSubs(ai, sub).willingToPlay()) continue;
                manaMap.put(64, m);
                for (SpellAbility tail = m; tail != null; tail = tail.getSubAbility()) {
                    AbilityManaPart mp = tail.getManaPart();
                    if (mp == null || !tail.metConditions()) continue;
                    String origin = mp.getOrigProduced();
                    Map<AbilityKey, Object> repParams = AbilityKey.mapFromAffected((GameEntity)sourceCard);
                    repParams.put(AbilityKey.Mana, origin);
                    repParams.put(AbilityKey.Activator, ai);
                    repParams.put(AbilityKey.AbilityMana, m);
                    List<ReplacementEffect> reList = game.getReplacementHandler().getReplacementList(ReplacementType.ProduceMana, repParams, ReplacementLayer.Other);
                    if (reList.isEmpty()) {
                        Set reflectedColors = CardUtil.getReflectableManaColors((SpellAbility)m);
                        for (MagicColor.Color color : MagicColor.Color.values()) {
                            if (!mp.canProduce(color.getShortName(), tail) && !reflectedColors.contains(color.getName())) continue;
                            manaMap.put(ManaAtom.fromName((String)color.getName()), m);
                        }
                        continue;
                    }
                    for (ReplacementEffect re : reList) {
                        SpellAbility o = re.getOverridingAbility();
                        String replaced = origin;
                        if (o == null || o.getApi() != ApiType.ReplaceMana) continue;
                        if (o.hasParam("ReplaceMana")) {
                            replaced = o.getParam("ReplaceMana");
                        } else if (o.hasParam("ReplaceType")) {
                            String color = o.getParam("ReplaceType");
                            for (byte c : MagicColor.WUBRGC) {
                                String s = MagicColor.toShortString(c);
                                replaced = replaced.replace(s, color);
                            }
                        } else if (o.hasParam("ReplaceColor")) {
                            String color = o.getParam("ReplaceColor");
                            if (o.hasParam("ReplaceOnly")) {
                                replaced = replaced.replace(o.getParam("ReplaceOnly"), color);
                            } else {
                                for (byte c : MagicColor.WUBRG) {
                                    String s = MagicColor.toShortString(c);
                                    replaced = replaced.replace(s, color);
                                }
                            }
                        }
                        for (byte color : MagicColor.WUBRG) {
                            if (!"Any".equals(replaced) && !replaced.contains(MagicColor.toShortString((byte)color))) continue;
                            manaMap.put(color, m);
                        }
                        if (!replaced.contains("C")) continue;
                        manaMap.put(32, m);
                    }
                }
                if (!m.getHostCard().isSnow()) continue;
                manaMap.put(2048, m);
            }
        }
        return manaMap;
    }

    public static int determineLeftoverMana(SpellAbility sa, Player player, boolean effect) {
        int max = 99;
        if (sa.hasParam("XMax")) {
            max = Math.min(max, AbilityUtils.calculateAmount((Card)sa.getHostCard(), (String)sa.getParam("XMax"), (CardTraitBase)sa));
        }
        if (sa.hasParam("AIXMax")) {
            sa.setXManaCostPaid(Integer.valueOf(max));
            max = Math.min(max, AbilityUtils.calculateAmount((Card)sa.getHostCard(), (String)sa.getParam("AIXMax"), (CardTraitBase)sa));
        }
        for (int i = 1; i <= max; ++i) {
            if (ComputerUtilMana.canPayManaCost(sa.getRootAbility(), player, i, effect)) continue;
            return i - 1;
        }
        return max;
    }

    public static int determineLeftoverMana(SpellAbility sa, Player player, String shardColor, boolean effect) {
        ManaCost origCost = sa.getRootAbility().getPayCosts().getTotalMana();
        Object shardSurplus = shardColor;
        for (int i = 1; i < 100; ++i) {
            ManaCost extra = new ManaCost((String)shardSurplus);
            if (!ComputerUtilMana.canPayManaCost(new ManaCostBeingPaid(ManaCost.combine((ManaCost)origCost, (ManaCost)extra)), sa, player, effect)) {
                return i - 1;
            }
            shardSurplus = (String)shardSurplus + " " + shardColor;
        }
        return 99;
    }

    public static List<SpellAbility> getAIPlayableMana(Card c) {
        ArrayList<SpellAbility> res = new ArrayList<SpellAbility>();
        for (SpellAbility a : c.getManaAbilities()) {
            Cost cost = a.getPayCosts();
            if (a.getApi() != ApiType.Mana && a.getApi() != ApiType.ManaReflected || a.getRestrictions() != null && a.getRestrictions().isInstantSpeed() || res.contains(a)) continue;
            if (cost != null && cost.hasManaCost()) {
                if (!c.isInZone(ZoneType.Battlefield)) continue;
            }
            if (cost != null && cost.isReusuableResource()) {
                res.add(0, a);
                continue;
            }
            res.add(res.size(), a);
        }
        return res;
    }

    public static Map<Card, ManaCostShard> getConvokeOrImproviseFromList(ManaCost cost, List<Card> list, boolean artifacts, boolean creatures) {
        HashMap<Card, ManaCostShard> convoke = new HashMap<Card, ManaCostShard>();
        Card convoked = null;
        if (creatures && !artifacts) {
            for (ManaCostShard toPay : cost) {
                if (toPay.isSnow() || toPay.isColorless()) continue;
                for (Card c : list) {
                    int mask = c.getColor().getColor() & toPay.getColorMask();
                    if (mask == 0) continue;
                    convoked = c;
                    convoke.put(c, toPay);
                    break;
                }
                if (convoked != null) {
                    list.remove(convoked);
                }
                convoked = null;
            }
        }
        for (int i = 0; i < list.size() && i < cost.getGenericCost(); ++i) {
            convoke.put(list.get(i), ManaCostShard.GENERIC);
        }
        return convoke;
    }
}
