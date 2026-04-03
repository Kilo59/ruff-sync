# Reference: mike CLI commands

Detailed parameter and core command reference for `mike`.

## `deploy`

```bash
mike deploy [options] <version> [alias]...
```

Build the documentation for the specified version and commit it to the deployment branch.

- `<version>`: The version name to deploy (e.g., `1.0`, `v1.2.3`).
- `[alias]`: Optional aliases to point to this version (e.g., `latest`, `stable`).

**Common options:**
- `-p, --push`: Push the branch to the remote repository.
- `-b, --branch NAME`: Deployment branch (default: `gh-pages`).
- `-m, --message MESSAGE`: Custom commit message.
- `-u, --update-aliases`: Update existing aliases if they already point to a different version.
- `--alias-type {symlink,redirect,copy}`: Method for creating aliases.

---

## `alias`

```bash
mike alias [options] <version> <alias>...
```

Create or update aliases for a version without rebuilding the documentation.

---

## `set-default`

```bash
mike set-default [options] <version>
```

Set the default version for the documentation site's root redirect.

---

## `list`

```bash
mike list [options]
```

List all versions and aliases deployed to the deployment branch.

---

## `delete`

```bash
mike delete [options] <identifier>...
```

Delete one or more versions or aliases.

- `<identifier>`: Version or alias name.

**Options:**
- `--all`: Delete all versions/aliases.

---

## `serve`

```bash
mike serve [options]
```

Locally serve the documentation from the deployment branch. This is for testing the built versioned site.

- `-a, --addr ADDR`: Address to bind to (default: `localhost:8000`).
