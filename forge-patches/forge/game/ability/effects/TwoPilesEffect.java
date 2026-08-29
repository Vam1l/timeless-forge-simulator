/*
 * Decompiled with CFR 0.152.
 */
package forge.game.ability.effects;

import com.google.common.collect.Lists;
import forge.game.CardTraitBase;
import forge.game.ability.AbilityUtils;
import forge.game.ability.SpellAbilityEffect;
import forge.game.card.Card;
import forge.game.card.CardCollection;
import forge.game.card.CardCollectionView;
import forge.game.card.CardLists;
import forge.game.player.Player;
import forge.game.player.PlayerCollection;
import forge.game.spellability.SpellAbility;
import forge.game.zone.ZoneType;
import forge.util.Lang;
import forge.util.Localizer;
import java.util.ArrayList;

public class TwoPilesEffect
extends SpellAbilityEffect {
    @Override
    protected String getStackDescription(SpellAbility sa) {
        StringBuilder sb = new StringBuilder();
        String valid = sa.getParamOrDefault("ValidCards", "");
        sb.append("Separate all ").append(valid).append(" cards ");
        sb.append(Lang.joinHomogenous(TwoPilesEffect.getTargetPlayers(sa)));
        sb.append(" controls into two piles.");
        return sb.toString();
    }

    @Override
    public void resolve(SpellAbility sa) {
        PlayerCollection choosers;
        PlayerCollection choosers2;
        Card source = sa.getHostCard();
        ZoneType zone = null;
        boolean pile1WasChosen = true;
        boolean isLeftRightPile = sa.hasParam("LeftRightPile");
        if (sa.hasParam("Zone")) {
            zone = ZoneType.smartValueOf(sa.getParam("Zone"));
        }
        String valid = sa.getParamOrDefault("ValidCards", "Card");
        PlayerCollection tgtPlayers = TwoPilesEffect.getTargetPlayers(sa);
        Player separator = source.getController();
        if (sa.hasParam("Separator") && !(choosers2 = AbilityUtils.getDefinedPlayers(source, sa.getParam("Separator"), sa)).isEmpty()) {
            separator = sa.getActivatingPlayer().getController().chooseSingleEntityForEffect(choosers2, null, sa, Localizer.getInstance().getMessage("lblChooser", new Object[0]) + ":", false, null, null);
        }
        Player chooser = (Player)tgtPlayers.get(0);
        if (sa.hasParam("Chooser") && !(choosers = AbilityUtils.getDefinedPlayers(source, sa.getParam("Chooser"), sa)).isEmpty()) {
            chooser = sa.getActivatingPlayer().getController().chooseSingleEntityForEffect(choosers, null, sa, Localizer.getInstance().getMessage("lblChooser", new Object[0]) + ":", false, null, null);
        }
        for (Player p : tgtPlayers) {
            SpellAbility sub;
            ArrayList<Object> tempRemembered;
            CardCollection pile2;
            CardCollectionView pile1;
            if (!p.isInGame()) continue;
            if (sa.hasParam("DefinedPiles")) {
                String[] def = sa.getParam("DefinedPiles").split(",", 2);
                pile1 = AbilityUtils.getDefinedCards(source, def[0], sa);
                pile2 = AbilityUtils.getDefinedCards(source, def[1], sa);
            } else {
                CardCollectionView pool0 = sa.hasParam("DefinedCards") ? AbilityUtils.getDefinedCards(source, sa.getParam("DefinedCards"), sa) : p.getCardsIn(zone);
                CardCollection pool = CardLists.getValidCards((Iterable<Card>)pool0, valid, source.getController(), source, (CardTraitBase)sa);
                int size = pool.size();
                if (size == 0) {
                    return;
                }
                String title = "One".equals(sa.getParamOrDefault("FaceDown", "False")) ? Localizer.getInstance().getMessage("lblSelectCardForFaceDownPile", new Object[0]) : (isLeftRightPile ? Localizer.getInstance().getMessage("lblSelectCardForLeftPile", new Object[0]) : Localizer.getInstance().getMessage("lblDivideCardIntoTwoPiles", new Object[0]));
                pile1 = separator.getController().chooseCardsForEffect(pool, sa, title, 0, size, false, null);
                pile2 = new CardCollection(pool);
                pile2.removeAll(pile1);
            }
            pile1WasChosen = isLeftRightPile ? true : chooser.getController().chooseCardsPile(sa, pile1, pile2, sa.getParamOrDefault("FaceDown", "False"));
            CardCollection chosenPile = new CardCollection(pile1WasChosen ? pile1 : pile2);
            CardCollection unchosenPile = new CardCollection(!pile1WasChosen ? pile1 : pile2);
            StringBuilder notification = new StringBuilder();
            if (isLeftRightPile) {
                notification.append("\n");
                notification.append(Lang.getInstance().getPossessedObject(separator.getName(), Localizer.getInstance().getMessage("lblLeftPile", new Object[0])));
                notification.append("\n--------------------\n");
                if (!chosenPile.isEmpty()) {
                    for (Card c : chosenPile) {
                        notification.append(c.getName()).append("\n");
                    }
                } else {
                    notification.append("(" + Localizer.getInstance().getMessage("lblEmptyPile", new Object[0]) + ")\n");
                }
                notification.append("\n");
                notification.append(Lang.getInstance().getPossessedObject(separator.getName(), Localizer.getInstance().getMessage("lblRightPile", new Object[0])));
                notification.append("\n--------------------\n");
                if (!unchosenPile.isEmpty()) {
                    for (Card c : unchosenPile) {
                        notification.append(c.getName()).append("\n");
                    }
                } else {
                    notification.append("(" + Localizer.getInstance().getMessage("lblEmptyPile", new Object[0]) + ")\n");
                }
                p.getGame().getAction().notifyOfValue(sa, separator, notification.toString(), separator);
            } else {
                notification.append(String.valueOf(chooser) + " " + Localizer.getInstance().getMessage("lblChoosesPile", new Object[0]) + " " + (pile1WasChosen ? "1" : "2") + ":\n");
                if (!chosenPile.isEmpty()) {
                    for (Card c : chosenPile) {
                        notification.append(c.getName()).append("\n");
                    }
                } else {
                    notification.append("(" + Localizer.getInstance().getMessage("lblEmptyPile", new Object[0]) + ")");
                }
                p.getGame().getAction().notifyOfValue(sa, chooser, notification.toString(), chooser);
            }
            if (sa.hasParam("RememberChosen")) {
                source.addRemembered(chosenPile);
            }
            if (sa.hasParam("ChosenPile")) {
                tempRemembered = Lists.newArrayList(source.getRemembered());
                source.removeRemembered(tempRemembered);
                source.addRemembered(chosenPile);
                sub = sa.getAdditionalAbility("ChosenPile");
                if (sub != null) {
                    AbilityUtils.resolve(sub);
                }
                source.removeRemembered(chosenPile);
                source.addRemembered(tempRemembered);
            }
            if (!sa.hasParam("UnchosenPile")) continue;
            tempRemembered = Lists.newArrayList(source.getRemembered());
            source.removeRemembered(tempRemembered);
            source.addRemembered(unchosenPile);
            sub = sa.getAdditionalAbility("UnchosenPile");
            if (sub != null) {
                AbilityUtils.resolve(sub);
            }
            source.removeRemembered(unchosenPile);
            source.addRemembered(tempRemembered);
        }
        if (!sa.hasParam("KeepRemembered") && !sa.hasParam("RememberChosen")) {
            source.clearRemembered();
        }
        source.getGame().incPiledGuessedSA();
    }
}

