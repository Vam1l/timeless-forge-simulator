package forge.ai.ability;

public final class CleansingWildfireTargetingPolicyTest {
    private static void using(final String name, final boolean exact,
            final int distinctUrza, final boolean ownIndestructible,
            final CleansingWildfireTargetingPolicy.Decision expected) {
        final CleansingWildfireTargetingPolicy.Decision actual =
                CleansingWildfireTargetingPolicy.decide(exact, distinctUrza, ownIndestructible);
        if (actual != expected) {
            throw new AssertionError(name + ": expected " + expected + " but got " + actual);
        }
    }

    public static void main(String[] args) {
        using("own indestructible Bridge preference", true, 0, true,
                CleansingWildfireTargetingPolicy.Decision.SELF_INDESTRUCTIBLE);
        using("Mine plus Plant visible", true, 2, true,
                CleansingWildfireTargetingPolicy.Decision.DISRUPT_VISIBLE_TRON);
        using("Mine plus Tower visible", true, 2, true,
                CleansingWildfireTargetingPolicy.Decision.DISRUPT_VISIBLE_TRON);
        using("Plant plus Tower visible", true, 2, true,
                CleansingWildfireTargetingPolicy.Decision.DISRUPT_VISIBLE_TRON);
        using("duplicate Plants only", true, 1, true,
                CleansingWildfireTargetingPolicy.Decision.SELF_INDESTRUCTIBLE);
        using("duplicate Mines only", true, 1, true,
                CleansingWildfireTargetingPolicy.Decision.SELF_INDESTRUCTIBLE);
        using("no Bridge", true, 0, false,
                CleansingWildfireTargetingPolicy.Decision.PRESERVE_STOCK);
        using("one distinct Urza plus Bridge", true, 1, true,
                CleansingWildfireTargetingPolicy.Decision.SELF_INDESTRUCTIBLE);
        using("unrelated destruction spell", false, 3, true,
                CleansingWildfireTargetingPolicy.Decision.PRESERVE_STOCK);
        using("illegal self land excluded before policy", true, 0, false,
                CleansingWildfireTargetingPolicy.Decision.PRESERVE_STOCK);
        using("empty candidate safety", true, 0, false,
                CleansingWildfireTargetingPolicy.Decision.PRESERVE_STOCK);
        System.out.println("CleansingWildfireTargetingPolicyTest: PASS");
    }
}
