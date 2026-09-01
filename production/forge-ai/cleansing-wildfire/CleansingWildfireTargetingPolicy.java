package forge.ai.ability;

/**
 * Narrow policy gate for Cleansing Wildfire target overrides.
 *
 * This class intentionally contains no deck-specific state and no Forge card
 * objects so the policy can be tested deterministically before gameplay.
 */
public final class CleansingWildfireTargetingPolicy {
    private CleansingWildfireTargetingPolicy() {}

    public enum Decision {
        PRESERVE_STOCK,
        DISRUPT_VISIBLE_TRON,
        SELF_INDESTRUCTIBLE
    }

    /**
     * Decide whether the Cleansing Wildfire hook should override stock Forge.
     *
     * @param isExactCleansingWildfireStructure exact Destroy -> optional basic
     *        search for TargetedController -> Draw structure
     * @param visibleDistinctOpponentUrzaPieces number of distinct Mine/Tower/
     *        Power Plant names among legal opponent battlefield targets
     * @param hasEligibleOwnIndestructibleLand whether a legal, targetable,
     *        indestructible land controlled by the caster exists
     * @return override class, or PRESERVE_STOCK when normal Forge should run
     */
    public static Decision decide(
            final boolean isExactCleansingWildfireStructure,
            final int visibleDistinctOpponentUrzaPieces,
            final boolean hasEligibleOwnIndestructibleLand) {
        if (!isExactCleansingWildfireStructure) {
            return Decision.PRESERVE_STOCK;
        }
        if (visibleDistinctOpponentUrzaPieces >= 2) {
            return Decision.DISRUPT_VISIBLE_TRON;
        }
        if (hasEligibleOwnIndestructibleLand) {
            return Decision.SELF_INDESTRUCTIBLE;
        }
        return Decision.PRESERVE_STOCK;
    }
}
