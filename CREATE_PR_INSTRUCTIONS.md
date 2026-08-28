# Manual PR Creation Instructions

If `gh` CLI is not available, follow these steps:

## Option 1: GitHub Web UI

1. Navigate to: https://github.com/Vam1l/timeless-forge-simulator
2. Click **"New pull request"** button
3. Set:
   - **Compare branch** (head): `ai-balance/peasant-10deck-roundrobin`
   - **Base branch**: `main`
4. Click **"Create pull request"**
5. Fill in:
   - **Title**: `Add Peasant+ 10-deck Forge round-robin baseline`
   - **Body**: Copy entire contents from `PR_DESCRIPTION.md`
6. Click **"Create pull request"**

## Option 2: GitHub CLI

```bash
gh pr create --repo Vam1l/timeless-forge-simulator \
  --head ai-balance/peasant-10deck-roundrobin \
  --base main \
  --title "Add Peasant+ 10-deck Forge round-robin baseline" \
  --body-file PR_DESCRIPTION.md
```

## After PR Creation

1. **Workflow auto-triggers** on push, or manually trigger:
   ```bash
   gh workflow run peasant-10deck-baseline.yml -r ai-balance/peasant-10deck-roundrobin
   ```

2. **Monitor progress**:
   - 9 parallel simulation jobs (roughly 5 matchups each)
   - Validation step runs first
   - Aggregation runs after all jobs complete
   - Total: ~18,000 games

3. **Review results**:
   - Artifact: `forge-balance-results` contains all outputs
   - Files: `deck-stats.csv`, `report.md`, matchup matrix, raw logs

4. **Check for anomalies**:
   - Balance flags (win rates outside 45–55%)
   - Matchup anomalies (beyond 35–65%)
   - High unparsed game counts

5. **Freeze policy**:
   - This is v1.0 — do NOT modify decks after results
   - Any changes happen in future versions
