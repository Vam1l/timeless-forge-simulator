#!/usr/bin/env python3
"""Apply the second narrow Tron Crop Rotation integration overlay.

The immutable recovered blobs are never edited. This script patches a temporary
copy of exact Forge 2.0.14 ComputerUtil.java. In recovered mode it adds only
observational logging to the real sacrifice-cost path. In candidate mode it adds
the same telemetry plus the already-tested TronCropRotationSelection rule.
"""
from pathlib import Path
import argparse
import difflib

METHODS = r'''
    private static final boolean TRON_CROP_CANDIDATE_ENABLED = __CANDIDATE_ENABLED__;

    private static boolean isTronCropRotationLandSacrifice(final SpellAbility ability,
            final String type, final int amount) {
        if (ability == null || ability.getHostCard() == null || amount != 1) {
            return false;
        }
        if (!"Crop Rotation".equals(ability.getHostCard().getName())) {
            return false;
        }
        if (ability.getApi() != ApiType.ChangeZone) {
            return false;
        }
        if (!"Library".equals(ability.getParamOrDefault("Origin", ""))
                || !"Battlefield".equals(ability.getParamOrDefault("Destination", ""))) {
            return false;
        }
        if (!ability.getParamOrDefault("ChangeType", "").contains("Land")) {
            return false;
        }
        return type != null && type.contains("Land");
    }

    private static String tronCropNames(final Iterable<Card> cards) {
        final List<String> names = new ArrayList<>();
        for (final Card card : cards) {
            names.add(card.getName() + "#" + card.getId());
        }
        return names.toString();
    }

'''

REAL_PATH = r'''
        final boolean tronCropDecision = isTronCropRotationLandSacrifice(ability, type, amount);
        Map<String, Integer> tronCropBattlefieldCounts = null;
        Set<String> tronCropLibraryLandNames = null;
        Set<String> tronCropMissingAvailable = null;
        if (tronCropDecision) {
            tronCropBattlefieldCounts = new LinkedHashMap<>();
            for (final Card land : ai.getLandsInPlay()) {
                tronCropBattlefieldCounts.merge(land.getName(), 1, Integer::sum);
            }
            tronCropLibraryLandNames = ai.getCardsIn(ZoneType.Library).stream()
                    .filter(Card::isLand).map(Card::getName).collect(Collectors.toCollection(LinkedHashSet::new));
            tronCropMissingAvailable = TronCropRotationSelection.missingAvailablePieces(
                    tronCropBattlefieldCounts, tronCropLibraryLandNames);
            final List<String> uniqueTron = new ArrayList<>();
            final List<String> duplicateTron = new ArrayList<>();
            for (final String name : Arrays.asList("Urza's Mine", "Urza's Power Plant", "Urza's Tower")) {
                final int n = tronCropBattlefieldCounts.getOrDefault(name, 0);
                if (n == 1) uniqueTron.add(name);
                if (n > 1) duplicateTron.add(name);
            }
            System.out.println("[TRON_CROP_REALPATH] host=" + ability.getHostCard().getName()
                    + " api=" + ability.getApi()
                    + " origin=" + ability.getParamOrDefault("Origin", "")
                    + " destination=" + ability.getParamOrDefault("Destination", "")
                    + " changeType=" + ability.getParamOrDefault("ChangeType", "")
                    + " costType=" + type
                    + " legalCandidates=" + tronCropNames(typeList)
                    + " controlledLands=" + tronCropNames(ai.getLandsInPlay())
                    + " uniqueTron=" + uniqueTron
                    + " duplicateTron=" + duplicateTron
                    + " missingAvailable=" + tronCropMissingAvailable
                    + " libraryLandNames=" + tronCropLibraryLandNames
                    + " candidateEnabled=" + TRON_CROP_CANDIDATE_ENABLED);

            if (TRON_CROP_CANDIDATE_ENABLED) {
                final List<String> candidateNames = typeList.stream().map(Card::getName).collect(Collectors.toList());
                final List<String> allowedNames = TronCropRotationSelection.allowedSacrificeNames(
                        candidateNames, tronCropBattlefieldCounts, tronCropLibraryLandNames);
                if (allowedNames != null) {
                    if (allowedNames.isEmpty()) {
                        System.out.println("[TRON_CROP_DECISION] activated=true reason=no_safe_assembly_sacrifice selected=none");
                        return new CardCollection();
                    }
                    final CardCollection allowedCards = CardLists.filter(
                            typeList, c -> allowedNames.contains(c.getName()));
                    final Card chosen = ComputerUtilCard.getWorstLand(allowedCards);
                    final CardCollection result = new CardCollection();
                    if (chosen != null) {
                        result.add(chosen);
                    }
                    System.out.println("[TRON_CROP_DECISION] activated=true reason=assembly_protection"
                            + " allowed=" + allowedNames
                            + " selected=" + (chosen == null ? "none" : chosen.getName() + "#" + chosen.getId()));
                    return result;
                }
                System.out.println("[TRON_CROP_DECISION] activated=false reason=no_distinct_missing_piece_available");
            } else {
                System.out.println("[TRON_CROP_DECISION] activated=false reason=recovered_control");
            }
        }
'''

