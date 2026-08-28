# Peasant+ 10-Deck Baseline Infrastructure Checklist

## ✅ Completed

### Deck Files (exactly 60 cards each)
- ✅ 01-white-weenie.dck
- ✅ 02-madness-burn.dck
- ✅ 03-green-stompy.dck
- ✅ 04-black-sacrifice.dck
- ✅ 05-blue-terror.dck
- ✅ 06-jund-wildfire.dck
- ✅ 07-esper-control.dck
- ✅ 08-sultai-beans.dck
- ✅ 09-hunting-storm.dck
- ✅ 10-tron.dck

### Configuration
- ✅ battlebox/roundrobin.json (45 matchups × 400 games each)
- ✅ battlebox/unsupported-card-substitutions.md
- ✅ battlebox/README.md (comprehensive documentation)

### Python Infrastructure
- ✅ timeless_forge/__init__.py
- ✅ timeless_forge/deck.py (deck loading & validation)
- ✅ timeless_forge/runner.py (Forge execution & parsing)
- ✅ timeless_forge/stats.py (Wilson confidence intervals)
- ✅ pyproject.toml (package metadata)

### Validation & Execution Scripts
- ✅ scripts/validate_battlebox.py (60-card enforcement)
- ✅ scripts/validate_cards.py (Forge card recognition)
- ✅ scripts/run_matchup_batch.py (batch executor)
- ✅ scripts/aggregate_results.py (result aggregation)
- ✅ scripts/build_results_report.py (Markdown + CSV reporting)
- ✅ scripts/check_anomalies.py (anomaly detection)
- ✅ scripts/__init__.py

### Tests
- ✅ tests/test_deck_validation.py
- ✅ tests/test_parser.py

### GitHub Actions
- ✅ .github/workflows/peasant-10deck-baseline.yml (9-job matrix)
  - Validate job
  - Forge setup job
  - 9 simulation jobs (batches 1–9)
  - Aggregate & reporting job

### Documentation
- ✅ PR_DESCRIPTION.md (comprehensive PR body)
- ✅ CREATE_PR_INSTRUCTIONS.md (manual PR steps)
- ✅ BASELINE_CHECKLIST.md (this file)

## 🔄 Next Steps

### 1. Create Pull Request

Use one of:

**GitHub CLI:**
```bash
gh pr create --repo Vam1l/timeless-forge-simulator \
  --head ai-balance/peasant-10deck-roundrobin \
  --base main \
  --title "Add Peasant+ 10-deck Forge round-robin baseline" \
  --body-file PR_DESCRIPTION.md
```

**GitHub Web UI:**
- Go to https://github.com/Vam1l/timeless-forge-simulator
- Compare `ai-balance/peasant-10deck-roundrobin` → `main`
- Title: "Add Peasant+ 10-deck Forge round-robin baseline"
- Body: Copy from `PR_DESCRIPTION.md`

### 2. Trigger Workflow

After PR created, workflow auto-triggers or manually run:
```bash
gh workflow run peasant-10deck-baseline.yml -r ai-balance/peasant-10deck-roundrobin
```

### 3. Monitor Execution

- **Validation** (~2 min): Unit tests + deck structure check
- **Forge Setup** (~1 min): Download/cache Forge 2.0.14
- **9 Parallel Simulations** (~60–120 min each depending on CI runners):
  - Each batch: ~5 matchups × 400 games = 2,000 games
  - Total: 45 matchups × 400 games = 18,000 games
- **Aggregation** (~5 min): Combine results, generate report

### 4. Review Results

After workflow completes:
- Check artifact `forge-balance-results`
- Review `report.md` for:
  - Overall deck win rates (flagged if outside 45–55%)
  - 10×10 matchup matrix (flagged if outside 35–65%)
  - Anomaly report (unparsed games, timeouts)
  - Balance assessment

### 5. Document Findings

- Note any Forge AI quirks (especially control/combo)
- Identify decks that need rebalancing
- Plan v1.1 changes (NOT in v1.0)

## 📋 Baseline v1.0 Policy

- **Frozen after creation**: No deck changes
- **Raw data preserved**: All Forge logs retained
- **Unsupported cards tracked**: Substitutions documented
- **Future improvements**: v1.1+ only

## 🎯 Success Criteria

- ✅ All 45 matchups complete with 400 games each
- ✅ No more than 5% unparsed games per matchup
- ✅ All decks in 45–55% win rate band (ideally)
- ✅ No catastrophic Forge AI failures
- ✅ Comprehensive report generated

## 📞 Troubleshooting

**Workflow fails on validation:**
- Check deck files for card count (must be exactly 60)
- Run `python scripts/validate_battlebox.py` locally

**High unparsed game counts:**
- Check Forge logs for error patterns
- May indicate Forge AI crash or timeout
- Update `CLOCK_SECONDS` if needed

**Balance severely off:**
- Normal for AI-based testing (Forge AI ≠ optimal play)
- Document findings for v1.1 planning
- Do NOT modify decks in v1.0
