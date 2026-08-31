package forge.ai;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Narrow Crop Rotation protection while assembling Urza Tron. */
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
     * Null means use Forge's normal chooser. A non-null list limits legal sacrifice
     * identities while another distinct Tron piece is both missing and available.
     */
    public static List<String> allowedSacrificeNames(final List<String> sacrificeCandidateNames,
                                                     final Map<String, Integer> battlefieldCounts,
                                                     final Set<String> libraryLandNames) {
        if (missingAvailablePieces(battlefieldCounts, libraryLandNames).isEmpty()) {
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
