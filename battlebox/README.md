## Peasant+ 10-Deck Forge Round-Robin Baseline v1.0

This directory contains the baseline AI-vs-AI balance test for a 10-archetype Peasant+ format using Forge 2.0.14.

### Scope

- **10 archetypes**: White Weenie, Madness Burn, Green Stompy, Black Sacrifice, Blue Terror, Jund Wildfire, Esper Control, Sultai Beans, Hunting Storm, Tron
- **45 matchups**: All unique pairings, each played exactly 400 times preboard
- **18,000 total games**: Distributed across 9 parallel GitHub Actions jobs
- **Forge version**: 2.0.14
- **Baseline policy**: No deck tuning after results are generated

### Deck Files

All deck files are in `battlebox/decks/`:
- `01-white-weenie.dck` (60 cards)
- `02-madness-burn.dck` (60 cards)
- `03-green-stompy.dck` (60 cards)
- `04-black-sacrifice.dck` (60 cards)
- `05-blue-terror.dck` (60 cards)
- `06-jund-wildfire.dck` (60 cards)
- `07-esper-control.dck` (60 cards)
- `08-sultai-beans.dck` (60 cards)
- `09-hunting-storm.dck` (60 cards)
- `10-tron.dck` (60 cards)

Each deck is exactly 60 main-deck cards with empty sideboards for baseline v1.0.

### Configuration

The round-robin configuration is defined in `battlebox/roundrobin.json`:
- 45 matchups generated from 10 decks
- 400 preboard games per matchup
- 120-second game timeout per Forge
- Pre-board only (no sideboarding for baseline)

### Unsupported Card Substitutions

See `battlebox/unsupported-card-substitutions.md` for any Forge 2.0.14 compatibility substitutions.

If a card is not recognized by Forge during simulation, it is documented there with:
- Original card name
- Replacement card name
- Functional reason
- Affected deck(s)

### Workflow

The GitHub Actions workflow (`.github/workflows/peasant-10deck-baseline.yml`) performs:

1. **Validation** (`validate` job)
   - Unit tests
   - Deck structure (exactly 60 cards)
   - Matchup configuration

2. **Forge Setup** (`forge-setup` job)
   - Downloads/caches Forge 2.0.14

3. **Parallel Simulation** (9 jobs: `simulate-batch-1` through `simulate-batch-9`)
   - Each runs ~5 matchups × 400 games
   - Preserves raw Forge logs
   - Outputs per-batch CSV and JSON summaries

4. **Aggregation** (`aggregate-results` job)
   - Combines all batch results
   - Builds final deck statistics
   - Generates 10×10 matchup matrix
   - Produces Markdown report and JSON output
   - Checks for anomalies (timeouts, unparsed games)
   - Flags decks outside 45–55% win rate
   - Flags matchups outside 35–65% range

### Running the Workflow

To manually trigger the workflow:

```bash
# From GitHub UI:
# 1. Go to Actions → "Peasant+ 10-Deck Forge Round-Robin Baseline"
# 2. Click "Run workflow" → "Run workflow"

# Or via GitHub CLI:
gh workflow run peasant-10deck-baseline.yml -r ai-balance/peasant-10deck-roundrobin
```

The workflow is also triggered automatically on any push to the `ai-balance/peasant-10deck-roundrobin` branch.

### Results

Results are saved under `results/peasant-10deck-baseline/` after the workflow completes:

- `combined-results.csv` — all batch results in tabular form
- `combined-results.json` — all batch results as JSON objects
- `deck-stats.csv` — aggregated win rates per deck
- `report.md` — human-readable Markdown report with 10×10 matrix
- `raw-logs/` — raw Forge output for each matchup

A final artifact `forge-balance-results` is uploaded containing all outputs.

### Interpreting Results

**Overall deck statistics:**
- Games played (should be ~1800 per deck across all matchups)
- Wins, losses, draws
- Overall win rate ± 95% confidence interval
- Flagged if outside 45–55%

**Matchup matrix:**
- 10×10 grid showing row deck's win rate vs column deck
- Reciprocal cells should be consistent (e.g., A vs B ≈ 100% – B vs A)
- Flagged if more extreme than approximately 65/35

**Balance flags:**
- Decks with overall win rate < 45% or > 55%
- Matchups with win rate < 35% or > 65%
- High unparsed game counts (> 5%)
- Incomplete batches

### Caveats

**Forge AI limitations:**
- Forge AI is strongest on straightforward aggro/midrange strategies
- Esper Control, Sultai Beans, Hunting Storm, and other decision-intensive decks are more sensitive to Forge AI quality
- This baseline reflects Forge AI quality, not necessarily optimal human play
- Some results may be skewed by Forge's heuristics, especially in control mirrors and combo matchups

**Frozen baseline:**
- This is v1.0 and is NOT retuned after initial results
- No deck changes based on win rates
- Any tuning improvements happen in future versions (v1.1+)

### Next Steps

After baseline completion:
1. Review flagged decks and matchups
2. Analyze Forge AI behavior in control/combo matchups
3. Plan deck refinements for v1.1 (if desired)
4. Document any cards that Forge mishandled
