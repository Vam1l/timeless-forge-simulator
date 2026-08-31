#!/usr/bin/env python3
from pathlib import Path
import argparse

METHOD='''    private static boolean isTronCropRotationLandSacrifice(final SpellAbility ability, final String type, final int amount) {
        if (ability == null || ability.getHostCard() == null || amount != 1) return false;
        if (!"Crop Rotation".equals(ability.getHostCard().getName())) return false;
        if (ability.getApi() != ApiType.ChangeZone) return false;
        if (!"Library".equals(ability.getParamOrDefault("Origin", "")) || !"Battlefield".equals(ability.getParamOrDefault("Destination", ""))) return false;
        if (!ability.getParamOrDefault("ChangeType", "").contains("Land")) return false;
        return type != null && type.contains("Land");
    }

'''

BLOCK='''        if (isTronCropRotationLandSacrifice(ability, type, amount)) {
            final java.util.Map<String, Integer> counts = new java.util.LinkedHashMap<>();
            for (final Card land : ai.getLandsInPlay()) counts.merge(land.getName(), 1, Integer::sum);
            final java.util.Set<String> libraryLands = ai.getCardsIn(ZoneType.Library).stream().filter(Card::isLand).map(Card::getName).collect(java.util.stream.Collectors.toCollection(java.util.LinkedHashSet::new));
            final java.util.List<String> names = typeList.stream().map(Card::getName).collect(java.util.stream.Collectors.toList());
            final java.util.List<String> allowed = TronCropRotationSelection.allowedSacrificeNames(names, counts, libraryLands);
            if (allowed != null) {
                if (allowed.isEmpty()) return new CardCollection();
                final CardCollection choices = CardLists.filter(typeList, c -> allowed.contains(c.getName()));
                final Card chosen = ComputerUtilCard.getWorstLand(choices);
                final CardCollection result = new CardCollection();
                if (chosen != null) result.add(chosen);
                return result;
            }
        }
'''

def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    s=a.input.read_text()
    sig='    public static CardCollection chooseSacrificeType(final Player ai, String type, final SpellAbility ability, final Card target, final boolean effect, final int amount, final CardCollectionView exclude) {\n'
    anchor='        typeList = ComputerUtilCost.paymentChoicesWithoutTargets(typeList, ability, ai);\n'
    if s.count(sig)!=1 or s.count(anchor)!=1: raise SystemExit('Forge 2.0.14 ComputerUtil anchor mismatch')
    s=s.replace(sig,METHOD+sig,1).replace(anchor,anchor+BLOCK,1)
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(s)
if __name__=='__main__': main()
