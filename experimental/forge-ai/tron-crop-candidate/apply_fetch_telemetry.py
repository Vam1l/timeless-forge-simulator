#!/usr/bin/env python3
"""Add observational Crop Rotation fetch-choice telemetry to a temporary recovered ChangeZoneAi copy.

This patcher changes diagnostic output only. It does not change any selected card,
return value, candidate ordering, random call, or AI threshold.
"""
from pathlib import Path
import argparse
import difflib

HELPERS = r'''
    private static boolean isTronCropFetchTelemetry(final ZoneType destination,
            final List<ZoneType> origin, final SpellAbility sa) {
        return sa != null && sa.getHostCard() != null
                && "Crop Rotation".equals(sa.getHostCard().getName())
                && sa.getApi() == ApiType.ChangeZone
                && origin != null && origin.contains(ZoneType.Library)
                && ZoneType.Battlefield.equals(destination)
                && sa.getParamOrDefault("ChangeType", "").contains("Land");
    }

    private static String tronCropFetchNames(final Iterable<Card> cards) {
        final List<String> names = new ArrayList<>();
        for (final Card card : cards) {
            names.add(card.getName() + "#" + card.getId());
        }
        return names.toString();
    }

    private static void logTronCropFetchTelemetry(final String path,
            final ZoneType destination, final List<ZoneType> origin,
            final SpellAbility sa, final CardCollection fetchList,
            final Player decider, final Card selected) {
        if (!isTronCropFetchTelemetry(destination, origin, sa)) {
            return;
        }
        final CardCollectionView controlled = decider.getCardsIn(ZoneType.Battlefield);
        final List<String> present = new ArrayList<>();
        final List<String> missing = new ArrayList<>();
        final List<String> missingAvailable = new ArrayList<>();
        for (final String piece : Arrays.asList("Urza's Mine", "Urza's Power Plant", "Urza's Tower")) {
            final boolean hasPiece = !CardLists.filter((Iterable)controlled,
                    (Predicate)CardPredicates.nameEquals(piece)).isEmpty();
            if (hasPiece) {
                present.add(piece);
            } else {
                missing.add(piece);
                if (!CardLists.filter((Iterable)fetchList,
                        (Predicate)CardPredicates.nameEquals(piece)).isEmpty()) {
                    missingAvailable.add(piece);
                }
            }
        }
        String classification = "none";
        if (selected != null) {
            if (missingAvailable.contains(selected.getName())) {
                classification = "missing_distinct_piece";
            } else if (!CardLists.filter((Iterable)controlled,
                    (Predicate)CardPredicates.nameEquals(selected.getName())).isEmpty()) {
                classification = "duplicate_or_same_identity";
            } else {
                classification = "fallback";
            }
        }
        System.out.println("[TRON_CROP_FETCH] host=" + sa.getHostCard().getName()
                + " hostId=" + sa.getHostCard().getId()
                + " api=" + sa.getApi()
                + " path=" + path
                + " origin=" + origin
                + " destination=" + destination
                + " legalCandidates=" + tronCropFetchNames(fetchList)
                + " controlledLands=" + tronCropFetchNames(decider.getLandsInPlay())
                + " tronPresent=" + present
                + " tronMissing=" + missing
                + " missingAvailable=" + missingAvailable
                + " selected=" + (selected == null ? "none" : selected.getName() + "#" + selected.getId())
                + " classification=" + classification);
    }

'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--diff", type=Path)
    args = ap.parse_args()
    original = args.input.read_text(encoding="utf-8")

    signature = (
        "    public static Card chooseCardToHiddenOriginChangeZone(ZoneType destination, "
        "List<ZoneType> origin, SpellAbility sa, CardCollection fetchList, Player player, Player decider) {\n"
    )
    if original.count(signature) != 1:
        raise SystemExit("expected exact recovered hidden-origin chooser signature")
    patched = original.replace(signature, HELPERS + signature, 1)

    method_start = patched.index(signature)
    method_end = patched.index("    private static CardCollection prefilterOwnListForBounceAnyNum", method_start)
    before, method, after = patched[:method_start], patched[method_start:method_end], patched[method_end:]

    init_anchor = "        Card c;\n"
    if method.count(init_anchor) != 1:
        raise SystemExit("expected one Card c declaration")
    method = method.replace(init_anchor, init_anchor + '        String tronCropFetchPath = "initial";\n', 1)

    key_return = "                return keycardFound;\n"
    key_paths = ["ailogic_bestcard_keycard", "basic_keycard", "hand_keycard", "battlefield_keycard", "general_keycard"]
    if method.count(key_return) != len(key_paths):
        raise SystemExit(f"expected {len(key_paths)} keycard returns")
    for path in key_paths:
        replacement = (
            f'                logTronCropFetchTelemetry("{path}", destination, origin, sa, fetchList, decider, keycardFound);\n'
            + key_return
        )
        method = method.replace(key_return, replacement, 1)

    ramp_anchor = (
        '                    if (logic.equals("ConsiderRamp") && (c = ChangeZoneAi.considerRamp(decider, sa, fetchList, keycardFound)) != null) {\n'
        '                        return c;\n'
        '                    }\n'
    )
    if method.count(ramp_anchor) != 1:
        raise SystemExit("expected ConsiderRamp selected-card return")
    method = method.replace(
        ramp_anchor,
        '                    if (logic.equals("ConsiderRamp") && (c = ChangeZoneAi.considerRamp(decider, sa, fetchList, keycardFound)) != null) {\n'
        '                        logTronCropFetchTelemetry("consider_ramp", destination, origin, sa, fetchList, decider, c);\n'
        '                        return c;\n'
        '                    }\n',
        1,
    )

    replacements = [
        ('            c = ChangeZoneAi.basicManaFixing(decider, (List<Card>)fetchList);\n','            c = ChangeZoneAi.basicManaFixing(decider, (List<Card>)fetchList);\n            tronCropFetchPath = "basic_mana_fixing";\n'),
        ('                c = ComputerUtilCard.getWorstAI((Iterable<Card>)fetchList);\n','                c = ComputerUtilCard.getWorstAI((Iterable<Card>)fetchList);\n                tronCropFetchPath = "battlefield_gaincontrol_worst";\n'),
        ('                c = ComputerUtilCard.getBestAI((Iterable<Card>)fetchList);\n','                c = ComputerUtilCard.getBestAI((Iterable<Card>)fetchList);\n                tronCropFetchPath = "battlefield_best_ai";\n'),
        ('                c = ChangeZoneAi.basicManaFixing(decider, (List<Card>)fetchList);\n','                c = ChangeZoneAi.basicManaFixing(decider, (List<Card>)fetchList);\n                tronCropFetchPath = "general_basic_mana_fixing";\n'),
        ('                    c = ComputerUtilCard.getBestLandAI((Iterable<Card>)fetchList);\n','                    c = ComputerUtilCard.getBestLandAI((Iterable<Card>)fetchList);\n                    tronCropFetchPath = "general_land_best";\n'),
        ('                    c = ChangeZoneAi.chooseCreature(decider, CardLists.filter((Iterable)fetchList, (Predicate)CardPredicates.CREATURES));\n','                    c = ChangeZoneAi.chooseCreature(decider, CardLists.filter((Iterable)fetchList, (Predicate)CardPredicates.CREATURES));\n                    tronCropFetchPath = "general_creature";\n'),
        ('                        c = potentialCard;\n','                        c = potentialCard;\n                        tronCropFetchPath = "general_low_life_castable";\n'),
        ('                    c = ComputerUtilCard.getBestAI((Iterable<Card>)fetchList);\n','                    c = ComputerUtilCard.getBestAI((Iterable<Card>)fetchList);\n                    tronCropFetchPath = "general_best_ai";\n'),
        ('            c = first;\n','            c = first;\n            tronCropFetchPath = "first_fallback";\n'),
    ]
    for anchor, replacement in replacements:
        if method.count(anchor) < 1:
            raise SystemExit(f"missing selection anchor: {anchor.strip()}")
        method = method.replace(anchor, replacement, 1)

    final_anchor = (
        '        if (c == null) {\n'
        '            c = first;\n'
        '            tronCropFetchPath = "first_fallback";\n'
        '        }\n'
        '        return c;\n'
        '    }\n'
    )
    if method.count(final_anchor) != 1:
        raise SystemExit("expected unique common final card-return block")
    method = method.replace(
        final_anchor,
        '        if (c == null) {\n'
        '            c = first;\n'
        '            tronCropFetchPath = "first_fallback";\n'
        '        }\n'
        '        logTronCropFetchTelemetry(tronCropFetchPath, destination, origin, sa, fetchList, decider, c);\n'
        '        return c;\n'
        '    }\n',
        1,
    )

    patched = before + method + after
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(patched, encoding="utf-8")
    if args.diff:
        args.diff.parent.mkdir(parents=True, exist_ok=True)
        diff = difflib.unified_diff(original.splitlines(True), patched.splitlines(True), fromfile="recovered/ChangeZoneAi.java", tofile="diagnostic/ChangeZoneAi.java")
        args.diff.write_text("".join(diff), encoding="utf-8")


if __name__ == "__main__":
    main()
