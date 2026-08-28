# Pull Request: Add Peasant+ 10-Deck Forge Round-Robin Baseline

This PR adds a complete baseline v1.0 AI-vs-AI balance test framework for 10 Peasant+ archetypes.

## Overview

- **10 decks**: White Weenie, Madness Burn, Green Stompy, Black Sacrifice, Blue Terror, Jund Wildfire, Esper Control, Sultai Beans, Hunting Storm, Tron
- **45 matchups**: Every unique pairing, 400 games each = 18,000 total games
- **Forge 2.0.14**: Real engine, not mock
- **9-job parallel matrix**: Approximately 5 matchups per GitHub Actions job
- **Comprehensive reporting**: Deck stats, 10×10 matchup matrix, balance flags, anomaly detection

## Files Added

### Deck Files (exactly 60 cards each)
- `battlebox/decks/01-white-weenie.dck` through `battlebox/decks/10-tron.dck`
- `battlebox/roundrobin.json` — configuration with 45 matchups

### Configuration & Documentation
- `battlebox/README.md` — comprehensive baseline documentation
- `battlebox/unsupported-card-substitutions.md` — card compatibility tracker

### Python Infrastructure
- `timeless_forge/deck.py` — deck loading and validation
- `timeless_forge/runner.py` — Forge execution and game parsing
- `timeless_forge/stats.py` — Wilson score confidence intervals
- `scripts/validate_battlebox.py` — deck validation (exactly 60 cards)
- `scripts/validate_cards.py` — Forge card recognition check
- `scripts/run_matchup_batch.py` — batch simulation executor
- `scripts/aggregate_results.py` — results aggregation
- `scripts/build_results_report.py` — report generation
- `scripts/check_anomalies.py` — anomaly detection
- `tests/test_deck_validation.py` — unit tests
- `tests/test_parser.py` — output parsing tests

### GitHub Actions Workflow
- `.github/workflows/peasant-10deck-baseline.yml` — 9-job parallel simulation with validation and aggregation

## Key Design Decisions

1. **Exactly 60 cards per deck** — enforced by validation
2. **Real Forge engine only** — no mock results in baseline
3. **Raw log retention** — all Forge output preserved for diagnostics
4. **No post-results tuning** — v1.0 is frozen
5. **Unsupported card tracking** — substitutions clearly documented
6. **Comprehensive anomaly detection** — timeouts, unparsed games, incomplete batches surfaced
7. **Balance flags** — decks outside 45–55%, matchups beyond 65/35

## Caveats & Disclaimers

- **Forge AI limitations**: Strongest on aggro/midrange, weaker on control/combo
- **Decision-intensive decks**: Esper Control, Sultai Beans, Hunting Storm results more AI-sensitive
- **Frozen baseline**: No rebalancing after v1.0 completes

## Workflow Usage

Manually trigger:
```bash
gh workflow run peasant-10deck-baseline.yml -r ai-balance/peasant-10deck-roundrobin
```

Or via GitHub UI: Actions → "Peasant+ 10-Deck Forge Round-Robin Baseline" → "Run workflow"

Workflow also auto-triggers on pushes to this branch.

## Expected Results

After workflow completion:
- Artifact: `forge-balance-results` (CSV, JSON, Markdown report, raw logs)
- Deck statistics: win rates with 95% CI
- Matchup matrix: 10×10 grid of win rates
- Balance flags: decks/matchups outside target ranges
- Anomaly report: unparsed games, timeouts, incomplete batches

## Next Steps

1. Run baseline workflow
2. Review results and flagged decks
3. Analyze Forge AI behavior in control/combo
4. Plan v1.1 improvements (if any) without modifying v1.0
