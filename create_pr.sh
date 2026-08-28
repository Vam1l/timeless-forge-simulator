#!/bin/bash
# Script to create the pull request for the Peasant+ 10-deck baseline
# Usage: bash create_pr.sh

GH_REPO="Vam1l/timeless-forge-simulator"
HEAD_BRANCH="ai-balance/peasant-10deck-roundrobin"
BASE_BRANCH="main"

echo "Creating pull request..."
echo "From: $HEAD_BRANCH"
echo "Into: $BASE_BRANCH"
echo ""

gh pr create \
  --repo "$GH_REPO" \
  --head "$HEAD_BRANCH" \
  --base "$BASE_BRANCH" \
  --title "Add Peasant+ 10-deck Forge round-robin baseline" \
  --body-file "PR_DESCRIPTION.md"

echo ""
echo "Pull request created! Next steps:"
echo "1. Navigate to the PR on GitHub"
echo "2. Monitor the 'peasant-10deck-baseline' workflow"
echo "3. Review results after workflow completes"
