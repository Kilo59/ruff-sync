# tapes/help_overview.tape
# Demonstrates: CLI help output overview.

Source tapes/_common.tape

Require ruff-sync

Output docs/assets/recordings/help_overview.gif

Set Height 700

# Main help
Type "ruff-sync --help"
Enter
Sleep 3s

# Pull help
Type "ruff-sync pull --help"
Enter
Sleep 3s

# Check help
Type "ruff-sync check --help"
Enter
Sleep 3s

Sleep 1s
