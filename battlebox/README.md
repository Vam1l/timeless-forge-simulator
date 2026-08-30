## Peasant+ 10-Deck Forge Round-Robin Stage 2

This directory contains the baseline AI-vs-AI balance test for a 10-archetype Peasant+ format using Forge 2.0.14.

### Scope

- **10 archetypes**: White Weenie, Madness Burn, Green Stompy, Black Sacrifice, Blue Terror, Jund Wildfire, Esper Control, Sultai Beans, Hunting Storm, Tron
- **45 matchups / 90 orientations**: every pairing is run in both seat orders
- **18,000 total games**: 200 games per orientation, distributed across a 9-job matrix
- **Forge version**: 2.0.14
- **Baseline policy**: validate the complete run before making balance changes

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
- 90 oriented runs generated from 10 decks (45 unordered matchups)
- 200 games per orientation / 400 games per unordered matchup
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

2. **Forge Setup** (`forge` job)
   - Downloads/caches Forge 2.0.14

3. **Parallel Simulation** (`simulate` matrix with 9 batches)
   - Each runs 10 orientations × 200 games
   - Preserves raw Forge logs
   - Outputs per-batch CSV and JSON summaries

4. **Aggregation** (`report` job)
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
gh workflow run peasant-10deck-baseline.yml
```

The full 18,000-game run is manual-only so ordinary commits do not consume hours of Actions time.

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

**Balance policy:**
- Do not tune from partial batches or the small behavioral smoke tests.
- Require 90 completed orientations, 18,000 accounted games, and zero unparsed games.
- Treat results from complex control/combo decks as AI-performance evidence as well as deck-balance evidence.

### Next Steps

After baseline completion:
1. Review flagged decks and matchups
2. Analyze Forge AI behavior in control/combo matchups
3. Plan deck refinements for v1.1 (if desired)
4. Document any cards that Forge mishandled
