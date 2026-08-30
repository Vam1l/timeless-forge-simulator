/*
 * Decompiled with CFR 0.152.
 */
package forge.ai;

import com.google.common.collect.Iterables;
import com.google.common.collect.ListMultimap;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import com.google.common.collect.Multimap;
import forge.LobbyPlayer;
import forge.ai.AiAttackController;
import forge.ai.AiBlockController;
import forge.ai.AiCardMemory;
import forge.ai.AiController;
import forge.ai.AiCostDecision;
import forge.ai.AiPlayDecision;
import forge.ai.AiProps;
import forge.ai.ComputerUtil;
import forge.ai.ComputerUtilCard;
import forge.ai.ComputerUtilCombat;
import forge.ai.ComputerUtilCost;
import forge.ai.ComputerUtilMana;
import forge.ai.SpecialCardAi;
import forge.ai.SpellApiToAi;
import forge.ai.ability.ProtectAi;
import forge.card.CardStateName;
import forge.card.ColorSet;
import forge.card.ICardFace;
import forge.card.MagicColor;
import forge.card.mana.ManaCost;
import forge.card.mana.ManaCostShard;
import forge.deck.Deck;
import forge.deck.DeckSection;
import forge.game.CardTraitBase;
import forge.game.Game;
import forge.game.GameEntity;
import forge.game.GameObject;
import forge.game.GameOutcome;
import forge.game.GameType;
import forge.game.PlanarDice;
import forge.game.ability.AbilityUtils;
import forge.game.ability.ApiType;
import forge.game.ability.effects.CharmEffect;
import forge.game.ability.effects.RollDiceEffect;
import forge.game.card.Card;
import forge.game.card.CardCollection;
import forge.game.card.CardCollectionView;
import forge.game.card.CardLists;
import forge.game.card.CardPredicates;
import forge.game.card.CardState;
import forge.game.card.CardView;
import forge.game.card.CounterType;
import forge.game.combat.Combat;
import forge.game.cost.Cost;
import forge.game.cost.CostDecisionMakerBase;
import forge.game.cost.CostEnlist;
import forge.game.cost.CostPart;
import forge.game.cost.CostPartMana;
import forge.game.cost.CostPartWithList;
import forge.game.cost.CostPayment;
import forge.game.keyword.Keyword;
import forge.game.keyword.KeywordInterface;
import forge.game.mana.Mana;
import forge.game.mana.ManaConversionMatrix;
import forge.game.mana.ManaCostBeingPaid;
import forge.game.phase.PhaseHandler;
import forge.game.phase.PhaseType;
import forge.game.player.DelayedReveal;
import forge.game.player.Player;
import forge.game.player.PlayerActionConfirmMode;
import forge.game.player.PlayerController;
import forge.game.player.PlayerView;
import forge.game.replacement.ReplacementEffect;
import forge.game.spellability.AbilitySub;
import forge.game.spellability.OptionalCostValue;
import forge.game.spellability.Spell;
import forge.game.spellability.SpellAbility;
import forge.game.spellability.SpellAbilityStackInstance;
import forge.game.spellability.TargetChoices;
import forge.game.staticability.StaticAbility;
import forge.game.trigger.Trigger;
import forge.game.trigger.TriggerType;
import forge.game.trigger.WrappedAbility;
import forge.game.zone.PlayerZone;
import forge.game.zone.ZoneType;
import forge.item.PaperCard;
import forge.util.Aggregates;
import forge.util.ITriggerEvent;
import forge.util.IterableUtil;
import forge.util.MyRandom;
import forge.util.collect.FCollection;
import forge.util.collect.FCollectionView;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;
import java.util.function.Predicate;
import java.util.stream.Collectors;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.tuple.ImmutablePair;
import org.apache.commons.lang3.tuple.Pair;

