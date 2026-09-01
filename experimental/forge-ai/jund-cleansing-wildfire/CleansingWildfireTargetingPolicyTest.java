package forge.ai.ability;

public final class CleansingWildfireTargetingPolicyTest {
    private static void expect(String name,
            CleansingWildfireTargetingPolicy.Decision actual,
            CleansingWildfireTargetingPolicy.Decision expected) {
        if (actual != expected) {
            throw new AssertionError(name + ": expected " + expected + " but got " + actual);
        }
    }

    public static void main(String[] args) {
        using("own indestructible Bridge versus opponent basic", true, 0, true,
                CleansingWildfireTargetingPolicy.Decision.SELF_INDESTRUCTIBLE);
        using("own Bridge versus replaceable opponent nonbasic", true, 0, true,
                CleansingWildfireTargetingPolicy.Decision.SELF_INDESTRUCTIBLE);
        using("own Bridge versus opposing Urza assembly", true, 2, true,
                CleansingWildfireTargetingPolicy.Decision.DISRUPT_VISIBLE_TRON);
        using("multiple eligible own Bridges", true, 0, true,
                CleansingWildfireTargetingPolicy.Decision.SELF_INDESTRUCTIBLE);
        using("no eligible own Bridge", true, 0, false,
                CleansingWildfireTargetingPolicy.Decision.PRESERVE_STOCK);
        using("own land not indestructible", true, 0, false,
                CleansingWildfireTargetingPolicy.Decision.PRESERVE_STOCK);
        using("illegal or untargetable Bridge", true, 0, false,
                CleansingWildfireTargetingPolicy.Decision.PRESERVE_STOCK);
        using("unrelated land destruction spell", false, 3, true,
                CleansingWildfireTargetingPolicy.Decision.PRESERVE_STOCK);
        using("Cleansing Wildfire controlled by non-Jund deck", true, 0, true,
                CleansingWildfireTargetingPolicy.Decision.SELF_INDESTRUCTIBLE);
        using("no-target and empty-candidate safety", true, 0, false,
                CleansingWildfireTargetingPolicy.Decision.PRESERVE_STOCK);
        using("ordinary Forge fallback", true, 1, false,
                CleansingWildfireTargetingPolicy.Decision.PRESERVE_STOCK);
        System.out.println("CleansingWildfireTargetingPolicyTest: PASS");
    }

    private static void using(String name, boolean signature, int urza, boolean ownIndestructible,
            CleansingWildfireTargetingPolicy.Decision expected) {
        expect(name,
                CleansingWildfireTargetingPolicy.decide(signature, urza, ownIndestructible),
                expected);
    }
}
