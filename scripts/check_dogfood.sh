#!/usr/bin/env bash
set -euo pipefail

# Dogfooding script for "check" command of ruff-sync
#
# This script "dogfoods" ruff-sync by checking if this project's own pyproject.toml
# is in sync with the upstream repository.
#
# Usage:
#   ./scripts/dogfood_check.sh [upstream_url]
#
# Default upstream:
#   https://github.com/Kilo59/ruff-sync

DEFAULT_UPSTREAM="https://github.com/Kilo59/ruff-sync"
UPSTREAM=${1:-$DEFAULT_UPSTREAM}

echo "🐶 Dogfooding ruff-sync check..."
echo "🔗 Comparing with upstream: $UPSTREAM"
echo "📂 Target:   ./pyproject.toml"
echo ""

# Ensure we are in the project root
cd "$(dirname "$0")/.."

# Check if we have uncommitted changes in pyproject.toml
if ! git diff --quiet pyproject.toml; then
    echo "⚠️  Note: You have uncommitted changes in pyproject.toml. These will be included in the check."
    echo ""
fi

# Run the check command via uv
# This will return 0 if in sync, 1 if out of sync
set +e
uv run python ruff_sync.py check "$UPSTREAM" --semantic -v
EXIT_CODE=$?
set -e

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Dogfooding check: Ruff configuration is in sync."
else
    echo "❌ Dogfooding check: Ruff configuration is out of sync."
fi

echo "--------------------------------------------------"
echo "✨ Dogfooding check complete!"
echo "--------------------------------------------------"
