#!/usr/bin/env python3
"""Add observational Crop Rotation fetch-choice telemetry to a temporary recovered ChangeZoneAi copy."""
from pathlib import Path
import argparse
import difflib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--diff", type=Path)
    args = ap.parse_args()
    original = args.input.read_text(encoding="utf-8")
    anchor = "                    c = ComputerUtilCard.getBestLandAI((Iterable<Card>)fetchList);\n"
    if original.count(anchor) != 1:
        raise SystemExit("expected exact recovered getBestLandAI fetch anchor")
    replacement = anchor + r'''                    if (sa != null && sa.getHostCard() != null
                            && "Crop Rotation".equals(sa.getHostCard().getName())
                            && sa.getApi() == ApiType.ChangeZone
                            && "Library".equals(sa.getParamOrDefault("Origin", ""))
                            && "Battlefield".equals(sa.getParamOrDefault("Destination", ""))
                            && sa.getParamOrDefault("ChangeType", "").contains("Land")) {
                        final CardCollectionView tronCropField = decider.getCardsIn(ZoneType.Battlefield);
                        final List<String> tronCropPresent = new ArrayList<>();
                        for (final String piece : Arrays.asList("Urza's Mine", "Urza's Power Plant", "Urza's Tower")) {
                            if (!CardLists.filter((Iterable)tronCropField, (Predicate)CardPredicates.nameEquals(piece)).isEmpty()) {
                                tronCropPresent.add(piece);
                            }
                        }
                        System.out.println("[TRON_CROP_FETCH] host=" + sa.getHostCard().getName()
                                + " fetchCandidates=" + fetchList.stream().map(Card::getName).collect(Collectors.toList())
                                + " selected=" + (c == null ? "none" : c.getName() + "#" + c.getId())
                                + " battlefieldTronBeforeFetch=" + tronCropPresent);
                    }
'''
    patched = original.replace(anchor, replacement, 1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(patched, encoding="utf-8")
    if args.diff:
        args.diff.parent.mkdir(parents=True, exist_ok=True)
        diff = difflib.unified_diff(original.splitlines(True), patched.splitlines(True),
            fromfile="recovered/ChangeZoneAi.java", tofile="diagnostic/ChangeZoneAi.java")
        args.diff.write_text("".join(diff), encoding="utf-8")


if __name__ == "__main__":
    main()
