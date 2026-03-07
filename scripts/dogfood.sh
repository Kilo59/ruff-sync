#!/usr/bin/env bash
set -euo pipefail

# Dogfooding script for ruff-sync
#
# This script "dogfoods" ruff-sync by syncing this project's own pyproject.toml
# with a complex upstream configuration (defaults to Pydantic).
#
# Usage:
#   ./scripts/dogfood.sh [upstream_url]
#
# Default upstream:
#   https://github.com/pydantic/pydantic/blob/main/pyproject.toml

DEFAULT_UPSTREAM="https://github.com/pydantic/pydantic/blob/main/pyproject.toml"
UPSTREAM=${1:-$DEFAULT_UPSTREAM}

echo "🐶 Dogfooding ruff-sync..."
echo "🔗 Upstream: $UPSTREAM"
echo "📂 Target:   ./pyproject.toml"
echo ""

# Ensure we are in the project root
cd "$(dirname "$0")/.."

# Check if we have uncommitted changes in pyproject.toml
if ! git diff --quiet pyproject.toml; then
    echo "⚠️  Warning: You have uncommitted changes in pyproject.toml."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborting."
        exit 1
    fi
fi

# Run the tool via poetry
poetry run python ruff_sync.py "$UPSTREAM"

echo ""
echo "✨ Dogfooding run complete!"
echo "--------------------------------------------------"
echo "Next steps:"
echo "1. Inspect the changes: git diff pyproject.toml"
echo "2. Discard when done:   git checkout pyproject.toml"
echo "--------------------------------------------------"
