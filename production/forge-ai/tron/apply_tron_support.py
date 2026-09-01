#!/usr/bin/env python3
from pathlib import Path
import argparse

def one(s,o,n,label):
    if s.count(o)!=1: raise SystemExit(f'{label} anchor mismatch: {s.count(o)}')
    return s.replace(o,n,1)

def between(s,start,end,new,label):
    i=s.find(start); j=s.find(end,i)
    if i<0 or j<0: raise SystemExit(f'{label} boundary mismatch')
    return s[:i]+new+'\n\n'+s[j:]

def card(s):
    s=one(s,'import java.util.Collection;\n','import java.util.Collection;\nimport java.util.Collections;\n','Collections import')
    best='''    public static Card getBestLandAI(final Iterable<Card> list) {
        final List<Card> land = CardLists.filter(list, CardPredicates.LANDS);
        if (land.isEmpty()) return null;
        final List<Card> nbLand = CardLists.filter(land, CardPredicates.NONBASIC_LANDS);
        if (!nbLand.isEmpty()) {
            final CardCollectionView field = nbLand.get(0).getController().getCardsIn(ZoneType.Battlefield);
            final boolean mine = !CardLists.filter(field, CardPredicates.nameEquals("Urza's Mine")).isEmpty();
            final boolean tower = !CardLists.filter(field, CardPredicates.nameEquals("Urza's Tower")).isEmpty();
            final boolean plant = !CardLists.filter(field, CardPredicates.nameEquals("Urza's Power Plant")).isEmpty();
            if (!mine && IterableUtil.any(list, CardPredicates.nameEquals("Urza's Mine"))) return CardLists.filter(nbLand, CardPredicates.nameEquals("Urza's Mine")).getFirst();
            if (!tower && IterableUtil.any(list, CardPredicates.nameEquals("Urza's Tower"))) return CardLists.filter(nbLand, CardPredicates.nameEquals("Urza's Tower")).getFirst();
            if (!plant && IterableUtil.any(list, CardPredicates.nameEquals("Urza's Power Plant"))) return CardLists.filter(nbLand, CardPredicates.nameEquals("Urza's Power Plant")).getFirst();
            final List<Card> nonUrza = CardLists.filter(nbLand, c -> !c.getName().startsWith("Urza's"));
            if (!nonUrza.isEmpty()) return nonUrza.get(0);
            final List<Card> basics = CardLists.filter(land, CardPredicates.BASIC_LANDS);
            if (!basics.isEmpty()) return basics.get(0);
            return nbLand.get(0);
        }
        String basic = ""; int min = Integer.MAX_VALUE;
        for (String name : MagicColor.Constant.BASIC_LANDS) { final int n=CardLists.getType(land,name).size(); if(n>0&&n<min){min=n;basic=name;} }
        if (min==Integer.MAX_VALUE) return land.stream().filter(CardPredicates.UNTAPPED).findFirst().orElse(land.get(0));
        final List<Card> choices=CardLists.getType(land,basic);
        return choices.stream().filter(CardPredicates.UNTAPPED).findFirst().orElseGet(() -> Aggregates.random(choices));
    }'''
    s=between(s,'    public static Card getBestLandAI(final Iterable<Card> list) {','    public static Card getBestLandToRemoveAI(',best,'getBestLandAI')
    worst='''    public static Card getWorstLand(final List<Card> lands) {
        if (lands==null || lands.isEmpty()) return null;
        Card worst=null; int max=Integer.MIN_VALUE;
        final Player controller=lands.get(0).getController();
        final CardCollectionView all=controller==null?null:controller.getLandsInPlay();
        final boolean mine=all!=null&&!CardLists.filter(all,CardPredicates.nameEquals("Urza's Mine")).isEmpty();
        final boolean tower=all!=null&&!CardLists.filter(all,CardPredicates.nameEquals("Urza's Tower")).isEmpty();
        final boolean plant=all!=null&&!CardLists.filter(all,CardPredicates.nameEquals("Urza's Power Plant")).isEmpty();
        final boolean tron=mine&&tower&&plant; final Set<String> green=Collections.singleton("G");
        for(Card c:lands){
            int score=c.isTapped()?2:0; score+=c.isBasicLand()?1:0; score-=c.isCreature()?4:0;
            for(Card aura:c.getEnchantedBy()) score+=aura.getController().isOpponentOf(c.getController())?5:-5;
            if(all!=null){
                final long same=all.stream().filter(CardPredicates.sharesNameWith(c)).count(); if(same>1) score+=50;
                if(c.canProduceColorMana(green)||(c.isBasicLand()&&"Forest".equals(c.getName()))){
                    final long gs=all.stream().filter(l->l.canProduceColorMana(green)||(l.isBasicLand()&&"Forest".equals(l.getName()))).count(); if(gs<=1) score-=1000;
                }
                if(tron&&c.getName().startsWith("Urza's")&&same==1) score-=1000;
            }
            if(score==max&&worst!=null&&CardLists.count(lands,CardPredicates.sharesNameWith(c))>CardLists.count(lands,CardPredicates.sharesNameWith(worst))) worst=c;
            if(score>max||worst==null){worst=c;max=score;}
        }
        return worst;
    }'''
    return between(s,'    public static Card getWorstLand(final List<Card> lands) {','    public static Card getBestLandToAnimate(',worst,'getWorstLand')

def mana(s):
    old='''            for (Integer colorint : manaAbilityMap.keySet()) {
                // apply mana color change matrix here
                if (ai.getManaPool().canPayForShardWithColor(shard, colorint.byteValue())) {
                    for (SpellAbility sa : manaAbilityMap.get(colorint)) {
                        if (!res.get(shard).contains(sa)) {
                            res.put(shard, sa);
                        }
                    }
                }
            }
'''
    new='''            for (Object key : manaAbilityMap.keySet()) {
                if (!(key instanceof Number)) continue;
                int colorVal = ((Number) key).intValue();
                if (!ai.getManaPool().canPayForShardWithColor(shard, (byte)colorVal)) continue;
                for (SpellAbility sa : manaAbilityMap.get(colorVal)) {
                    if (res.get(shard).contains(sa)) continue;
                    res.put(shard, sa);
                }
            }
'''
    return one(s,old,new,'numeric-map')

def permanent(s):
    old='''        // Wait for Main2 if possible
        return !ph.is(PhaseType.MAIN1) || !ph.isPlayerTurn(ai) || sa.hasParam("WithoutManaCost") || ComputerUtil.castPermanentInMain1(ai, sa);
'''
    new='''        if (ph.is(PhaseType.MAIN1) && ph.isPlayerTurn(ai) && !sa.hasParam("WithoutManaCost")) {
            final String name = card.getName();
            if ("Chromatic Star".equals(name) || "Chromatic Sphere".equals(name)
                    || (card.isArtifact() && !card.getManaAbilities().isEmpty())) return true;
        }
        // Wait for Main2 if possible
        return !ph.is(PhaseType.MAIN1) || !ph.isPlayerTurn(ai) || sa.hasParam("WithoutManaCost") || ComputerUtil.castPermanentInMain1(ai, sa);
'''
    return one(s,old,new,'PermanentAi MAIN1')

def main():
    p=argparse.ArgumentParser();p.add_argument('--source-dir',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    files={'forge/ai/ComputerUtilCard.java':card,'forge/ai/ComputerUtilMana.java':mana,'forge/ai/ability/PermanentAi.java':permanent}
    for rel,fn in files.items():
        src=a.source_dir/rel; out=a.output_dir/rel; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(fn(src.read_text()))
if __name__=='__main__':main()
