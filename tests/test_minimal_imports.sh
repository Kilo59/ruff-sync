#!/usr/bin/env bash
set -euo pipefail

# This script verifies that ruff-sync works correctly without optional dependencies.
# It is intended to be run in a clean environment where only base dependencies are installed.

echo "🔍 Verifying absence of optional dependencies..."
if pip show textual > /dev/null 2>&1; then
    echo "❌ Error: 'textual' is installed, but it should be absent for this test."
    exit 1
fi
echo "✅ Optional dependencies are absent."

echo "🚀 Testing 'ruff-sync --help'..."
ruff-sync --version
ruff-sync --help > /dev/null
echo "✅ 'ruff-sync --help' passed."

echo "🚀 Testing 'ruff-sync pull --help'..."
ruff-sync pull --help > /dev/null
echo "✅ 'ruff-sync pull --help' passed."

echo "🚀 Testing 'ruff-sync inspect --help'..."
ruff-sync inspect --help > /dev/null
echo "✅ 'ruff-sync inspect --help' passed."

echo "🚀 Testing 'ruff-inspect --help'..."
ruff-inspect --help > /dev/null
echo "✅ 'ruff-inspect --help' passed."

echo "🚀 Testing 'ruff-sync check' (dogfooding)..."
# Use the current project's repo for a real-world check that should pass.
ruff-sync check https://github.com/Kilo59/ruff-sync
echo "✅ 'ruff-sync check' passed."

echo "🚀 Testing 'ruff-sync inspect' graceful failure..."
# Capture output and check for the expected error message.
if ruff-sync inspect 2> inspect_error.log; then
    echo "❌ Error: 'ruff-sync inspect' should have failed without 'textual'."
    exit 1
fi

ERROR_MSG=$(cat inspect_error.log)
echo "Captured error: $ERROR_MSG"

if [[ "$ERROR_MSG" == *"textual"* ]] && [[ "$ERROR_MSG" == *"ruff-sync[tui]"* ]]; then
    echo "✅ 'ruff-sync inspect' failed gracefully with correct message."
else
    echo "❌ Error: 'ruff-sync inspect' failed with unexpected message."
    exit 1
fi

echo "✨ All optional dependency validation tests passed!"
rm inspect_error.log