public class PlayerControllerAi
extends PlayerController {
    private final AiController brains;
    private boolean pilotsNonAggroDeck = false;

    public PlayerControllerAi(Game game, Player p, LobbyPlayer lp) {
        super(game, p, lp);
        this.brains = new AiController(p, game);
    }

    public boolean pilotsNonAggroDeck() {
        return this.pilotsNonAggroDeck;
    }

    public void setupAutoProfile(Deck deck) {
        this.pilotsNonAggroDeck = deck.getName().contains("Control") || deck.getAverageCMC() > 3;
    }

    @Override
    public SpellAbility getAbilityToPlay(Card hostCard, List<SpellAbility> abilities, ITriggerEvent triggerEvent) {
        if (abilities.isEmpty()) {
            return null;
        }
        return abilities.get(0);
    }

    public AiController getAi() {
        return this.brains;
    }

    @Override
    public boolean isAI() {
        return true;
    }

    @Override
    public List<PaperCard> sideboard(Deck deck, GameType gameType, String message) {
        if (!this.brains.getGame().getRules().getAISideboardingEnabled() || !deck.has(DeckSection.Sideboard)) {
            return null;
        }
        HashMap<PaperCard, PaperCard> sideboardPlan = Maps.newHashMap();
        List<PaperCard> main = deck.get(DeckSection.Main).toFlatList();
        List sideboard = deck.get(DeckSection.Sideboard).toFlatList();
        boolean definedSideboardPlan = false;
        String sideboardAiHint = deck.getAiHint("SideboardingPlan");
        if (!sideboardAiHint.isEmpty()) {
            for (String element : sideboardAiHint.split(";")) {
                String[] cardPair = element.split("->");
                PaperCard src = null;
                PaperCard tgt = null;
                for (PaperCard cMain : main) {
                    if (!cMain.getCardName().equals(cardPair[0].trim())) continue;
                    src = cMain;
                    break;
                }
                for (PaperCard cSide : (List<PaperCard>)(List<?>)sideboard) {
                    if (!cSide.getCardName().equals(cardPair[1].trim())) continue;
                    tgt = cSide;
                    break;
                }
                if (src == null || tgt == null) continue;
                sideboardPlan.put(src, tgt);
            }
            if (!sideboardPlan.isEmpty()) {
                definedSideboardPlan = true;
            }
        }
        boolean sbLimitedFormats = this.getAi().getBoolProperty(AiProps.SIDEBOARDING_IN_LIMITED_FORMATS);
        boolean sbSharedTypesOnly = this.getAi().getBoolProperty(AiProps.SIDEBOARDING_SHARED_TYPE_ONLY);
        boolean sbPlaneswalkerException = this.getAi().getBoolProperty(AiProps.SIDEBOARDING_PLANESWALKER_EQ_CREATURE);
        int sbChanceOnWin = this.getAi().getIntProperty(AiProps.SIDEBOARDING_CHANCE_ON_WIN);
        int sbChancePerCard = this.getAi().getIntProperty(AiProps.SIDEBOARDING_CHANCE_PER_CARD);
        if (!sbLimitedFormats && gameType.isCardPoolLimited()) {
            return null;
        }
        GameOutcome lastOutcome = this.brains.getGame().getMatch().getLastOutcome();
        if (lastOutcome.getWinningPlayer().getPlayer().equals(this.player.getLobbyPlayer()) && MyRandom.getRandom().nextInt(100) > sbChanceOnWin) {
            return null;
        }
        if (!definedSideboardPlan) {
            ArrayList<PaperCard> processed = Lists.newArrayList();
            block3: for (PaperCard cSide : (List<PaperCard>)(List<?>)sideboard) {
                if (processed.contains(cSide) || cSide.getRules().getAiHints().getRemAIDecks() || cSide.getRules().getType().isLand()) continue;
                for (PaperCard cMain : main) {
                    if (processed.contains(cMain) || cMain.getName().equals(cSide.getName()) || cMain.getRules().getType().isLand() || (!sbSharedTypesOnly ? (cMain.getRules().getType().isCreature() && !cSide.getRules().getType().isCreature() || cSide.getRules().getType().isCreature() && !cMain.getRules().getType().isCreature()) && (!sbPlaneswalkerException || !cMain.getRules().getType().isPlaneswalker() && !cSide.getRules().getType().isPlaneswalker()) : !cMain.getRules().getType().sharesCardTypeWith(cSide.getRules().getType()))) continue;
                    if (!Card.fromPaperCard(cMain, this.player).getManaAbilities().isEmpty()) {
                        processed.add(cMain);
                        continue;
                    }
                    if (!cSide.getRules().getColor().hasNoColorsExcept(cMain.getRules().getColor()) || cMain.getRules().getManaCost().getCMC() != cSide.getRules().getManaCost().getCMC()) continue;
                    sideboardPlan.put(cMain, cSide);
                    processed.add(cSide);
                    processed.add(cMain);
                    continue block3;
                }
            }
        }
        for (Map.Entry ent : sideboardPlan.entrySet()) {
            if (!definedSideboardPlan && MyRandom.getRandom().nextInt(100) < sbChancePerCard) continue;
            long inMain = main.stream().filter(pc -> ((PaperCard)pc).getName().equals(((PaperCard)ent.getKey()).getName())).count();
            long inSide = sideboard.stream().filter(pc -> ((PaperCard)pc).getName().equals(((PaperCard)ent.getValue()).getName())).count();
            while (inMain-- > 0L && inSide-- > 0L) {
                sideboard.remove(ent.getValue());
                sideboard.add((PaperCard)ent.getKey());
                main.add((PaperCard)ent.getValue());
                main.remove(ent.getKey());
            }
        }
        return main;
    }

    @Override
    public Map<Card, Integer> assignCombatDamage(Card attacker, CardCollectionView blockers, CardCollectionView remaining, int damageDealt, GameEntity defender, boolean overrideOrder) {
        return ComputerUtilCombat.distributeAIDamage(this.player, attacker, blockers, remaining, damageDealt, defender, overrideOrder);
    }

    @Override
    public Map<GameEntity, Integer> divideShield(Card effectSource, Map<GameEntity, Integer> affected, int shieldAmount) {
        return new HashMap<GameEntity, Integer>();
    }

    @Override
    public Map<Byte, Integer> specifyManaCombo(SpellAbility sa, ColorSet colorSet, int manaAmount, boolean different) {
        HashMap<Byte, Integer> result = new HashMap<Byte, Integer>();
        for (int i = 0; i < manaAmount; ++i) {
            Byte chosen = this.chooseColor("", sa, colorSet);
            result.merge(chosen, 1, Integer::sum);
            if (!different) continue;
            colorSet = ColorSet.fromMask(colorSet.getColor() - chosen);
        }
        return result;
    }

    @Override
    public Integer announceRequirements(SpellAbility ability, int min2, int max, String announce) {
        if (ability.getApi() != null) {
            switch (ability.getApi()) {
                case ChooseNumber: {
                    Player payingPlayer = ability.getActivatingPlayer();
                    String logic = ability.getParamOrDefault("AILogic", "");
                    boolean anyController = logic.equals("MaxForAnyController");
                    if (logic.startsWith("PowerLeakMaxMana.") && ability.getHostCard().isEnchantingCard()) {
                        payingPlayer = ability.getHostCard().getEnchantingCard().getController();
                    }
                    int number = ComputerUtilMana.determineLeftoverMana(ability, this.player, false);
                    if (logic.startsWith("MaxMana.") || logic.startsWith("PowerLeakMaxMana.")) {
                        number = Math.min(number, Integer.parseInt(logic.substring(logic.indexOf(".") + 1)));
                    }
                    return payingPlayer.isOpponentOf(this.player) && !anyController ? 0 : number;
                }
                case BidLife: {
                    return 0;
                }
            }
            return null;
        }
        return null;
    }

    @Override
    public CardCollectionView choosePermanentsToSacrifice(SpellAbility sa, int min2, int max, CardCollectionView validTargets, String message) {
        return ComputerUtil.choosePermanentsToSacrifice(this.player, validTargets, max, sa, false, min2 == 0);
    }

    @Override
    public CardCollectionView choosePermanentsToDestroy(SpellAbility sa, int min2, int max, CardCollectionView validTargets, String message) {
        return ComputerUtil.choosePermanentsToSacrifice(this.player, validTargets, max, sa, true, min2 == 0);
    }

    @Override
    public CardCollectionView chooseCardsForEffect(CardCollectionView sourceList, SpellAbility sa, String title, int min2, int max, boolean isOptional, Map<String, Object> params) {
        return this.brains.chooseCardsForEffect(sourceList, sa, min2, max, isOptional, params);
    }

    @Override
    public List<Card> chooseContraptionsToCrank(List<Card> contraptions) {
        return CardLists.filter(contraptions, c -> {
            Trigger crankTrigger = IterableUtil.find(c.getTriggers(), t2 -> t2.getMode() == TriggerType.CrankContraption);
            return this.confirmTrigger(new WrappedAbility(crankTrigger, crankTrigger.getOverridingAbility(), this.player));
        });
    }

    @Override
    public boolean helpPayForAssistSpell(ManaCostBeingPaid cost, SpellAbility sa, int max, int requested) {
        int toPay = this.getAi().attemptToAssist(sa, max, requested);
        if (toPay == 0) {
            return true;
        }
        ManaCost manaCost = ManaCost.get(toPay);
        ManaCostBeingPaid assistCost = new ManaCostBeingPaid(manaCost);
        if (ComputerUtilMana.canPayManaCost(assistCost, sa, this.player, false)) {
            ComputerUtilMana.payManaCost(assistCost, sa, this.player, false);
            cost.decreaseGenericMana(toPay);
            return true;
        }
        return true;
    }

    @Override
    public Player choosePlayerToAssistPayment(FCollectionView<Player> optionList, SpellAbility sa, String title, int max) {
        return null;
    }

    @Override
    public <T extends GameEntity> T chooseSingleEntityForEffect(FCollectionView<T> optionList, DelayedReveal delayedReveal, SpellAbility sa, String title, boolean isOptional, Player targetedPlayer, Map<String, Object> params) {
        if (delayedReveal != null) {
            this.reveal(delayedReveal);
        }
        return SpellApiToAi.Converter.get(sa).chooseSingleEntity(this.player, sa, optionList, isOptional, targetedPlayer, params);
    }

    @Override
    public <T extends GameEntity> List<T> chooseEntitiesForEffect(FCollectionView<T> optionList, int min2, int max, DelayedReveal delayedReveal, SpellAbility sa, String title, Player targetedPlayer, Map<String, Object> params) {
        T selected;
        if (delayedReveal != null) {
            this.reveal(delayedReveal);
        }
        FCollection<T> remaining = new FCollection<T>(optionList);
        ArrayList<T> selecteds = new ArrayList<T>();
        do {
            if ((selected = this.chooseSingleEntityForEffect(remaining, null, sa, title, selecteds.size() >= min2, targetedPlayer, params)) == null) continue;
            remaining.remove(selected);
            selecteds.add(selected);
        } while (selected != null && selecteds.size() < max);
        return selecteds;
    }

    @Override
    public List<SpellAbility> chooseSpellAbilitiesForEffect(List<SpellAbility> spells, SpellAbility sa, String title, int num, Map<String, Object> params) {
        SpellAbility selected;
        ArrayList<SpellAbility> remaining = Lists.newArrayList(spells);
        ArrayList<SpellAbility> selecteds = Lists.newArrayList();
        do {
            if ((selected = this.chooseSingleSpellForEffect(remaining, sa, title, params)) == null) continue;
            remaining.remove(selected);
            selecteds.add(selected);
        } while (selected != null && selecteds.size() < num);
        return selecteds;
    }

    @Override
    public SpellAbility chooseSingleSpellForEffect(List<SpellAbility> spells, SpellAbility sa, String title, Map<String, Object> params) {
        return SpellApiToAi.Converter.get(sa).chooseSingleSpellAbility(this.player, sa, spells, params);
    }

    @Override
    public boolean confirmAction(SpellAbility sa, PlayerActionConfirmMode mode, String message, List<String> options, Card cardToShow, Map<String, Object> params) {
        return this.getAi().confirmAction(sa, mode, message, params);
    }

    @Override
    public boolean confirmBidAction(SpellAbility sa, PlayerActionConfirmMode mode, String string, int bid, Player winner) {
        return this.getAi().confirmBidAction(sa, mode, string, bid, winner);
    }

    @Override
    public boolean confirmStaticApplication(Card hostCard, PlayerActionConfirmMode mode, String message, String logic) {
        return this.getAi().confirmStaticApplication(hostCard, logic);
    }

    public boolean acceptsDrawOffer() {
        return false;
    }

    @Override
    public boolean confirmTrigger(WrappedAbility wrapper) {
        SpellAbility sa = wrapper.getWrappedAbility();
        if (wrapper.isMandatory()) {
            return true;
        }
        TargetChoices tc = null;
        TargetChoices subtc = null;
        boolean storeChoices = sa.usesTargeting();
        AbilitySub sub = sa.getSubAbility();
        boolean storeSubChoices = sub != null && sub.usesTargeting();
        boolean ret = true;
        if (storeChoices) {
            tc = sa.getTargets();
            sa.resetTargets();
        }
        if (storeSubChoices) {
            subtc = sub.getTargets();
            sub.resetTargets();
        }
        if (!this.brains.doTrigger(sa, false)) {
            ret = false;
        }
        if (storeChoices) {
            sa.resetTargets();
            sa.setTargets(tc);
        }
        if (storeSubChoices) {
            sub.resetTargets();
            sub.setTargets(subtc);
        }
        return ret;
    }

    @Override
    public boolean confirmPayment(CostPart costPart, String prompt, SpellAbility sa) {
        return this.brains.confirmPayment(costPart);
    }

    @Override
    public boolean confirmReplacementEffect(ReplacementEffect replacementEffect, SpellAbility effectSA, GameEntity affected, String question) {
        Card host = replacementEffect.getHostCard();
        if (host.hasAlternateState()) {
            host = host.getGame().getCardState(host);
        }
        if (effectSA != null) {
            effectSA.setActivatingPlayer(host.getController());
        }
        return this.brains.aiShouldRun(replacementEffect, effectSA, host, affected);
    }

    @Override
    public List<Card> exertAttackers(List<Card> attackers) {
        return AiAttackController.exertAttackers(attackers, this.brains.getAttackAggression());
    }

    @Override
    public List<Card> enlistAttackers(List<Card> attackers) {
        CardCollection cards = CostEnlist.getCardsForEnlisting(this.brains.getPlayer());
        cards = CardLists.filter((Iterable<Card>)cards, CardPredicates.hasGreaterPowerThan(0));
        CardCollection chosenAttackers = new CardCollection((Iterable<Card>)attackers);
        ComputerUtilCard.sortByEvaluateCreature(chosenAttackers);
        if (attackers.size() > cards.size()) {
            chosenAttackers = chosenAttackers.subList(0, cards.size());
        }
        return chosenAttackers;
    }

    @Override
    public CardCollection orderBlockers(Card attacker, CardCollection blockers) {
        return AiBlockController.orderBlockers(attacker, blockers);
    }

    @Override
    public CardCollection orderBlocker(Card attacker, Card blocker, CardCollection oldBlockers) {
        return AiBlockController.orderBlocker(attacker, blocker, oldBlockers);
    }

    @Override
    public CardCollection orderAttackers(Card blocker, CardCollection attackers) {
        return AiBlockController.orderAttackers(blocker, attackers);
    }

    @Override
    public void reveal(CardCollectionView cards, ZoneType zone, Player owner, String messagePrefix, boolean addSuffix) {
        for (Card c : cards) {
            AiCardMemory.rememberCard(this.player, c, AiCardMemory.MemorySet.REVEALED_CARDS);
        }
    }

    @Override
    public void reveal(List<CardView> cards, ZoneType zone, PlayerView owner, String messagePrefix, boolean addSuffix) {
        for (CardView cv : cards) {
            AiCardMemory.rememberCard(this.player, this.player.getGame().findByView(cv), AiCardMemory.MemorySet.REVEALED_CARDS);
        }
    }

    @Override
    public ImmutablePair<CardCollection, CardCollection> arrangeForScry(CardCollection topN) {
        CardCollection toBottom = new CardCollection();
        CardCollection toTop = new CardCollection();
        for (Card c : topN) {
            if (ComputerUtil.scryWillMoveCardToBottomOfLibrary(this.player, c)) {
                toBottom.add(c);
                continue;
            }
            toTop.add(c);
        }
        CardLists.shuffle(toTop);
        return ImmutablePair.of(toTop, toBottom);
    }

    @Override
    public ImmutablePair<CardCollection, CardCollection> arrangeForSurveil(CardCollection topN) {
        CardCollection toGraveyard = new CardCollection();
        CardCollection toTop = new CardCollection();
        if (this.getPlayer().getCardsIn(ZoneType.Library).size() <= this.getAi().getIntProperty(AiProps.SURVEIL_NUM_CARDS_IN_LIBRARY_TO_BAIL)) {
            toTop.addAll(topN);
        } else {
            for (Card c : topN) {
                if (ComputerUtil.scryWillMoveCardToBottomOfLibrary(this.player, c)) {
                    toGraveyard.add(c);
                    continue;
                }
                toTop.add(c);
            }
        }
        CardLists.shuffle(toTop);
        return ImmutablePair.of(toTop, toGraveyard);
    }

    @Override
    public boolean willPutCardOnTop(Card c) {
        return !ComputerUtil.scryWillMoveCardToBottomOfLibrary(this.player, c);
    }

    @Override
    public CardCollectionView orderMoveToZoneList(CardCollectionView cards, ZoneType destinationZone, SpellAbility source) {
        if (cards.isEmpty()) {
            return cards;
        }
        if (destinationZone == ZoneType.Graveyard) {
            if (this.getGame().getCardsInGame().anyMatch(card -> card.getOriginalState(CardStateName.Original).getName().equals("Volrath's Shapeshifter"))) {
                int bestValue = 0;
                Object bestCreature = null;
                for (Object c : cards) {
                    int curValue = ComputerUtilCard.evaluateCreature((Card)c);
                    if (!((Card)c).isCreature() || curValue <= bestValue) continue;
                    bestValue = curValue;
                    bestCreature = c;
                }
                if (bestCreature != null) {
                    CardCollection reordered = new CardCollection();
                    for (Card c : cards) {
                        if (c.equals(bestCreature)) continue;
                        reordered.add(c);
                    }
                    reordered.add((Card)bestCreature);
                    return reordered;
                }
            }
        } else if (destinationZone == ZoneType.Library) {
            Player p = ((Card)cards.getFirst()).getController();
            CardCollection reordered = new CardCollection();
            CardCollection topLands = new CardCollection();
            CardCollection topNonLands = new CardCollection();
            CardCollection bottom = new CardCollection();
            for (Card c : cards) {
                if (ComputerUtil.scryWillMoveCardToBottomOfLibrary(p, c)) {
                    bottom.add(c);
                    continue;
                }
                if (c.isLand()) {
                    topLands.add(c);
                    continue;
                }
                topNonLands.add(c);
            }
            int landsOTB = CardLists.count(p.getCardsIn(ZoneType.Battlefield), CardPredicates.LANDS_PRODUCING_MANA);
            if (!p.isOpponentOf(this.player)) {
                if (landsOTB <= 2) {
                    reordered.addAll(topLands);
                    topLands.clear();
                } else if (!topLands.isEmpty()) {
                    Card first = (Card)topLands.getFirst();
                    reordered.add(first);
                    topLands.remove(first);
                }
                reordered.addAll(topNonLands);
                reordered.addAll(topLands);
                reordered.addAll(bottom);
            } else {
                reordered.addAll(bottom);
                if (landsOTB <= 5) {
                    reordered.addAll(topNonLands);
                    reordered.addAll(topLands);
                } else {
                    reordered.addAll(topLands);
                    reordered.addAll(topNonLands);
                }
            }
            if (this.orderedMoveToTopOfLibrary(destinationZone, source)) {
                Collections.reverse(reordered);
            }
            assert (reordered.size() == cards.size());
            return reordered;
        }
        return cards;
    }

    @Override
    public CardCollection chooseCardsToDiscardFrom(Player p, SpellAbility sa, CardCollection validCards, int min2, int max, CardCollectionView visibleToChooser) {
        if (p == this.player) {
            CardCollection filtered = new CardCollection(validCards);
            if (filtered.size() > min2) {
                CardCollectionView hand = p.getCardsIn(ZoneType.Hand);
                long handHpCount = hand.stream().filter(c -> "Hunting Pack".equals(c.getName())).count();
                long libHpCount = p.getCardsIn(ZoneType.Library).stream().filter(c -> "Hunting Pack".equals(c.getName())).count();
                if (handHpCount + libHpCount <= 1 || handHpCount == 1) {
                    filtered.removeIf(c -> "Hunting Pack".equals(c.getName()));
                }
                boolean facesCreatures = p.getOpponents().stream().anyMatch(opp ->
                    opp.getCreaturesInPlay().size() > 0 ||
                    !CardLists.filter(opp.getCardsIn(ZoneType.Graveyard), CardPredicates.CREATURES).isEmpty() ||
                    !CardLists.filter(opp.getCardsIn(ZoneType.Library), CardPredicates.CREATURES).isEmpty()
                );
                if (facesCreatures) {
                    long psCount = hand.stream().filter(c -> "Prismatic Strands".equals(c.getName())).count();
                    if (psCount <= 1) {
                        filtered.removeIf(c -> "Prismatic Strands".equals(c.getName()));
                    }
                }
            }
            if (filtered.size() >= min2) {
                return this.brains.getCardsToDiscard(min2, max, filtered, sa);
            }
            if (sa != null) {
                String saHostName = sa.getHostCard() != null ? sa.getHostCard().getName() : "";
                if ("Bitter Reunion".equals(saHostName) || (sa.getParam("AILogic") != null && sa.getParam("AILogic").contains("Discard"))) {
                    return new CardCollection();
                }
            }
            if (min2 == 0) {
                return new CardCollection();
            }
            return this.brains.getCardsToDiscard(min2, max, validCards, sa);
        }
        boolean isTargetFriendly = !p.isOpponentOf(this.player);
        return isTargetFriendly ? ComputerUtil.getCardsToDiscardFromFriend(this.player, p, sa, validCards, min2, max) : ComputerUtil.getCardsToDiscardFromOpponent(this.player, p, sa, validCards, min2, max);
    }

    @Override
    public void playSpellAbilityNoStack(SpellAbility effectSA, boolean canSetupTargets) {
        if (canSetupTargets) {
            this.brains.doTrigger(effectSA, true);
        }
        ComputerUtil.playNoStack(this.player, effectSA, this.getGame(), true);
    }

    @Override
    public CardCollectionView chooseCardsToDelve(int genericAmount, CardCollection grave) {
        return this.getAi().chooseCardsToDelve(genericAmount, grave);
    }

    @Override
    public CardCollectionView chooseCardsToDiscardUnlessType(int num, CardCollectionView hand, String[] uTypes, SpellAbility sa) {
        Iterable<Card> cardsOfType = IterableUtil.filter(hand, CardPredicates.restriction(uTypes, sa.getActivatingPlayer(), sa.getHostCard(), (CardTraitBase)sa));
        if (!Iterables.isEmpty(cardsOfType)) {
            Card toDiscard = Aggregates.itemWithMin(cardsOfType, Card::getCMC);
            return new CardCollection(toDiscard);
        }
        return this.getAi().getCardsToDiscard(num, null, sa);
    }

    @Override
    public Mana chooseManaFromPool(List<Mana> manaChoices) {
        return manaChoices.get(0);
    }

    @Override
    public String chooseSomeType(String kindOfType, SpellAbility sa, Collection<String> validTypes, boolean isOptional) {
        if ("Color".equals(kindOfType) && sa != null && sa.getHostCard() != null && "Prismatic Strands".equals(sa.getHostCard().getName())) {
            Combat combat = this.player.getGame().getCombat();
            CardCollection oppAttackers = (combat != null && combat.getAttackers() != null)
                    ? CardLists.filterControlledBy(combat.getAttackers(), this.player.getOpponents())
                    : new CardCollection();
            if (!oppAttackers.isEmpty()) {
                int maxColorDmg = -1;
                String bestCol = null;
                for (String colName : (validTypes != null && !validTypes.isEmpty() ? validTypes : MagicColor.Constant.ONLY_COLORS)) {
                    byte colMask = MagicColor.fromName(colName);
                    int colDmg = 0;
                    for (Card c : oppAttackers) {
                        if ((c.getColor().getColor() & colMask) != 0) {
                            colDmg += Math.max(0, c.getNetPower());
                        }
                    }
                    if (colDmg > maxColorDmg && colDmg > 0) {
                        maxColorDmg = colDmg;
                        bestCol = colName;
                    }
                }
                if (bestCol != null) {
                    return bestCol;
                }
            }
            int maxPwr = -1;
            String bestCol = null;
            CardCollection oppCards = this.player.getOpponents().getCardsIn(ZoneType.Battlefield);
            for (String colName : (validTypes != null && !validTypes.isEmpty() ? validTypes : MagicColor.Constant.ONLY_COLORS)) {
                byte colMask = MagicColor.fromName(colName);
                int totalPwr = 0;
                for (Card c : oppCards) {
                    if (c.isCreature() && (c.getColor().getColor() & colMask) != 0) {
                        totalPwr += Math.max(0, c.getNetPower());
                    }
                }
                if (totalPwr > maxPwr && totalPwr > 0) {
                    maxPwr = totalPwr;
                    bestCol = colName;
                }
            }
            if (bestCol != null) {
                return bestCol;
            }
        }
        String chosen = ComputerUtil.chooseSomeType(this.player, kindOfType, sa, validTypes);
        if (StringUtils.isBlank(chosen) && !validTypes.isEmpty()) {
            chosen = validTypes.iterator().next();
        }
        return chosen;
    }

    @Override
    public Object vote(SpellAbility sa, String prompt, List<Object> options, ListMultimap<Object, Player> votes, Player forPlayer, boolean optional) {
        return ComputerUtil.vote(this.player, options, sa, votes, forPlayer);
    }

    @Override
    public String chooseSector(Card assignee, String ai, List<String> sectors) {
        return Aggregates.random(sectors);
    }

    @Override
    public int chooseSprocket(Card assignee, List<Integer> sprockets) {
        int nextSprocket = this.player.getCrankCounter() % 3 + 1;
        if (sprockets.contains(nextSprocket)) {
            return nextSprocket;
        }
        if (sprockets.contains(nextSprocket % 3 + 1)) {
            return nextSprocket % 3 + 1;
        }
        return sprockets.stream().findAny().orElse(0);
    }

    @Override
    public PlanarDice choosePDRollToIgnore(List<PlanarDice> rolls) {
        return Aggregates.random(rolls);
    }

    @Override
    public Integer chooseRollToIgnore(List<Integer> rolls) {
        return Aggregates.random(rolls);
    }

    @Override
    public List<Integer> chooseDiceToReroll(List<Integer> rolls) {
        return new ArrayList<Integer>();
    }

    @Override
    public Integer chooseRollToModify(List<Integer> rolls) {
        return Aggregates.random(rolls);
    }

    @Override
    public RollDiceEffect.DieRollResult chooseRollToSwap(List<RollDiceEffect.DieRollResult> rolls) {
        return Aggregates.random(rolls);
    }

    @Override
    public String chooseRollSwapValue(List<String> swapChoices, Integer currentResult, int power, int toughness) {
        return Aggregates.random(swapChoices);
    }

    @Override
    public boolean mulliganKeepHand(Player firstPlayer, int cardsToReturn) {
        return !ComputerUtil.wantMulligan(this.player, cardsToReturn);
    }

    @Override
    public CardCollectionView tuckCardsViaMulligan(CardCollectionView hand, int cardsToReturn) {
        int numLandsDesired = (this.player.getStartingHandSize() - cardsToReturn) / 2;
        CardCollection toReturn = new CardCollection();
        for (int i = 0; i < cardsToReturn; ++i) {
            hand.removeAll(toReturn);
            CardCollection landsInHand = CardLists.filter((Iterable<Card>)hand, CardPredicates.LANDS);
            int numLandsInHand = landsInHand.size() - CardLists.count(toReturn, CardPredicates.LANDS);
            if (numLandsInHand > 0 && numLandsInHand > numLandsDesired) {
                CardCollection producingLands = CardLists.filter((Iterable<Card>)landsInHand, CardPredicates.LANDS_PRODUCING_MANA);
                CardCollection nonProducingLands = CardLists.filter((Iterable<Card>)landsInHand, CardPredicates.LANDS_PRODUCING_MANA.negate());
                Card worstLand = nonProducingLands.isEmpty() ? ComputerUtilCard.getWorstLand(producingLands) : ComputerUtilCard.getWorstLand(nonProducingLands);
                toReturn.add(worstLand);
                continue;
            }
            CardCollection scryBottom = new CardCollection();
            for (Card c : hand) {
                if (c.isLand() || toReturn.contains(c) || this.willPutCardOnTop(c)) continue;
                scryBottom.add(c);
            }
            if (!scryBottom.isEmpty()) {
                CardLists.sortByCmcDesc(scryBottom);
                toReturn.add((Card)scryBottom.getFirst());
                continue;
            }
            toReturn.add(ComputerUtilCard.getWorstAI(hand));
        }
        return CardCollection.getView(toReturn);
    }

    @Override
    public void declareAttackers(Player attacker, Combat combat) {
        this.brains.declareAttackers(attacker, combat);
    }

    @Override
    public void declareBlockers(Player defender, Combat combat) {
        this.brains.declareBlockersFor(defender, combat);
    }

    @Override
    public List<SpellAbility> chooseSpellAbilityToPlay() {
        return this.brains.chooseSpellAbilityToPlay();
    }

    @Override
    public boolean playChosenSpellAbility(SpellAbility sa) {
        if (sa.isLandAbility()) {
            if (sa.canPlay()) {
                sa.resolve();
            }
        } else {
            ComputerUtil.handlePlayingSpellAbility(this.player, sa, this.getDeferredTargetingPlayerAction(sa));
        }
        return true;
    }

    private Consumer<SpellAbility> getDeferredTargetingPlayerAction(SpellAbility sa) {
        while (sa != null) {
            if (sa.hasParam("TargetingPlayer") && sa.getTargetingPlayer() != null) {
                return root -> {
                    for (SpellAbility cur = root; cur != null; cur = cur.getSubAbility()) {
                        if (!cur.hasParam("TargetingPlayer") || cur.getTargetingPlayer() == null) continue;
                        cur.clearTargets();
                        cur.getTargetingPlayer().getController().chooseTargetsFor(cur);
                        if (ComputerUtilCost.canPayCost(root, root.getActivatingPlayer(), false)) continue;
                        cur.resetTargets();
                        root.setSkip(true);
                        return;
                    }
                };
            }
            sa = sa.getSubAbility();
        }
        return null;
    }

    @Override
    public CardCollectionView chooseCardsToDiscardToMaximumHandSize(int numDiscard) {
        CardCollection validCards = new CardCollection(this.player.getCardsIn(ZoneType.Hand));
        CardCollection filtered = new CardCollection(validCards);
        if (filtered.size() > numDiscard) {
            long handHpCount = validCards.stream().filter(c -> "Hunting Pack".equals(c.getName())).count();
            long libHpCount = this.player.getCardsIn(ZoneType.Library).stream().filter(c -> "Hunting Pack".equals(c.getName())).count();
            if (handHpCount + libHpCount <= 1 || handHpCount == 1) {
                filtered.removeIf(c -> "Hunting Pack".equals(c.getName()));
            }
            boolean facesCreatures = this.player.getOpponents().stream().anyMatch(opp ->
                opp.getCreaturesInPlay().size() > 0 ||
                !CardLists.filter(opp.getCardsIn(ZoneType.Graveyard), CardPredicates.CREATURES).isEmpty() ||
                !CardLists.filter(opp.getCardsIn(ZoneType.Library), CardPredicates.CREATURES).isEmpty()
            );
            if (facesCreatures) {
                long psCount = validCards.stream().filter(c -> "Prismatic Strands".equals(c.getName())).count();
                if (psCount <= 1) {
                    filtered.removeIf(c -> "Prismatic Strands".equals(c.getName()));
                }
            }
        }
        if (filtered.size() >= numDiscard) {
            return this.brains.getCardsToDiscard(numDiscard, numDiscard, filtered, null);
        }
        return this.brains.getCardsToDiscard(numDiscard, null, null);
    }

    @Override
    public CardCollectionView chooseCardsToRevealFromHand(int min2, int max, CardCollectionView valid) {
        int numCardsToReveal = Math.min(max, valid.size());
        return numCardsToReveal == 0 ? CardCollection.EMPTY : (CardCollection)valid.subList(0, numCardsToReveal);
    }

    @Override
    public Player chooseStartingPlayer(boolean isFirstGame) {
        return this.player;
    }

    @Override
    public PlayerZone chooseStartingHand(List<PlayerZone> zones) {
        int bestScore = Integer.MIN_VALUE;
        PlayerZone bestZone = null;
        for (PlayerZone zone : zones) {
            int score = ComputerUtil.scoreHand(zone.getCards(), this.player, 0);
            if (score <= bestScore) continue;
            bestScore = score;
            bestZone = zone;
        }
        return bestZone;
    }

    @Override
    public List<SpellAbility> chooseSaToActivateFromOpeningHand(List<SpellAbility> usableFromOpeningHand) {
        return this.brains.chooseSaToActivateFromOpeningHand(usableFromOpeningHand);
    }

    @Override
    public int chooseNumber(SpellAbility sa, String title, int min2, int max) {
        return this.brains.chooseNumber(sa, title, min2, max);
    }

    @Override
    public int chooseNumber(SpellAbility sa, String string, int min2, int max, Map<String, Object> params) {
        return SpellApiToAi.Converter.get(sa).chooseNumber(this.player, sa, min2, max, params);
    }

    @Override
    public int chooseNumber(SpellAbility sa, String title, List<Integer> options, Player relatedPlayer) {
        return this.brains.chooseNumber(sa, title, options, relatedPlayer);
    }

    @Override
    public boolean chooseFlipResult(SpellAbility sa, Player flipper, boolean call) {
        if (call) {
            return true;
        }
        return MyRandom.getRandom().nextBoolean();
    }

    @Override
    public Pair<SpellAbilityStackInstance, GameObject> chooseTarget(SpellAbility saSrc, List<Pair<SpellAbilityStackInstance, GameObject>> allTargets) {
        return allTargets.get(0);
    }

    @Override
    public void notifyOfValue(SpellAbility saSource, GameObject realtedTarget, String value) {
    }

    @Override
    public boolean chooseBinary(SpellAbility sa, String question, PlayerController.BinaryChoiceType kindOfChoice, Boolean defaultVal) {
        switch (kindOfChoice) {
            case TapOrUntap: {
                return true;
            }
            case UntapOrLeaveTapped: {
                Card source = sa.getHostCard();
                if (source != null && source.hasSVar("AIUntapPreference")) {
                    switch (source.getSVar("AIUntapPreference")) {
                        case "Always": {
                            return true;
                        }
                        case "Never": {
                            return false;
                        }
                        case "NothingRemembered": {
                            if (!source.hasRemembered()) {
                                return true;
                            }
                            Card rem = (Card)source.getFirstRemembered();
                            if (rem.isInPlay()) break;
                            return true;
                        }
                        case "BetterTgtThanRemembered": {
                            if (!source.hasGainControlTarget()) break;
                            Card rem = (Card)source.getGainControlTargets().get(0);
                            if (!rem.isInPlay() || rem.getController().isOpponentOf(source.getController())) {
                                return true;
                            }
                            for (Card c : source.getController().getCreaturesInPlay()) {
                                if (c == rem || ComputerUtilCard.evaluateCreature(c) <= ComputerUtilCard.evaluateCreature(rem) + 30) continue;
                                return true;
                            }
                            return false;
                        }
                    }
                }
                return defaultVal != null && defaultVal != false;
            }
            case LeftOrRight: {
                return this.brains.chooseDirection(sa);
            }
            case OddsOrEvens: {
                return this.brains.chooseEvenOdd(sa);
            }
            case HeadsOrTails: {
                return true;
            }
        }
        return MyRandom.getRandom().nextBoolean();
    }

    @Override
    public boolean chooseBinary(SpellAbility sa, String question, PlayerController.BinaryChoiceType kindOfChoice, Map<String, Object> params) {
        return SpellApiToAi.Converter.get(sa).chooseBinary(kindOfChoice, sa, params);
    }

    @Override
    public List<AbilitySub> chooseModeForAbility(SpellAbility sa, List<AbilitySub> possible, int min2, int num, boolean allowRepeat) {
        List<AbilitySub> result = this.brains.chooseModeForAbility(sa, possible, min2, num, allowRepeat);
        if (result != null) {
            return result;
        }
        if (sa.getChosenList() == null) {
            this.getAi().doTrigger(sa, true);
        }
        return sa.getChosenList();
    }

    @Override
    public byte chooseColorAllowColorless(String message, Card card, ColorSet colors) {
        String c = ComputerUtilCard.getMostProminentColor(this.player.getCardsIn(ZoneType.Hand));
        byte chosenColorMask = MagicColor.fromName(c);
        if ((colors.getColor() & chosenColorMask) != 0) {
            return chosenColorMask;
        }
        return Iterables.getFirst(colors, MagicColor.Color.COLORLESS).getColorMask();
    }

    @Override
    public byte chooseColor(String message, SpellAbility sa, ColorSet colors) {
        if (sa != null && sa.getHostCard() != null && "Prismatic Strands".equals(sa.getHostCard().getName())) {
            Player p = this.player;
            Game game = p.getGame();
            Combat combat = game.getCombat();
            if (combat != null && !combat.getAttackers().isEmpty()) {
                CardCollection oppAttackers = CardLists.filterControlledBy(combat.getAttackers(), p.getOpponents());
                if (!oppAttackers.isEmpty()) {
                    int maxColorDamage = -1;
                    byte bestColorMask = 0;
                    for (byte color : MagicColor.WUBRG) {
                        if ((colors.getColor() & color) != 0) {
                            int colDmg = 0;
                            for (Card c : oppAttackers) {
                                if ((c.getColor().getColor() & color) != 0) {
                                    colDmg += Math.max(0, c.getNetPower());
                                }
                            }
                            if (colDmg > maxColorDamage && colDmg > 0) {
                                maxColorDamage = colDmg;
                                bestColorMask = color;
                            }
                        }
                    }
                    if (bestColorMask != 0) {
                        return bestColorMask;
                    }
                }
            }
            int maxPower = -1;
            byte bestColorMask = 0;
            for (Player opp : p.getOpponents()) {
                for (Card creature : opp.getCreaturesInPlay()) {
                    int pwr = creature.getNetPower();
                    byte col = creature.getColor().getColor();
                    if (pwr > maxPower && (colors.getColor() & col) != 0) {
                        maxPower = pwr;
                        bestColorMask = col;
                    }
                }
            }
            if (bestColorMask != 0) {
                return bestColorMask;
            }
        }
        if (colors.countColors() < 2) {
            return Iterables.getFirst(colors, MagicColor.Color.WHITE).getColorMask();
        }
        CardCollectionView hand = this.player.getCardsIn(ZoneType.Hand);
        if (sa.getApi() == ApiType.Mana) {
            hand = CardCollection.combine(hand, this.player.getCardsIn(ZoneType.Stack));
        }
        String c = ComputerUtilCard.getMostProminentColor(hand);
        byte chosenColorMask = MagicColor.fromName(c);
        if ((colors.getColor() & chosenColorMask) != 0) {
            return chosenColorMask;
        }
        return Iterables.getFirst(colors, MagicColor.Color.WHITE).getColorMask();
    }

    @Override
    public ColorSet chooseColors(String message, SpellAbility sa, int min2, int max, ColorSet options) {
        return ColorSet.fromNames(ComputerUtilCard.chooseColor(sa, min2, max, options.stream().map(MagicColor.Color::getName).collect(Collectors.toList())));
    }

    @Override
    public CounterType chooseCounterType(List<CounterType> options, SpellAbility sa, String prompt, Map<String, Object> params) {
        if (options.size() <= 1) {
            return Iterables.getFirst(options, null);
        }
        return SpellApiToAi.Converter.get(sa).chooseCounterType(options, sa, params);
    }

    @Override
    public String chooseKeywordForPump(List<String> options, SpellAbility sa, String prompt, Card tgtCard) {
        if (options.size() <= 1) {
            return Iterables.getFirst(options, null);
        }
        ArrayList<String> possible = Lists.newArrayList();
        CardCollection oppUntappedCreatures = CardLists.filter((Iterable<Card>)this.player.getOpponents().getCreaturesInPlay(), CardPredicates.UNTAPPED);
        if (tgtCard != null) {
            for (String kw : options) {
                if (tgtCard.hasKeyword(kw)) continue;
                if ("Indestructible".equals(kw)) {
                    if (oppUntappedCreatures.isEmpty()) continue;
                    possible.clear();
                    possible.add(kw);
                    break;
                }
                if ("Flying".equals(kw)) {
                    if (oppUntappedCreatures.isEmpty()) continue;
                    boolean flyingGood = true;
                    for (Card c : oppUntappedCreatures) {
                        if (!c.hasKeyword(Keyword.FLYING) && !c.hasKeyword(Keyword.REACH)) continue;
                        flyingGood = false;
                        break;
                    }
                    if (flyingGood) {
                        possible.clear();
                        possible.add(kw);
                        break;
                    }
                } else if (kw.startsWith("Protection from ")) {
                    String fromWhat = kw.substring(16);
                    boolean found = false;
                    block2: for (String color : MagicColor.Constant.ONLY_COLORS) {
                        if (!color.equalsIgnoreCase(fromWhat)) continue;
                        CardCollection known = this.player.getOpponents().getCardsIn(ZoneType.Battlefield);
                        for (Card c : known) {
                            if (!c.associatedWithColor(color)) continue;
                            found = true;
                            continue block2;
                        }
                    }
                    if (!found) continue;
                }
                possible.add(kw);
            }
        }
        if (!possible.isEmpty()) {
            return (String)Aggregates.random(possible);
        }
        return Aggregates.random(options);
    }

    @Override
    public ReplacementEffect chooseSingleReplacementEffect(List<ReplacementEffect> possibleReplacers) {
        return this.brains.chooseSingleReplacementEffect(possibleReplacers);
    }

    @Override
    public StaticAbility chooseSingleStaticAbility(List<StaticAbility> possibleStatics) {
        return Iterables.getFirst(possibleStatics, null);
    }

    @Override
    public String chooseProtectionType(SpellAbility sa, List<String> choices) {
        AiAttackController aiAtk;
        PhaseHandler ph;
        Combat combat;
        String s2;
        String choice = choices.get(0);
        SpellAbility hostsa = null;
        if (this.getGame().stack.size() > 1) {
            for (SpellAbilityStackInstance si : this.getGame().getStack()) {
                SpellAbility spell = si.getSpellAbility();
                if (sa == spell || sa.getHostCard() == spell.getHostCard()) continue;
                s2 = ProtectAi.toProtectFrom(spell.getHostCard(), sa);
                if (s2 == null) break;
                return s2;
            }
        }
        if ((combat = this.getGame().getCombat()) != null) {
            SpellAbility topstack;
            if (this.getGame().stack.size() == 1 && (topstack = this.getGame().stack.peekAbility()).getSubAbility() == sa) {
                hostsa = topstack;
            }
            Card toSave = hostsa == null ? sa.getTargetCard() : hostsa.getTargetCard();
            FCollection threats = null;
            if (toSave != null) {
                if (combat.isBlocked(toSave)) {
                    threats = combat.getBlockers(toSave);
                }
                if (combat.isBlocking(toSave)) {
                    threats = combat.getAttackersBlockedBy(toSave);
                }
            }
            if (threats != null && !threats.isEmpty()) {
                ComputerUtilCard.sortByEvaluateCreature((CardCollection)threats);
                s2 = ProtectAi.toProtectFrom((Card)threats.get(0), sa);
                if (s2 != null) {
                    return s2;
                }
            }
        }
        if ((ph = this.getGame().getPhaseHandler()).getPlayerTurn() == sa.getActivatingPlayer() && ph.getPhase() == PhaseType.MAIN1 && sa.getTargetCard() != null && (s2 = (aiAtk = new AiAttackController(sa.getActivatingPlayer(), sa.getTargetCard())).toProtectAttacker(sa)) != null) {
            return s2;
        }
        String logic = sa.getParam("AILogic");
        if (logic == null || logic.equals("MostProminentHumanCreatures")) {
            CardCollection list = this.player.getOpponents().getCreaturesInPlay();
            if (list.isEmpty()) {
                list = CardLists.filterControlledBy((Iterable<Card>)this.getGame().getCardsInGame(), this.player.getOpponents());
            }
            if (!list.isEmpty()) {
                choice = ComputerUtilCard.getMostProminentColor(list);
            }
        }
        return choice;
    }

    @Override
    public boolean payManaCost(ManaCost toPay, CostPartMana costPartMana, SpellAbility sa, String prompt, ManaConversionMatrix matrix, boolean effect) {
        return ComputerUtilMana.payManaCost(new Cost(toPay, effect), this.player, sa, effect);
    }

    @Override
    public boolean payCombatCost(Card c, Cost cost, SpellAbility sa, String prompt) {
        return ComputerUtil.playNoStack(c.getController(), sa, this.getGame(), true);
    }

    @Override
    public CardCollectionView chooseCardsForCost(CardCollectionView optionList, SpellAbility sa, CostPartWithList cpl, int amount, boolean isOptional, String prompt) {
        assert (false);
        return cpl.accept(new AiCostDecision((Player)this.player, (SpellAbility)sa, (boolean)true)).cards;
    }

    @Override
    public boolean applyManaToCost(ManaCostBeingPaid toPay, SpellAbility ability, String prompt, ManaConversionMatrix matrix, boolean effect) {
        assert (false);
        return ComputerUtilMana.payManaCost(toPay, ability, this.player, effect);
    }

    @Override
    public CostDecisionMakerBase getCostDecisionMaker(Player player, SpellAbility ability, boolean effect, String prompt) {
        return new AiCostDecision(player, ability, effect);
    }

    @Override
    public boolean payCostToPreventEffect(Cost cost, SpellAbility sa, boolean alreadyPaid, FCollectionView<Player> allPayers) {
        if (SpellApiToAi.Converter.get(sa).willPayUnlessCost(this.player, sa, cost, alreadyPaid, allPayers)) {
            if (!ComputerUtilCost.canPayCost(cost, sa, this.player, true)) {
                return false;
            }
            CostPayment pay = new CostPayment(cost, sa);
            return pay.payComputerCosts(new AiCostDecision(this.player, sa, true));
        }
        return false;
    }

    @Override
    public boolean payCostDuringRoll(Cost cost, SpellAbility sa) {
        return false;
    }

    @Override
    public List<SpellAbility> orderSimultaneousSa(List<SpellAbility> activePlayerSAs) {
        return this.getAi().orderPlaySa(activePlayerSAs);
    }

    @Override
    public void orderAndPlaySimultaneousSa(List<SpellAbility> activePlayerSAs) {
        for (SpellAbility sa : this.orderSimultaneousSa(activePlayerSAs)) {
            if (sa.isTrigger() && !sa.isCopied()) {
                if (!this.prepareSingleSa(sa.getHostCard(), sa, true)) continue;
                ComputerUtil.playStack(sa, this.player, this.getGame());
                continue;
            }
            if (sa.isCopied()) {
                if (sa.isSpell()) {
                    if (!sa.getHostCard().isInZone(ZoneType.Stack)) {
                        sa.setHostCard(this.getGame().getAction().moveToStack(sa.getHostCard(), sa));
                    } else {
                        this.getGame().getStackZone().add(sa.getHostCard());
                    }
                }
                if (sa.isMayChooseNewTargets()) {
                    TargetChoices tc = sa.getTargets();
                    if (!sa.setupTargets()) {
                        sa.setTargets(tc);
                    }
                }
            }
            this.getGame().getStack().add(sa);
        }
    }

    private boolean prepareSingleSa(Card host, SpellAbility sa, boolean isMandatory) {
        if (sa.getApi() == ApiType.Charm) {
            if (!CharmEffect.makeChoices(sa)) {
                return false;
            }
            if (!sa.hasParam("Random")) {
                return true;
            }
            sa = sa.getSubAbility();
        }
        if (sa.hasParam("TargetingPlayer")) {
            Player targetingPlayer = (Player)AbilityUtils.getDefinedPlayers(host, sa.getParam("TargetingPlayer"), sa).get(0);
            sa.setTargetingPlayer(targetingPlayer);
            return targetingPlayer.getController().chooseTargetsFor(sa);
        }
        return this.brains.doTrigger(sa, isMandatory);
    }

    @Override
    public boolean playTrigger(Card host, WrappedAbility wrapperAbility, boolean isMandatory) {
        if (this.prepareSingleSa(host, wrapperAbility, isMandatory)) {
            return ComputerUtil.playNoStack(wrapperAbility.getActivatingPlayer(), wrapperAbility, this.getGame(), true);
        }
        return false;
    }

    @Override
    public boolean playSaFromPlayEffect(SpellAbility tgtSA) {
        boolean optional = !tgtSA.getPayCosts().isMandatory();
        boolean noManaCost = tgtSA.hasParam("WithoutManaCost");
        if (tgtSA instanceof Spell) {
            Spell spell = (Spell)tgtSA;
            if (this.brains.canPlayFromEffectAI(spell, !optional, noManaCost) == AiPlayDecision.WillPlay || !optional) {
                return ComputerUtil.playStack(tgtSA, this.player, this.getGame());
            }
            return false;
        }
        return true;
    }

    @Override
    public boolean chooseTargetsFor(SpellAbility currentAbility) {
        return this.brains.doTrigger(currentAbility, true);
    }

    @Override
    public TargetChoices chooseNewTargetsFor(SpellAbility ability, Predicate<GameObject> filter, boolean optional) {
        return null;
    }

    @Override
    public boolean chooseCardsPile(SpellAbility sa, CardCollectionView pile1, CardCollectionView pile2, String faceUp) {
        if (faceUp.equals("True")) {
            return pile1.size() >= pile2.size();
        }
        if (faceUp.equals("One")) {
            return pile1.size() >= pile2.size();
        }
        boolean allCreatures = IterableUtil.all(Iterables.concat(pile1, pile2), CardPredicates.CREATURES);
        int cmc1 = allCreatures ? ComputerUtilCard.evaluateCreatureList(pile1) : ComputerUtilCard.evaluatePermanentList(pile1);
        int cmc2 = allCreatures ? ComputerUtilCard.evaluateCreatureList(pile2) : ComputerUtilCard.evaluatePermanentList(pile2);
        return "Worst".equals(sa.getParam("AILogic")) ^ cmc1 >= cmc2;
    }

    @Override
    public void revealAnte(String message, Multimap<Player, PaperCard> removedAnteCards) {
    }

    @Override
    public void revealAISkipCards(String message, Map<Player, Map<DeckSection, List<? extends PaperCard>>> deckCards) {
    }

    @Override
    public void revealUnsupported(Map<Player, List<PaperCard>> unsupported) {
    }

    @Override
    public Map<DeckSection, List<? extends PaperCard>> complainCardsCantPlayWell(Deck myDeck) {
        this.setupAutoProfile(myDeck);
        return this.brains.complainCardsCantPlayWell(myDeck);
    }

    @Override
    public CardCollectionView cheatShuffle(CardCollectionView list) {
        return this.brains.cheatShuffle(list);
    }

    @Override
    public List<PaperCard> chooseCardsYouWonToAddToDeck(List<PaperCard> losses) {
        return losses;
    }

    @Override
    public Map<Card, ManaCostShard> chooseCardsForConvokeOrImprovise(SpellAbility sa, ManaCost manaCost, CardCollectionView untappedCards, boolean artifacts, boolean creatures, Integer maxReduction) {
        Player ai = sa.getActivatingPlayer();
        PhaseHandler ph = ai.getGame().getPhaseHandler();
        CardCollection untapped = CardLists.filter((Iterable<Card>)untappedCards, c -> c.getManaAbilities().isEmpty());
        if (ph.isPlayerTurn(ai) && ph.getPhase().isBefore(PhaseType.COMBAT_DECLARE_ATTACKERS)) {
            if (!creatures) {
                untapped = CardLists.filter((Iterable<Card>)untapped, c -> !c.isCreature());
            } else {
                return new HashMap<Card, ManaCostShard>();
            }
        }
        if (ph.isPlayerTurn(ai) && ph.getPhase().isAfter(PhaseType.COMBAT_BEGIN) || !ph.isPlayerTurn(ai) && ph.getPhase().isBefore(PhaseType.COMBAT_DECLARE_BLOCKERS)) {
            CardCollectionView blockers = ComputerUtil.protectRecursion(sa, () -> ComputerUtilCard.getLikelyBlockers(ai, null), CardCollection.EMPTY);
            untapped.removeAll(blockers);
            if (!ai.getGame().getStack().isEmpty() && !blockers.isEmpty()) {
                List<GameObject> objects = ComputerUtil.predictThreatenedObjects(ai, null);
                for (Card c2 : blockers) {
                    if (objects.contains(c2) && (creatures || c2.isArtifact())) {
                        untapped.add(c2);
                    }
                    if (maxReduction == null || untapped.size() < maxReduction) continue;
                    break;
                }
            }
        }
        return ComputerUtilMana.getConvokeOrImproviseFromList(manaCost, untapped, artifacts, creatures);
    }

    @Override
    public String chooseCardName(SpellAbility sa, List<ICardFace> faces, String message) {
        return SpellApiToAi.Converter.get(sa).chooseCardName(this.player, sa, faces);
    }

    @Override
    public String chooseCardName(SpellAbility sa, Predicate<ICardFace> cpp, String valid, String message) {
        if (sa.hasParam("AILogic")) {
            CardCollectionView aiLibrary = this.player.getCardsIn(ZoneType.Library);
            CardCollectionView oppLibrary = this.player.getStrongestOpponent().getCardsIn(ZoneType.Library);
            Card source = sa.getHostCard();
            String logic = sa.getParam("AILogic");
            if (!valid.isEmpty()) {
                aiLibrary = CardLists.getValidCards((Iterable<Card>)aiLibrary, valid, source.getController(), source, (CardTraitBase)sa);
                oppLibrary = CardLists.getValidCards((Iterable<Card>)oppLibrary, valid, source.getController(), source, (CardTraitBase)sa);
            }
            if (source != null && source.getState(CardStateName.Original).hasKeyword(Keyword.HIDDEN_AGENDA)) {
                for (Card consp : this.player.getCardsIn(ZoneType.Command)) {
                    String chosenName;
                    if (!consp.getState(CardStateName.Original).hasKeyword(Keyword.HIDDEN_AGENDA) || (chosenName = consp.getNamedCard()).isEmpty()) continue;
                    aiLibrary = CardLists.filter((Iterable<Card>)aiLibrary, CardPredicates.nameNotEquals(chosenName));
                }
            }
            String name = "";
            if (logic.equals("MostProminentInComputerDeck")) {
                name = ComputerUtilCard.getMostProminentCardName(aiLibrary);
            } else if (logic.equals("MostProminentInHumanDeck")) {
                name = ComputerUtilCard.getMostProminentCardName(oppLibrary);
            } else if (logic.equals("MostProminentCreatureInComputerDeck")) {
                CardCollection cards = CardLists.getValidCards((Iterable<Card>)aiLibrary, "Creature", this.player, sa.getHostCard(), (CardTraitBase)sa);
                name = ComputerUtilCard.getMostProminentCardName(cards);
            } else if (logic.equals("BestCreatureInComputerDeck")) {
                Card bestCreature = ComputerUtilCard.getBestCreatureAI(aiLibrary);
                name = bestCreature != null ? bestCreature.getName() : "";
            } else if (logic.equals("RandomInComputerDeck")) {
                name = aiLibrary.isEmpty() ? "" : Aggregates.random(aiLibrary).getName();
            } else if (logic.equals("MostProminentSpellInComputerDeck")) {
                CardCollection cards = CardLists.getValidCards((Iterable<Card>)aiLibrary, "Card.Instant,Card.Sorcery", this.player, sa.getHostCard(), (CardTraitBase)sa);
                name = ComputerUtilCard.getMostProminentCardName(cards);
            } else if (logic.equals("CursedScroll")) {
                name = SpecialCardAi.CursedScroll.chooseCard(this.player, sa);
            } else if (logic.equals("PithingNeedle") || logic.equals("PhyrexianRevoker") || logic.equals("SorcerousSpyglass")) {
                name = SpecialCardAi.PithingNeedle.chooseCard(this.player, sa);
            }
            if (!StringUtils.isBlank(name)) {
                return name;
            }
        } else {
            CardCollection list = CardLists.filterControlledBy((Iterable<Card>)this.getGame().getCardsInGame(), this.player.getOpponents());
            if (!(list = CardLists.filter((Iterable<Card>)list, CardPredicates.NON_LANDS)).isEmpty()) {
                return ((Card)list.get(0)).getName();
            }
        }
        return "Morphling";
    }

    @Override
    public Card chooseSingleCardForZoneChange(ZoneType destination, List<ZoneType> origin, SpellAbility sa, CardCollection fetchList, DelayedReveal delayedReveal, String selectPrompt, boolean isOptional, Player decider) {
        if (delayedReveal != null) {
            this.reveal(delayedReveal);
        }
        return this.brains.chooseCardToHiddenOriginChangeZone(destination, origin, sa, fetchList, this.player, decider);
    }

    @Override
    public List<Card> chooseCardsForZoneChange(ZoneType destination, List<ZoneType> origin, SpellAbility sa, CardCollection fetchList, int min2, int max, DelayedReveal delayedReveal, String selectPrompt, Player decider) {
        return null;
    }

    @Override
    public void resetAtEndOfTurn() {
        this.getAi().getCardMemory().clearAllRemembered();
    }

    @Override
    public void autoPassCancel() {
    }

    @Override
    public void awaitNextInput() {
    }

    @Override
    public void cancelAwaitNextInput() {
    }

    @Override
    public ICardFace chooseSingleCardFace(SpellAbility sa, List<ICardFace> faces, String message) {
        return SpellApiToAi.Converter.get(sa).chooseCardFace(this.player, sa, faces);
    }

    @Override
    public ICardFace chooseSingleCardFace(SpellAbility sa, String message, Predicate<ICardFace> cpp, String name) {
        throw new UnsupportedOperationException("Should not be called for AI");
    }

    @Override
    public CardState chooseSingleCardState(SpellAbility sa, List<CardState> states, String message, Map<String, Object> params) {
        return SpellApiToAi.Converter.get(sa).chooseCardState(this.player, sa, states, params);
    }

    @Override
    public List<Card> chooseCardsForSplice(SpellAbility sa, List<Card> cards) {
        CardLists.sortByCmcDesc(cards);
        ArrayList<Card> result = Lists.newArrayList();
        SpellAbility oldSA = sa;
        for (Card c : cards) {
            SpellAbility newSA = oldSA.copy();
            AbilityUtils.addSpliceEffect(newSA, c);
            if (AiPlayDecision.WillPlay != this.getAi().canPlayFromEffectAI((Spell)newSA, false, false)) continue;
            oldSA = newSA;
            result.add(c);
        }
        return result;
    }

    @Override
    public List<OptionalCostValue> chooseOptionalCosts(SpellAbility chosen, List<OptionalCostValue> optionalCostValues) {
        return SpellApiToAi.Converter.get(chosen).chooseOptionalCosts(this.player, chosen, optionalCostValues);
    }

    @Override
    public int chooseNumberForKeywordCost(SpellAbility sa, Cost cost, KeywordInterface keyword, String prompt, int max) {
        if (sa.hasOptionalKeywordAmount(keyword)) {
            return Math.min(sa.getOptionalKeywordAmount(keyword), max);
        }
        if (keyword.getKeyword() == Keyword.CASUALTY && "true".equalsIgnoreCase(sa.getHostCard().getSVar("AINoCasualtyPayment"))) {
            return 0;
        }
        int chosenAmount = 0;
        Cost costSoFar = sa.getPayCosts().copy();
        for (int i = 0; i < max; ++i) {
            costSoFar.add(cost);
            SpellAbility fullCostSa = sa.copyWithDefinedCost(costSoFar);
            if (!ComputerUtilCost.canPayCost(fullCostSa, this.player, sa.isTrigger())) break;
            ++chosenAmount;
        }
        return chosenAmount;
    }

    @Override
    public int chooseNumberForCostReduction(SpellAbility sa, int min2, int max) {
        return max;
    }

    @Override
    public List<CostPart> orderCosts(List<CostPart> costs) {
        return costs;
    }

    @Override
    public CardCollection chooseCardsForEffectMultiple(Map<String, CardCollection> validMap, SpellAbility sa, String title, boolean isOptional) {
        CardCollection choices = new CardCollection();
        for (String mapKey : validMap.keySet()) {
            CardCollection cc = validMap.get(mapKey);
            cc.removeAll(choices);
            Card chosen = ComputerUtilCard.getBestAI(cc);
            if (chosen == null) continue;
            choices.add(chosen);
        }
        return choices;
    }
}

