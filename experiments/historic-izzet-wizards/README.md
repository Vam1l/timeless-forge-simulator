# Historic Izzet Wizards Forge gauntlet

Status: **NOT RUN — Forge and Arena digital-card compatibility must be verified.**

Test candidates A (baseline), B (aggressive), and C (interactive) against Boros/Mardu Aggro, Dimir Midrange, Izzet Phoenix, Esper Control, Yawgmoth Combo, Affinity, and spell-based combo. Target 200 games per candidate/opponent matchup (100 play, 100 draw), 4,200 total.

Prerequisites: current Historic ban check; verify card name and rules support (particularly **A-Symmetry Sage**); seven dated opponent lists; identical London mulligan policy; controlled starting-player assignment; reproducible Forge version and random seeds; outcome and error logging.

**No results may be inferred from mock mode or unverified Forge support.** Existing wrapper documentation does not guarantee controlled play/draw assignment or digital-card fidelity. Do not run or publish win rates until gates pass.

Source candidate decklists: previous conversation's `historic_izzet_wizards_forge_setup.zip`. Follow-up work: import A/B/C .dck files and opponent decks, implement preflight, add experiment JSON, then run headless engine and review logs.
