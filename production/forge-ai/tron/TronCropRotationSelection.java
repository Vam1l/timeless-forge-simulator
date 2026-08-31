package forge.ai;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Narrow candidate helper for Crop Rotation while assembling Urza Tron.
 *
 * This class is deliberately independent of deck name, seed, opponent, and card id.
 * It only decides whether assembly protection applies and which sacrifice identities
 * remain eligible. The caller still uses Forge's normal land valuation to choose a
 * specific Card from the allowed identities.
 */
public final class TronCropRotationSelection {
    private static final List<String> TRON = Arrays.asList(
            "Urza's Mine", "Urza's Power Plant", "Urza's Tower");

    private TronCropRotationSelection() {}

    public static boolean isTronPiece(final String name) {
        return TRON.contains(name);
    }

    public static Set<String> missingAvailablePieces(final Map<String, Integer> battlefieldCounts,
                                                     final Set<String> libraryLandNames) {
        final Set<String> missing = new HashSet<>();
        for (final String piece : TRON) {
            if (battlefieldCounts.getOrDefault(piece, 0) == 0 && libraryLandNames.contains(piece)) {
                missing.add(piece);
            }
        }
        return missing;
    }

    /**
     * Returns null when the assembly rule should not apply and Forge should use its
     * ordinary sacrifice chooser. Returns a possibly-empty list when assembly
     * protection does apply: non-Tron lands are preferred; otherwise duplicate Tron
     * identities are eligible. An empty list means there is no safe assembly sacrifice
     * and the caller must not sacrifice a unique Tron piece merely to refetch it.
     */
    public static List<String> allowedSacrificeNames(final List<String> sacrificeCandidateNames,
                                                     final Map<String, Integer> battlefieldCounts,
                                                     final Set<String> libraryLandNames) {
        final Set<String> missingAvailable = missingAvailablePieces(battlefieldCounts, libraryLandNames);
        if (missingAvailable.isEmpty()) {
            return null;
        }

        final List<String> nonTron = new ArrayList<>();
        for (final String name : sacrificeCandidateNames) {
            if (!isTronPiece(name)) {
                nonTron.add(name);
            }
        }
        if (!nonTron.isEmpty()) {
            return nonTron;
        }

        final List<String> duplicateTron = new ArrayList<>();
        for (final String name : sacrificeCandidateNames) {
            if (isTronPiece(name) && battlefieldCounts.getOrDefault(name, 0) > 1) {
                duplicateTron.add(name);
            }
        }
        return duplicateTron;
    }
}
