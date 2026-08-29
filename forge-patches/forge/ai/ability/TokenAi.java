/*
 * Decompiled with CFR 0.152.
 * 
 * Could not load the following classes:
 *  com.google.common.collect.Iterables
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
 *  forge.game.card.CardLists
 *  forge.game.card.CardPredicates
 *  forge.game.card.CardUtil
 *  forge.game.card.CounterEnumType
 *  forge.game.card.CounterType
 *  forge.game.card.token.TokenInfo
 *  forge.game.combat.Combat
 *  forge.game.combat.CombatUtil
 *  forge.game.cost.Cost
 *  forge.game.cost.CostDraw
 *  forge.game.cost.CostPart
 *  forge.game.cost.CostPutCounter
 *  forge.game.cost.CostRemoveCounter
 *  forge.game.keyword.Keyword
 *  forge.game.phase.PhaseHandler
 *  forge.game.phase.PhaseType
 *  forge.game.player.Player
 *  forge.game.player.PlayerActionConfirmMode
 *  forge.game.player.PlayerCollection
 *  forge.game.player.PlayerPredicates
 *  forge.game.spellability.SpellAbility
 *  forge.game.spellability.TargetRestrictions
 *  forge.game.zone.Zone
 *  forge.game.zone.ZoneType
 *  forge.util.MyRandom
 *  forge.util.collect.FCollectionView
 */
package forge.ai.ability;

import com.google.common.collect.Iterables;
import forge.ai.AiAbilityDecision;
import forge.ai.AiPlayDecision;
import forge.ai.AiProfileUtil;
import forge.ai.AiProps;
import forge.ai.ComputerUtil;
import forge.ai.ComputerUtilCard;
import forge.ai.ComputerUtilCombat;
import forge.ai.ComputerUtilCost;
import forge.ai.ComputerUtilMana;
import forge.ai.SpellAbilityAi;
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
import forge.game.card.CardLists;
import forge.game.card.CardPredicates;
import forge.game.card.CardUtil;
import forge.game.card.CounterEnumType;
import forge.game.card.CounterType;
import forge.game.card.token.TokenInfo;
import forge.game.combat.Combat;
import forge.game.combat.CombatUtil;
import forge.game.cost.Cost;
import forge.game.cost.CostDraw;
import forge.game.cost.CostPart;
import forge.game.cost.CostPutCounter;
import forge.game.cost.CostRemoveCounter;
import forge.game.keyword.Keyword;
import forge.game.phase.PhaseHandler;
import forge.game.phase.PhaseType;
import forge.game.player.Player;
import forge.game.player.PlayerActionConfirmMode;
import forge.game.player.PlayerCollection;
import forge.game.player.PlayerPredicates;
import forge.game.spellability.SpellAbility;
import forge.game.spellability.TargetRestrictions;
import forge.game.zone.Zone;
import forge.game.zone.ZoneType;
import forge.util.MyRandom;
import forge.util.collect.FCollectionView;
import java.util.Map;
import java.util.function.Predicate;

