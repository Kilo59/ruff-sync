#!/usr/bin/env bash
set -euo pipefail

# Dogfooding script for ruff-sync using a git URL
#
# This script "dogfoods" ruff-sync by syncing this project's own pyproject.toml
# with a complex upstream configuration (defaults to Pydantic) using a giturl.
#
# Usage:
#   ./scripts/gitclone_dogfood.sh [upstream_url]
#
# Default upstream:
#   git@github.com:pydantic/pydantic.git

DEFAULT_UPSTREAM="git@github.com:pydantic/pydantic.git"
UPSTREAM=${1:-$DEFAULT_UPSTREAM}

echo "🐶 Dogfooding ruff-sync via git clone..."
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

# Run the tool via uv
uv run python ruff_sync.py "$UPSTREAM" -v

echo ""
echo "✨ Dogfooding run complete!"
echo "--------------------------------------------------"
echo "Next steps:"
echo "1. Inspect the changes: git diff pyproject.toml"
echo "2. Discard when done:   git checkout pyproject.toml"
echo "--------------------------------------------------"
