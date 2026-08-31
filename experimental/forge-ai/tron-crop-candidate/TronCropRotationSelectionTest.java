package forge.ai;

import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class TronCropRotationSelectionTest {
    private static Map<String, Integer> counts(Object... pairs) {
        Map<String, Integer> out = new HashMap<>();
        for (int i = 0; i < pairs.length; i += 2) {
            out.put((String)pairs[i], (Integer)pairs[i + 1]);
        }
        return out;
    }

    private static Set<String> set(String... names) {
        return new HashSet<>(Arrays.asList(names));
    }

    private static void require(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }

    private static void requireNull(Object value, String message) {
        require(value == null, message + " expected null but got " + value);
    }

    private static void requireList(List<String> actual, String... expected) {
        require(actual != null, "expected list, got null");
        require(actual.equals(Arrays.asList(expected)), "expected " + Arrays.asList(expected) + " got " + actual);
    }

    public static void main(String[] args) {
        // 1. Mine controlled; Plant/Tower available: unique Mine must not be sacrificed.
        requireList(TronCropRotationSelection.allowedSacrificeNames(
                Arrays.asList("Urza's Mine"),
                counts("Urza's Mine", 1),
                set("Urza's Mine", "Urza's Power Plant", "Urza's Tower")));

        // 2. Plant controlled; Mine/Tower available: unique Plant must not be sacrificed.
        requireList(TronCropRotationSelection.allowedSacrificeNames(
                Arrays.asList("Urza's Power Plant"),
                counts("Urza's Power Plant", 1),
                set("Urza's Mine", "Urza's Power Plant", "Urza's Tower")));

        // 3. Tower controlled; Mine/Plant available: unique Tower must not be sacrificed.
        requireList(TronCropRotationSelection.allowedSacrificeNames(
                Arrays.asList("Urza's Tower"),
                counts("Urza's Tower", 1),
                set("Urza's Mine", "Urza's Power Plant", "Urza's Tower")));

        // 4/5. One missing distinct piece plus expendable Forest: Forest is the only allowed identity.
        requireList(TronCropRotationSelection.allowedSacrificeNames(
                Arrays.asList("Forest", "Urza's Mine", "Urza's Power Plant"),
                counts("Forest", 1, "Urza's Mine", 1, "Urza's Power Plant", 1),
                set("Urza's Tower", "Urza's Mine")),
                "Forest");

        // Duplicate Tron piece is expendable while another distinct piece is available.
        requireList(TronCropRotationSelection.allowedSacrificeNames(
                Arrays.asList("Urza's Mine", "Urza's Mine"),
                counts("Urza's Mine", 2),
                set("Urza's Power Plant", "Urza's Tower", "Urza's Mine")),
                "Urza's Mine", "Urza's Mine");

        // 6. Missing distinct piece absent from library: do not manufacture an unavailable choice.
        requireNull(TronCropRotationSelection.allowedSacrificeNames(
                Arrays.asList("Urza's Mine"),
                counts("Urza's Mine", 1),
                set("Urza's Mine")),
                "missing piece absent from library");

        // 7. Full Tron already assembled: assembly filter must not apply.
        requireNull(TronCropRotationSelection.allowedSacrificeNames(
                Arrays.asList("Forest", "Urza's Mine"),
                counts("Urza's Mine", 1, "Urza's Power Plant", 1, "Urza's Tower", 1),
                set("Urza's Mine", "Urza's Power Plant", "Urza's Tower")),
                "full Tron");

        // 8. Same-piece replacement/nonassembly remains possible when no distinct missing piece is available.
        requireNull(TronCropRotationSelection.allowedSacrificeNames(
                Arrays.asList("Urza's Mine"),
                counts("Urza's Mine", 1, "Urza's Power Plant", 1),
                set("Urza's Mine", "Urza's Power Plant")),
                "legitimate same-piece fallback");

        System.out.println("TronCropRotationSelectionTest PASS");
    }
}
