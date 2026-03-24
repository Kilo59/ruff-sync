# URL Resolution & Discovery

`ruff-sync` is designed to be flexible with the URLs you provide. Whether you point to a GitHub repository, a specific file on GitLab, or use an SSH link, the tool handles the complexity of locating and fetching the target configuration.

---

## 🌐 Browser URL Conversion

For public repositories on GitHub and GitLab, you can copy the URL directly from your browser. `ruff-sync` automatically converts these into "raw" content URLs.

### GitHub
| Input Type | Browser URL Example | Resolved Raw URL |
| :--- | :--- | :--- |
| **Repository Root** | `https://github.com/<org>/<repo>` | `.../raw.githubusercontent.com/<org>/<repo>/main/pyproject.toml` |
| **Specific Branch** | `https://github.com/<org>/<repo>/tree/<branch>` | `.../raw.githubusercontent.com/<org>/<repo>/<branch>/pyproject.toml` |
| **Specific File** | `https://github.com/<org>/<repo>/blob/<branch>/ruff.toml` | `.../raw.githubusercontent.com/<org>/<repo>/<branch>/ruff.toml` |

### GitLab
| Input Type | Browser URL Example | Resolved Raw URL |
| :--- | :--- | :--- |
| **Repository Root** | `https://gitlab.com/<org>/<repo>` | `.../gitlab.com/<org>/<repo>/-/raw/main/pyproject.toml` |
| **Specific File** | `https://gitlab.com/<org>/<repo>/-/blob/<branch>/ruff.toml` | `.../gitlab.com/<org>/<repo>/-/raw/<branch>/ruff.toml` |

---

## 📂 Configuration Discovery

When you target a directory (either locally or via a repo-root URL), `ruff-sync` searches for a configuration file in the following order:

1.  `ruff.toml`
2.  `.ruff.toml`
3.  `pyproject.toml` (extracting the `[tool.ruff]` section)

If you target a URL that doesn't end in `.toml`, the tool assumes it's a directory and performs this search automatically.

---

## 🛠️ Git & SSH URLs

For private repositories or environments where HTTP access is restricted, you can use Git/SSH URLs.

```bash
ruff-sync git@github.com:<my-org>/<standards>.git
```

### Efficient Cloning
When using Git URLs, `ruff-sync` performs an optimized "partial clone" to minimize network traffic:
- `--depth 1`: Fetches only the latest commit.
- `--filter=blob:none`: Avoids downloading any file contents initially.
- `--no-checkout`: Does not populate the working directory.

The tool then uses `git restore` (or `git checkout` as a fallback) to pull **only** the configuration file it needs.

---

## 💡 Troubleshooting & Permissions

### Private Repositories via HTTP
Conversion to `raw.githubusercontent.com` works beautifully for public repositories. However, if your repository is private, these HTTP requests will fail with a `404` or `401` unless you have configured authentication for `httpx`.

**Recommendation**: Use **SSH URLs** (`git@github.com:...`) for private repositories. `ruff-sync` will detect the HTTP failure and suggest the equivalent SSH command if it recognizes the host.

### Custom Branches
If your upstream repository uses a default branch other than `main` (e.g., `master` or `develop`), you should specify it via the `--branch` flag or in your configuration:

```toml
[tool.ruff-sync]
upstream = "https://github.com/<my-org>/<standards>"
branch = "develop"
```
