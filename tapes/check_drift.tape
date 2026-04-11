# tapes/check_drift.tape
# Demonstrates: Catching configuration drift with `ruff-sync check`.

Source tapes/_common.tape

Require ruff-sync

Output docs/assets/recordings/check_drift.gif

# Silently introduce drift so the check fails
Hide
Type "cp pyproject.toml pyproject.toml.bak"
Enter
Sleep 300ms
# Remove a rule to simulate drift
Type 'python3 -c "import pathlib; p = pathlib.Path(\"pyproject.toml\"); p.write_text(p.read_text().replace(\"    \\\"PERF\\\", # perflint - performance related rules\\n\", \"\"))"'
Enter
Sleep 500ms
Show

# Run the check command
Type "ruff-sync check --semantic -v"
Enter
Sleep 4s

# Show the exit code
Type 'echo "Exit code: $?"'
Enter
Sleep 2s

# Restore the original file (hidden)
Hide
Type "mv pyproject.toml.bak pyproject.toml"
Enter
Sleep 300ms
Show

Sleep 1s