FINAL_LOG = r'''
        if (tronCropDecision) {
            System.out.println("[TRON_CROP_SELECTED] activated=false reason=forge_fallback selected="
                    + tronCropNames(sacList)
                    + " missingAvailable=" + tronCropMissingAvailable);
        }
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--mode", choices=("recovered", "candidate"), required=True)
    ap.add_argument("--diff", type=Path)
    args = ap.parse_args()

    original = args.input.read_text(encoding="utf-8")
    signature = (
        "    public static CardCollection chooseSacrificeType(final Player ai, String type, "
        "final SpellAbility ability, final Card target, final boolean effect, final int amount, "
        "final CardCollectionView exclude) {\n"
    )
    if original.count(signature) != 1:
        raise SystemExit("expected exactly one chooseSacrificeType signature")
    if "TRON_CROP_REALPATH" in original or "chooseTronCropRotationAssemblySacrifice" in original:
        raise SystemExit("unexpected prior candidate integration in source")

    methods = METHODS.replace("__CANDIDATE_ENABLED__", "true" if args.mode == "candidate" else "false")
    patched = original.replace(signature, methods + signature, 1)

    method_start = patched.index(signature)
    next_method = patched.index("    public static CardCollection chooseCollectEvidence", method_start)
    before, method, after = patched[:method_start], patched[method_start:next_method], patched[next_method:]

    legal_anchor = "        typeList = ComputerUtilCost.paymentChoicesWithoutTargets(typeList, ability, ai);\n"
    if method.count(legal_anchor) != 1:
        raise SystemExit("expected one legal-candidate anchor in chooseSacrificeType")
    method = method.replace(legal_anchor, legal_anchor + REAL_PATH, 1)

    return_anchor = "        return sacList;\n"
    if method.count(return_anchor) != 1:
        raise SystemExit("expected one final sacrifice return in chooseSacrificeType")
    method = method.replace(return_anchor, FINAL_LOG + return_anchor, 1)

    patched = before + method + after
    if "chooseTronCropRotationAssemblySacrifice" in patched:
        raise SystemExit("dead choosePermanentsToSacrifice integration survived")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(patched, encoding="utf-8")
    if args.diff:
        args.diff.parent.mkdir(parents=True, exist_ok=True)
        diff = difflib.unified_diff(
            original.splitlines(True), patched.splitlines(True),
            fromfile="Forge-2.0.14/ComputerUtil.java",
            tofile=f"{args.mode}/ComputerUtil.java")
        args.diff.write_text("".join(diff), encoding="utf-8")


if __name__ == "__main__":
    main()
