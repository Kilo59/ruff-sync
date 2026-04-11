# tapes/validate_strict.tape
# Demonstrates: --validate and --strict flags.

Source tapes/_common.tape

Require ruff-sync

Output docs/assets/recordings/validate_strict.gif

# First show normal validation passing
Type "ruff-sync --validate -v"
Enter
Sleep 4s

Type ""
Enter
Sleep 500ms

# Now show strict mode
Type "ruff-sync --strict -v"
Enter
Sleep 4s

Sleep 2s
