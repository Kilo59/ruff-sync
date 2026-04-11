# tapes/pull_basic.tape
# Demonstrates: Basic ruff-sync pull from an upstream repository.

Source tapes/_common.tape

Require ruff-sync

Output docs/assets/recordings/pull_basic.gif

# Show the current state of pyproject.toml
Type "cat pyproject.toml | head -20"
Enter
Sleep 1.5s

# Run ruff-sync against the upstream
Type "ruff-sync https://github.com/Kilo59/ruff-sync -v"
Enter
Sleep 4s

# Show what changed
Type "git diff pyproject.toml | head -30"
Enter
Sleep 3s

# Clean up
Hide
Type "git checkout pyproject.toml"
Enter
Sleep 500ms
Show

Sleep 1s
