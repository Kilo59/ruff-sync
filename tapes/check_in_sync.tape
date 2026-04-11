# tapes/check_in_sync.tape
# Demonstrates: Happy path — config is already in sync.

Source tapes/_common.tape

Require ruff-sync

Output docs/assets/recordings/check_in_sync.gif

# Run the check — should pass since we're dogfooding our own config
Type "ruff-sync check --semantic -v"
Enter
Sleep 4s

# Confirm exit code
Type "echo \"Exit code: $?\""
Enter
Sleep 2s

Sleep 1s
