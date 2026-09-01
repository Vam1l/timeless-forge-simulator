#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

DESTROY_CLASS_ANCHOR = "public class DestroyAi extends SpellAbilityAi {\n"
DESTROY_ADD_ANCHOR = """                if (wildfireChoice != null) {
                    sa.getTargets().add(wildfireChoice);
                    return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
                }
"""
DESTROY_ADD_INSTRUMENTED = """                if (wildfireChoice != null) {
                    sa.getTargets().add(wildfireChoice);
                    logCleansingWildfirePostSelection(ai, sa);
                    return new AiAbilityDecision(100, AiPlayDecision.WillPlay);
                }
"""
DESTROY_LOG_CALLS = (
    ("logCleansingWildfireTelemetry(legal, new CardCollection(), new CardCollection(), null, \"fallback-empty\");",
     "logCleansingWildfireTelemetry(ai, sa, legal, new CardCollection(), new CardCollection(), null, \"fallback-empty\");"),
    ("logCleansingWildfireTelemetry(legal, ownIndestructible, urza, choice, \"visible-tron\");",
     "logCleansingWildfireTelemetry(ai, sa, legal, ownIndestructible, urza, choice, \"visible-tron\");"),
    ("logCleansingWildfireTelemetry(legal, ownIndestructible, urza, choice, \"self-indestructible\");",
     "logCleansingWildfireTelemetry(ai, sa, legal, ownIndestructible, urza, choice, \"self-indestructible\");"),
    ("logCleansingWildfireTelemetry(legal, ownIndestructible, urza, null, \"stock-fallback\");",
     "logCleansingWildfireTelemetry(ai, sa, legal, ownIndestructible, urza, null, \"stock-fallback\");"),
)
DESTROY_STATE = """    // CWMEASURE-BEGIN diagnostic identity state
    private static final java.util.concurrent.atomic.AtomicLong CW_MEASURE_SEQUENCE =
            new java.util.concurrent.atomic.AtomicLong();
    private static final java.util.Map<SpellAbility, Long> CW_MEASURE_INVOCATIONS =
            java.util.Collections.synchronizedMap(new java.util.IdentityHashMap<>());
    // CWMEASURE-END diagnostic identity state

"""
BASE_LOGGER_RE = re.compile(
    r"    private void logCleansingWildfireTelemetry\(final CardCollection legal,\n"
    r"            final CardCollection ownIndestructible, final CardCollection urza,\n"
    r"            final Card choice, final String reason\) \{\n"
    r"        System\.out\.println\(\"CWAI candidates=\" \+ cleansingWildfireNames\(legal\)\n"
    r"                \+ \" ownIndestructible=\" \+ cleansingWildfireNames\(ownIndestructible\)\n"
    r"                \+ \" opposingHighValue=\" \+ cleansingWildfireNames\(urza\)\n"
    r"                \+ \" selected=\" \+ \(choice == null \? \"<stock>\" : choice\.toString\(\)\)\n"
    r"                \+ \" reason=\" \+ reason\);\n"
    r"    \}\n\n"
)
INSTRUMENTED_LOGGER = '''    // CWMEASURE-BEGIN correlated probe telemetry
    private void logCleansingWildfireTelemetry(final Player ai, final SpellAbility sa,
            final CardCollection legal, final CardCollection ownIndestructible,
            final CardCollection urza, final Card choice, final String reason) {
        final long invocation = CW_MEASURE_SEQUENCE.incrementAndGet();
        CW_MEASURE_INVOCATIONS.put(sa, invocation);
        System.out.println("CWMEASURE kind=probe"
                + " inv=" + invocation
                + " sa=" + System.identityHashCode(sa)
                + " host=" + sa.getHostCard().getId()
                + " player=" + cleansingWildfireToken(ai.toString())
                + " turn=" + ai.getGame().getPhaseHandler().getTurn()
                + " phase=" + cleansingWildfireToken(ai.getGame().getPhaseHandler().getPhase().toString())
                + " candidates=" + cleansingWildfireIds(legal)
                + " own=" + cleansingWildfireIds(ownIndestructible)
                + " high=" + cleansingWildfireIds(urza)
                + " selected=" + (choice == null ? "-" : cleansingWildfireId(choice))
                + " reason=" + reason
                + " targets=" + cleansingWildfireTargetIds(sa)
                + " evaluation=canPlay");
    }

    private void logCleansingWildfirePostSelection(final Player ai, final SpellAbility sa) {
        final Long invocation = CW_MEASURE_INVOCATIONS.get(sa);
        System.out.println("CWMEASURE kind=postselect"
                + " inv=" + (invocation == null ? "-" : invocation)
                + " sa=" + System.identityHashCode(sa)
                + " host=" + sa.getHostCard().getId()
                + " player=" + cleansingWildfireToken(ai.toString())
                + " turn=" + ai.getGame().getPhaseHandler().getTurn()
                + " phase=" + cleansingWildfireToken(ai.getGame().getPhaseHandler().getPhase().toString())
                + " targets=" + cleansingWildfireTargetIds(sa)
                + " evaluation=canPlay");
    }

    private String cleansingWildfireIds(final Iterable<Card> cards) {
        final StringBuilder out = new StringBuilder();
        boolean first = true;
        for (Card c : cards) {
            if (!first) {
                out.append(',');
            }
            first = false;
            out.append(cleansingWildfireId(c));
        }
        return out.length() == 0 ? "-" : out.toString();
    }

    private String cleansingWildfireTargetIds(final SpellAbility sa) {
        return cleansingWildfireIds(sa.getTargets().getTargetCards());
    }

    private String cleansingWildfireId(final Card card) {
        return cleansingWildfireToken(card.getName()) + "#" + card.getId();
    }

    private String cleansingWildfireToken(final String value) {
        return value == null ? "-" : value.replaceAll("[^A-Za-z0-9_'()-]+", "_");
    }
    // CWMEASURE-END correlated probe telemetry

'''
BASE_LOGGER = '''    private void logCleansingWildfireTelemetry(final CardCollection legal,
            final CardCollection ownIndestructible, final CardCollection urza,
            final Card choice, final String reason) {
        System.out.println("CWAI candidates=" + cleansingWildfireNames(legal)
                + " ownIndestructible=" + cleansingWildfireNames(ownIndestructible)
                + " opposingHighValue=" + cleansingWildfireNames(urza)
                + " selected=" + (choice == null ? "<stock>" : choice.toString())
                + " reason=" + reason);
    }

'''
STACK_PUSH_ANCHOR = """        // The ability is added to stack HERE
        push(sp, si, id);
"""
STACK_PUSH_INSTRUMENTED = '''        // The ability is added to stack HERE
        // CWMEASURE-BEGIN committed-cast telemetry
        if (sp.isSpell() && "Cleansing Wildfire".equals(source.getName())) {
            System.out.println("CWMEASURE kind=commit"
                    + " sa=" + System.identityHashCode(sp)
                    + " host=" + source.getId()
                    + " player=" + cleansingWildfireCommitToken(activator.toString())
                    + " turn=" + game.getPhaseHandler().getTurn()
                    + " phase=" + cleansingWildfireCommitToken(game.getPhaseHandler().getPhase().toString())
                    + " targets=" + cleansingWildfireCommitTargets(sp)
                    + " committed=true");
        }
        // CWMEASURE-END committed-cast telemetry
        push(sp, si, id);
'''
STACK_HELPER_ANCHOR = """    public final void add(SpellAbility sp) {
"""
STACK_HELPERS = '''    // CWMEASURE-BEGIN commitment formatting helpers
    private String cleansingWildfireCommitTargets(final SpellAbility sa) {
        final StringBuilder out = new StringBuilder();
        boolean first = true;
        for (Card c : sa.getTargets().getTargetCards()) {
            if (!first) {
                out.append(',');
            }
            first = false;
            out.append(cleansingWildfireCommitToken(c.getName())).append('#').append(c.getId());
        }
        return out.length() == 0 ? "-" : out.toString();
    }

    private String cleansingWildfireCommitToken(final String value) {
        return value == null ? "-" : value.replaceAll("[^A-Za-z0-9_'()-]+", "_");
    }
    // CWMEASURE-END commitment formatting helpers

'''

