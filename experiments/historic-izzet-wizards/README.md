# Historic Izzet Wizards Forge gauntlet

Status: **NOT RUN.** No win rates or matchup conclusions are available.

## Requested experiment

Test candidates A, B, and C against seven Historic archetypes: Boros/Mardu Aggro, Dimir Midrange, Izzet Phoenix, Esper Control, Yawgmoth Combo, Affinity, and spell-based combo. Target 200 games per candidate/opponent matchup (100 on the play and 100 on the draw), for 4,200 games total.

## Current compatibility blockers

1. **Asymmetry Sage data is not verified in the available Forge release.** The former rebalanced card name, `A-Symmetry Sage`, was replaced for current Historic play by `Asymmetry Sage` in Alchemy: Reality Fracture, released October 13, 2026. The current card is 0/2 and has Magecraft that sets a target creature's base power to 3. The repository's existing CI example pins Forge 2.0.14 (August 2026); Forge 2.0.15 was released September 28, before the new set. The Forge source searched for this check contains an older `A-Symmetry Sage` definition with 0/3 stats. Do not treat that definition as a match.
2. **Opponent inputs are missing.** The PR currently contains no seven dated, source-linked opponent decklists. Do not substitute invented lists.
3. **The required play/draw balance is not exposed by the documented CLI.** Forge's simulation command accepts an RNG seed (`-s`), deck order, and AI profiles; its documented options do not include a forced starting-player option. A seed alone does not establish 100 games for each seat. The source implementation must be verified before claiming seat-balanced results.
4. **Mulligan behavior must be audited.** All games must use one documented AI profile and the same Forge mulligan behavior. Record the profile and inspect logs for invalid/unparsed games, card loading failures, and timeouts.

The current Historic banned list is maintained at <https://magic.wizards.com/en/banned-restricted-list>. Wizards announced the reversion of rebalanced cards with Historic ban-list changes effective September 22, 2026, and Alchemy: Reality Fracture released October 13, 2026: <https://magic.wizards.com/en/news/mtg-arena/state-of-the-formats-2026>. The new card's text and stats can be checked at <https://scryfall.com/search?q=%21%22Asymmetry+Sage%22>.

Forge's upstream command-line documentation is at <https://github.com/Card-Forge/forge/wiki/AI>. It documents `sim -d ... -D ... -n ... -s ... -a ... -q`, but does not document seat forcing. The CLI source currently available upstream is <https://github.com/Card-Forge/forge/blob/master/forge-gui-desktop/src/main/java/forge/view/SimulateMatch.java>.

## Ready-to-run command once gates pass

Convert each current Arena import list to Forge `.dck` format and place it, with the seven sourced opponent files, in `decks/`. Confirm the Forge JAR's card data reports Asymmetry Sage as 0/2 with the exact Magecraft text before running. Then run each candidate/opponent pair separately with a fixed seed and record raw output, Forge version/hash, AI profile, and deck hashes:

```bash
java -jar forge.jar sim -d Wizards_A.dck Boros_Mardu_Aggro.dck -D "$PWD/decks" -n 200 -s 20261023 -a Default Default -c 120
```

Repeat for the 3 candidates × 7 opponent lists with a unique documented seed per batch. This command is **not sufficient** to claim 100 games on each starting seat. Run the requested experiment only after a supported, verified method controls or reliably labels and stratifies the starting player, and after all seven opponent lists and the card script pass preflight. Do not use mock mode for the experiment.

## Current state

- Candidates A/B/C: 60-card imports, updated to the current card name `Asymmetry Sage`.
- Opponent decklists: not uploaded.
- Compatible Forge runtime: not verified.
- Seat-balanced protocol: not verified.
- Forge simulations: not executed.
