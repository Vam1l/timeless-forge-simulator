package forge.ai.ability;

import forge.ai.AiAbilityDecision;
import forge.ai.AiAttackController;
import forge.ai.AiPlayDecision;
import forge.ai.SpellAbilityAi;
import forge.game.CardTraitBase;
import forge.game.GameObject;
import forge.game.ability.AbilityUtils;
import forge.game.card.Card;
import forge.game.card.CardCollection;
import forge.game.card.CardLists;
import forge.game.player.Player;
import java.util.Map;
import forge.game.spellability.SpellAbility;
import forge.game.zone.ZoneType;
import forge.util.collect.FCollection;

public class TwoPilesAi extends SpellAbilityAi {

    @Override
    protected Player chooseSinglePlayer(Player ai, SpellAbility sa, Iterable<Player> options, Map<String, Object> params) {
        if (options == null || !options.iterator().hasNext()) {
            return ai;
        }
        for (Player p : options) {
            if (p == ai) {
                return ai;
            }
        }
        return options.iterator().next();
    }

    @Override
    protected AiAbilityDecision canPlay(Player ai, SpellAbility sa) {
        Card card = sa.getHostCard();
        ZoneType zone = null;
        if (sa.hasParam("Zone")) {
            zone = ZoneType.smartValueOf(sa.getParam("Zone"));
        }
        String valid = sa.getParamOrDefault("ValidCards", "");
        Player opp = AiAttackController.choosePreferredDefenderPlayer(ai);
        if (sa.usesTargeting()) {
            sa.resetTargets();
            if (sa.canTarget((GameObject) opp)) {
                sa.getTargets().add((GameObject) opp);
            } else {
                return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
            }
        }
        FCollection tgtPlayers = sa.usesTargeting() && !sa.hasParam("Defined")
                ? new FCollection(sa.getTargets().getTargetPlayers())
                : AbilityUtils.getDefinedPlayers(card, sa.getParam("Defined"), (CardTraitBase) sa);
        if (tgtPlayers == null || tgtPlayers.isEmpty()) {
            return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
        }
        Player p = (Player) tgtPlayers.get(0);
        Object pool = sa.hasParam("DefinedCards")
                ? AbilityUtils.getDefinedCards(card, sa.getParam("DefinedCards"), (CardTraitBase) sa)
                : p.getCardsIn(zone);
        CardCollection poolCol = CardLists.getValidCards((Iterable) pool, valid, card.getController(), card, (CardTraitBase) sa);
        int size = poolCol.size();
        if (size > 2) {
            return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
        }
        return new AiAbilityDecision(0, AiPlayDecision.CantPlayAi);
    }
}
