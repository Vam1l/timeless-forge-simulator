# Experimental Forge AI repair validation

This branch recovers and validates the final historical Forge 2.0.14 AI repair state from closed PR #2. It does not alter any battle-box deck and does not rerun the 18,000-game stock baseline.

## Provenance

- Current `main` at branch creation: `ee667eb8b110cd985578eef2acc3e9c97db861c8`
- Closed PR #2 final SHA: `237300550e94586479bba9b1c6123af3e87cb179`
- Initial targeted Hunting Storm / Tron / Esper implementation: `e26a34c153ca97581097fa87b473e96c57be53ed`
- Consolidated mana-filter / Storm / Tron / Prismatic Strands / TwoPiles / Supreme Verdict fixes: `eac89e561a62ffde39598c4a4dfa65cb939f4aad`
- Byte-vs-Integer safety fix: `ffdf24d974886a77bd0714836bdd8c0a1f047b87` and follow-up `f06a86e54c06567763074a90cafae5fca576c75e`
- Prismatic Strands timing/color and Hunting Pack preservation refinements: `4f07f1ced6901d24cebabb250d0bd103323de373`, `12e28b3df26054662a8b95d4534c80f5310bc7ee`
- Setup-permanent filtering: `a0c3af661135b5a761d5bdf5bf11e20597807508`
- Final targeted state: `237300550e94586479bba9b1c6123af3e87cb179`

## Recovery method

All Java files under `experimental/forge-ai/forge-patches/` are referenced by the exact Git blob SHA from PR #2's final tree. They are not reconstructed or rewritten.

`verify_recovered_blobs.py` is a mandatory repository-validation gate. It requires the files under `experimental/forge-ai/forge-patches/` to exactly match the documented recovered-file set and verifies each file byte-for-byte with `git hash-object --no-filters` against `RECOVERED_BLOBS.txt`. Any content change, including whitespace normalization, causes validation to fail.

## Historical whitespace exclusion

The recovered Forge source blobs contain pre-existing trailing whitespace and EOF blank lines from the historical PR #2 blobs. Normalizing those bytes would make the provenance claim false, so the general `git diff --check` gate excludes only `experimental/forge-ai/forge-patches/**`.

That exclusion is deliberately narrow. `git diff --check` still covers every newly authored workflow, validation script, test, and documentation file in this PR. The excluded historical source tree is subject to the stricter blob-integrity gate above, plus the unchanged Forge compilation, deterministic-scenario, runtime-safety, behavioral, exception, timeout, unparsed-game, deck-identity, and stopping gates.

## Forge constructed-deck harness

Run #2 established that Forge 2.0.14 resolves named constructed decks from the runner user-data directory (`~/.forge/decks/constructed/`) even when the repository deck directory is supplied to the simulation command. The resulting `No deck found` / `Could not load deck` messages meant no game started, so those logs were harness failures and contained no AI behavioral evidence.

Before either Phase 3 scenarios or focused A/B games, `prepare_forge_decks.py` copies the unchanged ten `battlebox/decks/*.dck` files into the resolved runner home directory and verifies every installed file byte-for-byte against the repository source. Each simulation script then performs a one-game deck-loading preflight. Behavioral execution is forbidden unless the requested deck files exist, no deck-load/runtime marker occurs, the match starts, and a parsed game result is produced. Any later deck-load failure is classified as a harness/runtime failure and stops the stage rather than being reported as a failure to demonstrate an AI behavior.

## Deliberately excluded from PR #2

- Every battle-box deck edit
- Forge JARs, executables, distributions, launchers, resources, and copied Forge documentation
- Historical generated logs and diagnostic results
- Old baseline/diagnostic workflows and temporary configs
- Root-level scratch analysis scripts and PR helper files
- Unrelated Forge source/material outside the final targeted patch set

## Validation interpretation

Compilation, absence of exceptions, and win rate are necessary but insufficient evidence. Behavioral acceptance requires verbose logs demonstrating that the intended decision paths were reached and that the patched AI selected materially improved legal actions without regressions.

The historical 18-game smoke output is retained only as context; it did **not** demonstrate Hunting Storm repair because it reported zero Chromatic Star/Sphere activations and zero original Hunting Pack casts. The new validation therefore starts with fixed-seed behavioral scenarios and stops before A/B simulation if those paths are not demonstrated.