public class TokenAi
extends SpellAbilityAi {
    @Override
    protected boolean checkPhaseRestrictions(Player ai, SpellAbility sa, PhaseHandler ph) {
        boolean tokenHasX;
        Card source = sa.getHostCard();
        if (source != null && (source.hasKeyword(Keyword.STORM) || "Hunting Pack".equals(source.getName()))) {
            if (ph.isPlayerTurn(ai)) {
                return ph.getPhase().isMain();
            } else {
                return ComputerUtil.aiLifeInDanger(ai, false, 0);
            }
        }
        boolean pwMinus = false;
        boolean pwPlus = false;
        if (sa.isPwAbility()) {
            for (CostPart c : sa.getPayCosts().getCostParts()) {
                if (c instanceof CostRemoveCounter) {
                    pwMinus = true;
                    break;
                }
                if (!(c instanceof CostPutCounter) || c.convertAmount() <= 0) continue;
                pwPlus = true;
                break;
            }
        }
        Card actualToken = TokenAi.spawnToken(ai, sa);
        String tokenAmount = sa.getParamOrDefault("TokenAmount", "1");
        String tokenPower = sa.getParamOrDefault("TokenPower", actualToken.getBasePowerString());
        String tokenToughness = sa.getParamOrDefault("TokenToughness", actualToken.getBaseToughnessString());
        boolean bl = tokenHasX = "X".equals(tokenAmount) || "X".equals(tokenPower) || "X".equals(tokenToughness);
        if (!tokenHasX && (actualToken == null || actualToken.isCreature() && actualToken.getNetToughness() < 1)) {
            return pwPlus || sa.getSubAbility() != null;
        }
        if (tokenHasX) {
            int x = AbilityUtils.calculateAmount((Card)sa.getHostCard(), (String)tokenAmount, (CardTraitBase)sa);
            if (source.getSVar("X").equals("Count$Converge")) {
                x = ComputerUtilMana.getConvergeCount(sa, ai);
            }
            if (sa.getSVar("X").equals("Count$xPaid")) {
                x = ComputerUtilCost.setMaxXValue(sa, ai, sa.isTrigger());
                sa.getRootAbility().setXManaCostPaid(Integer.valueOf(x));
            }
            if (x <= 0) {
                if ("RandomPT".equals(sa.getParam("AILogic"))) {
                    x = 1;
                } else {
                    return false;
                }
            }
        }
        if (this.canInterruptSacrifice(ai, sa, actualToken, tokenAmount)) {
            return true;
        }
        boolean haste = actualToken.hasKeyword(Keyword.HASTE);
        boolean oneShot = sa.getSubAbility() != null && sa.getSubAbility().getApi() == ApiType.DelayedTrigger;
        boolean isCreature = actualToken.isCreature();
        if (ph.getPhase().isBefore(PhaseType.MAIN2) && ph.isPlayerTurn(ai) && !haste && !sa.hasParam("ActivationPhases") && !ComputerUtil.castSpellInMain1(ai, sa)) {
            boolean buff = false;
            for (Card c : ai.getCardsIn(ZoneType.Battlefield)) {
                if (!isCreature || !"Creature".equals(c.getSVar("BuffedBy"))) continue;
                buff = true;
            }
            if (!buff && !pwMinus) {
                return false;
            }
        }
        if (!(!ph.isPlayerTurn(ai) && !ph.getPhase().isBefore(PhaseType.COMBAT_DECLARE_ATTACKERS) || sa.hasParam("ActivationPhases") || sa.hasParam("PlayerTurn") || TokenAi.isSorcerySpeed(sa, ai) || haste || pwMinus)) {
            return false;
        }
        return !ph.getPhase().isAfter(PhaseType.COMBAT_BEGIN) && ph.isPlayerTurn(ai) || !oneShot;
    }

    /*
     * Enabled force condition propagation
     * Lifted jumps to return sites
     */
    @Override
    protected AiAbilityDecision checkApiLogic(Player ai, SpellAbility sa) {
        Game game = ai.getGame();
        Player opp = ai.getWeakestOpponent();
        Card actualToken = TokenAi.spawnToken(ai, sa);
        if (actualToken.getType().isLegendary() && ai.isCardInPlay(actualToken.getName())) {
            return new AiAbilityDecision(0, AiPlayDecision.WouldDestroyLegend);
        }
        TargetRestrictions tgt = sa.getTargetRestrictions();
        if (tgt != null) {
            sa.resetTargets();
            if (actualToken.getType().hasSubtype("Role")) {
                if (!this.tgtRoleAura(ai, sa, actualToken, false)) return new AiAbilityDecision(0, AiPlayDecision.TargetingFailed);
                return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
            }
            if (tgt.canOnlyTgtOpponent() || "Opponent".equals(sa.getParam("AITgts"))) {
                if (!sa.canTarget((GameObject)opp)) return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
                sa.getTargets().add((GameObject)opp);
            } else if (sa.canTarget((GameObject)ai)) {
                sa.getTargets().add((GameObject)ai);
            } else {
                CardCollection list = CardLists.getTargetableCards((Iterable)ai.getOpponents().getCardsIn(ZoneType.Battlefield), (SpellAbility)sa);
                CardCollection betterList = CardLists.filter((Iterable)list, c -> c.getLethalDamage() == 1);
                if (!betterList.isEmpty()) {
                    list = betterList;
                }
                if (!(betterList = CardLists.getNotKeyword((Iterable)list, (Keyword)Keyword.TRAMPLE)).isEmpty()) {
                    list = betterList;
                }
                if (list.isEmpty()) return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
                sa.getTargets().add((GameObject)ComputerUtilCard.getBestCreatureAI((Iterable<Card>)list));
            }
        }
        double chance = (double)AiProfileUtil.getIntProperty(ai, AiProps.TOKEN_GENERATION_ABILITY_CHANCE) / 100.0;
        boolean alwaysFromPW = AiProfileUtil.getBoolProperty(ai, AiProps.TOKEN_GENERATION_ALWAYS_IF_FROM_PLANESWALKER);
        boolean alwaysOnOppAttack = AiProfileUtil.getBoolProperty(ai, AiProps.TOKEN_GENERATION_ALWAYS_IF_OPP_ATTACKS);
        if (sa.isPwAbility() && alwaysFromPW) {
            return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
        }
        if (game.getPhaseHandler().is(PhaseType.COMBAT_DECLARE_ATTACKERS) && game.getPhaseHandler().getPlayerTurn().isOpponentOf(ai) && game.getCombat() != null && !game.getCombat().getAttackers().isEmpty() && alwaysOnOppAttack && actualToken.isCreature()) {
            for (Card attacker : game.getCombat().getAttackers()) {
                if (!CombatUtil.canBlock((Card)attacker, (Card)actualToken)) continue;
                return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
            }
            return new AiAbilityDecision(0, AiPlayDecision.DoesntImpactCombat);
        }
        if (!((double)MyRandom.getRandom().nextFloat() <= chance)) return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
        return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
    }

    private boolean canInterruptSacrifice(Player ai, SpellAbility sa, Card token, String tokenAmount) {
        Game game = ai.getGame();
        if (game.getStack().isEmpty()) {
            return false;
        }
        SpellAbility topStack = game.getStack().peekAbility();
        if (topStack.getApi() != ApiType.Sacrifice) {
            return false;
        }
        int nTokens = AbilityUtils.calculateAmount((Card)sa.getHostCard(), (String)tokenAmount, (CardTraitBase)sa);
        String valid = topStack.getParamOrDefault("SacValid", "Card.Self");
        String num = sa.getParamOrDefault("Amount", "1");
        int nToSac = AbilityUtils.calculateAmount((Card)topStack.getHostCard(), (String)num, (CardTraitBase)topStack);
        CardCollection list = CardLists.getValidCards((Iterable)ai.getCardsIn(ZoneType.Battlefield), (String)valid, (Player)ai.getWeakestOpponent(), (Card)topStack.getHostCard(), (CardTraitBase)sa);
        if (!(list = CardLists.filter((Iterable)list, (Predicate)CardPredicates.canBeSacrificedBy((SpellAbility)topStack, (boolean)true))).isEmpty() && nTokens > 0 && list.size() == nToSac) {
            ComputerUtilCard.sortByEvaluateCreature(list);
            list.add(token);
            list = CardLists.getValidCards((Iterable)list, (String)valid, (Player)ai.getWeakestOpponent(), (Card)topStack.getHostCard(), (CardTraitBase)sa);
            list = CardLists.filter((Iterable)list, (Predicate)CardPredicates.canBeSacrificedBy((SpellAbility)topStack, (boolean)true));
            return ComputerUtilCard.evaluateCreature(token) < ComputerUtilCard.evaluateCreature((Card)list.get(0)) && list.contains(token);
        }
        return false;
    }

    @Override
    protected AiAbilityDecision doTriggerNoCost(Player ai, SpellAbility sa, boolean mandatory) {
        Card actualToken = TokenAi.spawnToken(ai, sa);
        TargetRestrictions tgt = sa.getTargetRestrictions();
        if (tgt != null) {
            sa.resetTargets();
            if (actualToken.getType().hasSubtype("Role")) {
                if (this.tgtRoleAura(ai, sa, actualToken, mandatory)) {
                    return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
                }
                return new AiAbilityDecision(0, AiPlayDecision.TargetingFailed);
            }
            if (sa.canTarget((GameObject)ai)) {
                sa.getTargets().add((GameObject)ai);
            } else if (mandatory || tgt.canOnlyTgtOpponent()) {
                PlayerCollection targetableOpps = ai.getOpponents().filter(PlayerPredicates.isTargetableBy((SpellAbility)sa));
                if (targetableOpps.isEmpty()) {
                    return new AiAbilityDecision(0, AiPlayDecision.TargetingFailed);
                }
                Player opp = targetableOpps.min(PlayerPredicates.compareByLife());
                sa.getTargets().add((GameObject)opp);
            } else {
                return new AiAbilityDecision(0, AiPlayDecision.TargetingFailed);
            }
        }
        String tokenPower = sa.getParamOrDefault("TokenPower", actualToken.getBasePowerString());
        String tokenToughness = sa.getParamOrDefault("TokenToughness", actualToken.getBaseToughnessString());
        String tokenAmount = sa.getParamOrDefault("TokenAmount", "1");
        Card source = sa.getHostCard();
        if ("X".equals(tokenAmount) || "X".equals(tokenPower) || "X".equals(tokenToughness)) {
            int x = AbilityUtils.calculateAmount((Card)source, (String)tokenAmount, (CardTraitBase)sa);
            if (sa.getSVar("X").equals("Count$xPaid") && x == 0) {
                x = ComputerUtilCost.setMaxXValue(sa, ai, true);
            }
            if (x <= 0 && !mandatory) {
                return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
            }
        }
        if (mandatory) {
            return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
        }
        if ("OnlyOnAlliedAttack".equals(sa.getParam("AILogic"))) {
            Combat combat = ai.getGame().getCombat();
            if (combat != null && combat.getAttackingPlayer() != null && !combat.getAttackingPlayer().isOpponentOf(ai)) {
                return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
            }
            return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
        }
        return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
    }

    @Override
    public boolean confirmAction(Player player, SpellAbility sa, PlayerActionConfirmMode mode, String message, Map<String, Object> params) {
        return true;
    }

    @Override
    protected Player chooseSinglePlayer(Player ai, SpellAbility sa, Iterable<Player> options, Map<String, Object> params) {
        if (params != null && params.containsKey("Attacker")) {
            return (Player)ComputerUtilCombat.addAttackerToCombat(sa, (Card)params.get("Attacker"), options);
        }
        return (Player)Iterables.getFirst(options, null);
    }

    @Override
    protected GameEntity chooseSingleAttackableEntity(Player ai, SpellAbility sa, Iterable<GameEntity> options, Map<String, Object> params) {
        if (params != null && params.containsKey("Attacker")) {
            return ComputerUtilCombat.addAttackerToCombat(sa, (Card)params.get("Attacker"), options);
        }
        return super.chooseSingleAttackableEntity(ai, sa, options, params);
    }

    public static Card spawnToken(Player ai, SpellAbility sa) {
        if (!sa.hasParam("TokenScript")) {
            throw new RuntimeException("Spell Ability has no TokenScript: " + String.valueOf(sa));
        }
        Card result = TokenInfo.getProtoType((String)sa.getParam("TokenScript").split(",")[0], (SpellAbility)sa, (Player)ai);
        if (result == null) {
            throw new RuntimeException("don't find Token for TokenScript: " + sa.getParam("TokenScript"));
        }
        result.setLastKnownZone((Zone)ai.getZone(ZoneType.Battlefield));
        Game game = ai.getGame();
        ComputerUtilCard.applyStaticContPT(game, result, null);
        return result;
    }

    private boolean tgtRoleAura(Player ai, SpellAbility sa, Card tok, boolean mandatory) {
        boolean isCurse = "Curse".equals(sa.getParam("AILogic")) || "Curse".equals(tok.getSVar("AttachAILogic"));
        CardCollection tgts = CardUtil.getValidCardsToTarget((SpellAbility)sa);
        CardCollection prefListSBA = CardLists.filter((Iterable)tgts, c -> !c.getAttachedCards().anyMatch(att -> att.getController() == ai && att.getType().hasSubtype("Role")));
        CardCollection prefList = isCurse ? CardLists.filterControlledBy((Iterable)prefListSBA, (FCollectionView)ai.getOpponents()) : CardLists.filterControlledBy((Iterable)prefListSBA, (FCollectionView)ai.getYourTeam());
        if (prefList.isEmpty()) {
            if (mandatory) {
                if (sa.isTargetNumberValid()) {
                    return true;
                }
                if (!prefListSBA.isEmpty()) {
                    sa.getTargets().add((GameObject)ComputerUtilCard.getWorstCreatureAI((Iterable<Card>)prefListSBA));
                    return true;
                }
                if (!tgts.isEmpty()) {
                    sa.getTargets().add((GameObject)ComputerUtilCard.getWorstCreatureAI((Iterable<Card>)tgts));
                    return true;
                }
            }
        } else {
            sa.getTargets().add((GameObject)ComputerUtilCard.getBestCreatureAI((Iterable<Card>)prefList));
            return true;
        }
        return false;
    }

    @Override
    public boolean willPayUnlessCost(Player payer, SpellAbility sa, Cost cost, boolean alreadyPaid, FCollectionView<Player> payers) {
        Card source = sa.getHostCard();
        Player p = sa.getActivatingPlayer();
        if (sa.isKeyword(Keyword.FABRICATE)) {
            CardCollection list;
            Card tokenCard;
            int n = Integer.parseInt(sa.getParam("TokenAmount"));
            if (source.hasSVar("EndOfTurnLeavePlay") || ComputerUtilCard.isUselessCreature(payer, source)) {
                return false;
            }
            Card copy = CardCopyService.getLKICopy((Card)source);
            copy.setCounters((CounterType)CounterEnumType.P1P1, Integer.valueOf(copy.getCounters((CounterType)CounterEnumType.P1P1) + n));
            copy.setZone(source.getZone());
            Combat combat = source.getGame().getCombat();
            if (combat != null && combat.isAttacking(source)) {
                Player defender = combat.getDefenderPlayerByAttacker(source);
                return defender.canLoseLife() && !ComputerUtilCard.canBeBlockedProfitably(defender, copy, true);
            }
            if (CombatUtil.canAttack((Card)copy)) {
                for (Player opp : payer.getOpponents()) {
                    if (!CombatUtil.canAttack((Card)copy, (GameEntity)opp) || !opp.canLoseLife() || ComputerUtilCard.canBeBlockedProfitably(opp, copy, true)) continue;
                    return true;
                }
            }
            if (!(tokenCard = TokenAi.spawnToken(payer, sa)).isCreature() || tokenCard.getNetToughness() < 1) {
                return true;
            }
            if ("Marionette Master".equals(source.getName())) {
                list = CardLists.filter((Iterable)payer.getCardsIn(ZoneType.Battlefield), (Predicate)CardPredicates.ARTIFACTS);
                return list.size() >= copy.getNetPower();
            }
            if ("Cultivator of Blades".equals(source.getName())) {
                list = payer.getCreaturesInPlay();
                return list.size() >= copy.getNetPower();
            }
            int evalCounter = ComputerUtilCard.evaluateCreature(copy);
            CardCollection tokenList = new CardCollection(source);
            for (int i = 0; i < n; ++i) {
                tokenList.add(TokenAi.spawnToken(payer, sa));
            }
            int evalToken = ComputerUtilCard.evaluateCreatureList((CardCollectionView)tokenList);
            return evalToken < evalCounter;
        }
        if (payer.isOpponentOf(sa.getActivatingPlayer())) {
            int evalPayerCreatures;
            CostDraw draw;
            if (cost.hasSpecificCostType(CostDraw.class) && (draw = (CostDraw)cost.getCostPartByType(CostDraw.class)).getPotentialPlayers(payer, sa).contains(p) && p.getCardsIn(ZoneType.Library).size() < 5 && (!p.isCardInPlay("Laboratory Maniac") || p.cantWin())) {
                return true;
            }
            if (alreadyPaid) {
                return false;
            }
            Card tokenCard = TokenAi.spawnToken(p, sa);
            if (!tokenCard.isCreature() || tokenCard.getNetToughness() < 1) {
                return false;
            }
            int evalActivator = ComputerUtilCard.evaluateCreature(tokenCard) + ComputerUtilCard.evaluateCreatureList((CardCollectionView)p.getCreaturesInPlay());
            if (evalActivator > (evalPayerCreatures = ComputerUtilCard.evaluateCreatureList((CardCollectionView)payer.getCreaturesInPlay()))) {
                return true;
            }
        }
        return super.willPayUnlessCost(payer, sa, cost, alreadyPaid, payers);
    }
}
