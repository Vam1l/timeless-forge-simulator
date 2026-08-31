#!/usr/bin/env python3
"""Apply the narrow Tron Crop Rotation candidate to stock Forge ComputerUtil.java.

The immutable recovered blobs are never edited. This script patches a temporary copy
of exact Forge 2.0.14 ComputerUtil.java, which is then compiled over the exact
recovered JAR to form the distinguishable candidate build.
"""
from pathlib import Path
import argparse

METHOD = r'''
    private static CardCollection chooseTronCropRotationAssemblySacrifice(final Player ai,
            final CardCollectionView cardlist, final int amount, final SpellAbility source,
            final boolean destroy) {
        if (destroy || amount != 1 || source == null || source.getHostCard() == null
                || !"Crop Rotation".equals(source.getHostCard().getName())) {
            return null;
        }
        if (!ai.canSearchLibraryWith(source, ai)) {
            return null;
        }

        final CardCollection lands = CardLists.filter(cardlist, CardPredicates.LANDS);
        if (lands.isEmpty()) {
            return null;
        }

        final Map<String, Integer> battlefieldCounts = new HashMap<>();
        for (final Card land : ai.getLandsInPlay()) {
            battlefieldCounts.merge(land.getName(), 1, Integer::sum);
        }
        final Set<String> libraryLandNames = ai.getCardsIn(ZoneType.Library).stream()
                .filter(Card::isLand)
                .map(Card::getName)
                .collect(Collectors.toSet());
        final List<String> candidateNames = lands.stream().map(Card::getName).collect(Collectors.toList());
        final List<String> allowedNames = TronCropRotationSelection.allowedSacrificeNames(
                candidateNames, battlefieldCounts, libraryLandNames);

        // null means no assembly-specific restriction: retain Forge's normal chooser.
        if (allowedNames == null) {
            return null;
        }

        final CardCollection result = new CardCollection();
        if (allowedNames.isEmpty()) {
            System.out.println("[TRON_CROP_CANDIDATE] assembly-protection: no safe sacrifice; "
                    + "battlefield=" + battlefieldCounts + " library=" + libraryLandNames);
            return result;
        }

        final CardCollection allowedCards = CardLists.filter(lands, c -> allowedNames.contains(c.getName()));
        final Card chosen = ComputerUtilCard.getWorstLand(allowedCards);
        if (chosen != null) {
            result.add(chosen);
        }
        System.out.println("[TRON_CROP_CANDIDATE] assembly-protection: battlefield=" + battlefieldCounts
                + " library=" + libraryLandNames + " candidates=" + candidateNames
                + " allowed=" + allowedNames + " selected=" + (chosen == null ? "none" : chosen.getName()));
        return result;
    }

'''

CALL = '''        final CardCollection tronCropSacrifice = chooseTronCropRotationAssemblySacrifice(
                ai, cardlist, amount, source, destroy);
        if (tronCropSacrifice != null) {
            return tronCropSacrifice;
        }
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--diff", type=Path)
    args = ap.parse_args()

    original = args.input.read_text(encoding="utf-8")
    signature = "    public static CardCollection choosePermanentsToSacrifice(final Player ai, final CardCollectionView cardlist, final int amount, final SpellAbility source,\n            final boolean destroy, final boolean isOptional) {\n"
    if original.count(signature) != 1:
        raise SystemExit("expected exactly one choosePermanentsToSacrifice signature")
    if "chooseTronCropRotationAssemblySacrifice" in original:
        raise SystemExit("candidate overlay already present")

    patched = original.replace(signature, METHOD + signature + CALL, 1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(patched, encoding="utf-8")

    if args.diff:
        import difflib
        args.diff.parent.mkdir(parents=True, exist_ok=True)
        diff = difflib.unified_diff(
            original.splitlines(True), patched.splitlines(True),
            fromfile="Forge-2.0.14/ComputerUtil.java",
            tofile="candidate/ComputerUtil.java")
        args.diff.write_text("".join(diff), encoding="utf-8")


if __name__ == "__main__":
    main()
