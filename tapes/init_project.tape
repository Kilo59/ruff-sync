# tapes/init_project.tape
# Demonstrates: Bootstrapping a new project with --init.

Source tapes/_common.tape

Require ruff-sync

Output docs/assets/recordings/init_project.gif

# Create and enter a fresh directory
Type "mkdir /tmp/my-new-project && cd /tmp/my-new-project"
Enter
Sleep 500ms

Type "ls -la"
Enter
Sleep 1s

# Initialize from an upstream
Type "ruff-sync https://github.com/Kilo59/ruff-sync --init -v"
Enter
Sleep 4s

# Show the generated file
Type "cat pyproject.toml"
Enter
Sleep 3s

# Clean up (hidden)
Hide
Type "cd - && rm -rf /tmp/my-new-project"
Enter
Sleep 300ms
Show

Sleep 1s