def instrument_destroy(text: str) -> str:
    original = text
    if text.count(DESTROY_CLASS_ANCHOR) != 1:
        raise RuntimeError("DestroyAi class anchor count mismatch")
    text = text.replace(DESTROY_CLASS_ANCHOR, DESTROY_CLASS_ANCHOR + DESTROY_STATE, 1)
    if text.count(DESTROY_ADD_ANCHOR) != 1:
        raise RuntimeError("DestroyAi selected-target anchor count mismatch")
    text = text.replace(DESTROY_ADD_ANCHOR, DESTROY_ADD_INSTRUMENTED, 1)
    for old, new in DESTROY_LOG_CALLS:
        if text.count(old) != 1:
            raise RuntimeError("DestroyAi telemetry call anchor mismatch: " + old)
        text = text.replace(old, new, 1)
    match = BASE_LOGGER_RE.search(text)
    if not match:
        raise RuntimeError("baseline DestroyAi telemetry logger anchor not found")
    text = text[:match.start()] + INSTRUMENTED_LOGGER + text[match.end():]
    if strip_destroy(text) != original:
        raise RuntimeError("DestroyAi diagnostic overlay is not exactly reversible")
    return text

def strip_destroy(text: str) -> str:
    text = text.replace(DESTROY_STATE, "", 1)
    text = text.replace(DESTROY_ADD_INSTRUMENTED, DESTROY_ADD_ANCHOR, 1)
    for old, new in DESTROY_LOG_CALLS:
        text = text.replace(new, old, 1)
    text = text.replace(INSTRUMENTED_LOGGER, BASE_LOGGER, 1)
    return text

