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
Type `python3 -c "
t = open('pyproject.toml').read()
t = t.replace('\"PERF\",\n', '')
open('pyproject.toml', 'w').write(t)
"`
Enter
Sleep 500ms
Show

# Run the check command
Type "ruff-sync check --semantic -v"
Enter
Sleep 4s

# Show the exit code
Type "echo \"Exit code: $?\""
Enter
Sleep 2s

# Restore the original file (hidden)
Hide
Type "mv pyproject.toml.bak pyproject.toml"
Enter
Sleep 300ms
Show

Sleep 1s