def instrument_stack(text: str) -> str:
    original = text
    if text.count(STACK_HELPER_ANCHOR) != 1:
        raise RuntimeError("MagicStack helper anchor count mismatch")
    if text.count(STACK_PUSH_ANCHOR) != 1:
        raise RuntimeError("MagicStack push anchor count mismatch")
    text = text.replace(STACK_HELPER_ANCHOR, STACK_HELPERS + STACK_HELPER_ANCHOR, 1)
    text = text.replace(STACK_PUSH_ANCHOR, STACK_PUSH_INSTRUMENTED, 1)
    if strip_stack(text) != original:
        raise RuntimeError("MagicStack diagnostic overlay is not exactly reversible")
    return text

def strip_stack(text: str) -> str:
    text = text.replace(STACK_HELPERS, "", 1)
    text = text.replace(STACK_PUSH_INSTRUMENTED, STACK_PUSH_ANCHOR, 1)
    return text

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--destroy-input", required=True, type=Path)
    p.add_argument("--destroy-output", required=True, type=Path)
    p.add_argument("--stack-input", required=True, type=Path)
    p.add_argument("--stack-output", required=True, type=Path)
    p.add_argument("--verify-destroy-output", type=Path)
    p.add_argument("--verify-stack-output", type=Path)
    args = p.parse_args()
    destroy_base = args.destroy_input.read_text()
    stack_base = args.stack_input.read_text()
    destroy_out = instrument_destroy(destroy_base)
    stack_out = instrument_stack(stack_base)
    args.destroy_output.parent.mkdir(parents=True, exist_ok=True)
    args.stack_output.parent.mkdir(parents=True, exist_ok=True)
    args.destroy_output.write_text(destroy_out)
    args.stack_output.write_text(stack_out)
    if args.verify_destroy_output:
        args.verify_destroy_output.parent.mkdir(parents=True, exist_ok=True)
        args.verify_destroy_output.write_text(strip_destroy(destroy_out))
    if args.verify_stack_output:
        args.verify_stack_output.parent.mkdir(parents=True, exist_ok=True)
        args.verify_stack_output.write_text(strip_stack(stack_out))

if __name__ == "__main__":
    main()
