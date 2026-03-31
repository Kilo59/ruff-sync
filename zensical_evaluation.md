# Zensical vs. MkDocs-Material: Evaluation for `ruff-sync`

> **Evaluated:** 2026-03-30 | **Source:** [zensical.org](https://zensical.org/)

---

## What is Zensical?

Zensical is a next-generation documentation platform **built by the creators of Material for MkDocs** (squidfunk/Martin Donath et al.). It bills itself as "adaptive systems for evolving ideas" and is designed to be a vertically integrated successor to the MkDocs + Material for MkDocs stack.

**Key identity points:**
- Built around a brand-new Rust runtime called **ZRX** — differential builds, automatic parallelization, and an integrated high-performance web server
- **Currently in alpha** — the team is actively working toward feature parity with Material for MkDocs
- **Open Source core** with a paid support/early-access subscription program called **Zensical Spark**
- Built by the same team that created Material for MkDocs, so it is a deliberate succession, not a fork by strangers

---

## Current `ruff-sync` Doc Setup

The existing documentation is a well-configured Material for MkDocs site:

| Config area | Details |
|---|---|
| **Theme** | `material` with amber/deep-purple palette, light/dark toggle |
| **Plugins** | `search`, `gen-files`, `literate-nav`, `mkdocstrings` |
| **Extensions** | `admonition`, `pymdownx.*` (superfences, highlight, emoji, tabbed, etc.), mermaid |
| **Nav** | ~10 hand-crafted pages + auto-generated API reference |
| **Hosting** | GitHub Pages (`Kilo59.github.io/ruff-sync`) |
| **Build tooling** | `invoke docs` task, Pygments pinned due to recent regression |

The plugins `gen-files`, `literate-nav`, and `mkdocstrings` are all Tier 1 or Tier 2 items on Zensical's backlog — **only `gen-files` is Tier 2 (lower priority)**.

---

## What Switching Would Involve

### Install & CLI

```bash
# Current
pip install mkdocs-material mkdocstrings[python] mkdocs-gen-files mkdocs-literate-nav
mkdocs serve / mkdocs build

# Zensical
pip install zensical
zensical serve / zensical build
```

Zensical natively reads `mkdocs.yml`, so the configuration file itself **does not need to change initially**. The command-line interface is a drop-in that understands the existing configuration format.

### Phase-by-phase migration

Zensical documents a **phased transition strategy**:

1. **Phase 1 (now):** Run `zensical build` against your existing `mkdocs.yml` — it maps plugins to equivalent Zensical modules. Most projects should build as-is.
2. **Phase 2:** As the module system matures, Zensical will introduce a native `zensical.toml` config format. Migration tooling will be provided.
3. **Phase 3:** Opt into new capabilities (Rust search engine, modular nav, component system, etc.) — these will live beyond what Material for MkDocs ever offered.

### Plugin compatibility for `ruff-sync`

| Plugin (current) | Tier | Status |
|---|---|---|
| `search` | Tier 1 | ✅ In backlog, being replaced by **Disco** (native Rust search engine) |
| `gen-files` | **Tier 2** | ⚠️ On backlog but lower priority than Tier 1 |
| `literate-nav` | Tier 1 | ✅ On backlog; eventually superseded by modular nav |
| `mkdocstrings` | Tier 1 | ✅ On backlog (Backlog #4) |

> [!WARNING]
> `gen-files` (used by `ruff-sync` to auto-generate the API reference pages via `docs/gen_ref_pages.py`) is Tier 2. This is the highest migration risk. If Zensical doesn't yet support it when you want to switch, the API reference page (`reference/`) would not build correctly.

### What would NOT require changes (by design)

- All markdown content in `docs/` — same Python Markdown dialect
- All existing pymdownx extensions (admonitions, code blocks, tabs, mermaid, etc.) — fully listed as supported
- `mkdocs.yml` configuration structure
- GitHub Pages deployment
- Template overrides (Jinja2 → MiniJinja, same template structure)
- Custom CSS/JS

### What would need testing

- `gen_ref_pages.py` script — depends on `mkdocs-gen-files` plugin compatibility
- `literate-nav` SUMMARY.md-driven navigation
- Pygments/syntax highlighting behavior (the pinned version issue may resurface differently)
- `mkdocstrings` API reference rendering (high priority backlog item but still in progress)

---

## Pros

### ✅ Same team and philosophy
Zensical is a direct evolution, not a replacement by strangers. The design decisions are made by the people who understand Material for MkDocs deeply. There is no risk of ideological drift in the design.

### ✅ Extreme backward compatibility focus
The explicit goal is that `zensical build` replaces `mkdocs build` with **zero changes** to `mkdocs.yml` or content. This is treated as a first-class commitment, not an afterthought.

### ✅ Rust runtime: dramatically better build performance (future)
Differential builds, automatic parallelization, and intelligent caching will be huge wins for large sites. For `ruff-sync` today the site is small, but this is compelling future-proofing.

### ✅ Modern design option (no breaking change)
A new cleaner design is available while keeping the classic Material look as default. You can opt in when ready.

### ✅ Consolidated ecosystem
Zensical plans to absorb the functionality of many common MkDocs plugins (literate-nav, mkdocstrings, gen-files, etc.) as native modules — removing the need to manage a constellation of separate plugin packages.

### ✅ Better search (Disco)
The new Disco search engine supports semantic vector search, faceting, offline use, and fuzzy matching — well beyond the current lunr-based MkDocs search.

### ✅ No Python ecosystem lock-in for extension
The future module API will support Rust and Python (via PyO3). This is more sustainable than the current tightly-coupled MkDocs plugin hooks.

### ✅ Built-in web server (Rust)
Replaces MkDocs' basic Python HTTP server with a high-performance Rust server with middleware support.

---

## Cons

### ❌ Currently in alpha
The roadmap explicitly says "Zensical is currently alpha software." This means instability, potential breaking changes between releases, and incomplete documentation. Not suitable for production use without Zensical Spark support.

### ❌ Key plugins not yet ready
`gen-files` (Tier 2) is essential for auto-generating the API reference pages. Until it — and `mkdocstrings` (Tier 1) — are production-ready in Zensical, switching would break the API docs. These are actively in progress but no ETAs are given.

### ❌ Paid support tier is expensive
Zensical Spark is not cheap for an open source project:

| Tier | Price | Details |
|---|---|---|
| Startup | **$249/month** | 2 seats, migration support, roadmap input |
| Professional | **$499/month** | + bi-weekly video calls, all workshops included |
| Partnership | **$999/month** | + private channel, 1:1 calls, optional NDA |

For a solo-maintainer or small OSS project, these costs are prohibitive. The core tool is free but there's no free support channel beyond GitHub issues.

### ❌ Immature ecosystem
The MkDocs plugin ecosystem is large and battle-tested. Zensical's module system API is deliberately not yet public — third-party modules can't be written yet. The existing community of ~hundreds of MkDocs plugins would not be directly usable.

### ❌ Roadmap without dates
The roadmap is transparent about direction but explicitly says "The items on this roadmap do not have a strict ordering or implied dates of completion." Feature parity could be 6 months or 2 years away.

### ❌ New config format coming
A new `zensical.toml` configuration format is planned. While conversion tooling will be provided, there is a future migration burden that doesn't exist with the current stack.

### ❌ Markdown dialect may change
Zensical currently uses Python Markdown (same as MkDocs), but is "exploring switching to CommonMark in the near future." While they promise automatic translation, this is a potential compatibility risk for edge cases in the existing docs.

---

## Comparison Summary

| Dimension | MkDocs-Material (current) | Zensical |
|---|---|---|
| **Maturity** | Battle-tested, stable | Alpha |
| **Build speed** | Moderate (Python) | Will be much faster (Rust, differential) |
| **Plugin ecosystem** | Large, community-maintained | Small, growing, not yet extensible externally |
| **Key plugins** | All working today | `gen-files`, `mkdocstrings` still in progress |
| **Search** | lunr-based (basic) | Disco (next-gen, Rust) |
| **Config** | `mkdocs.yml` | `mkdocs.yml` now → `zensical.toml` later |
| **Cost** | Free | Free core, $249–999/month for support |
| **Support** | GitHub Issues, community | GitHub + paid Spark tiers |
| **GitHub Pages deployment** | First-class | Should be identical (same static output) |
| **API docs (`mkdocstrings`)** | Working | Tier 1 backlog, in progress |

---

## Recommendation

> [!IMPORTANT]
> **Do not switch to Zensical yet, but bookmark it as a strong future migration target (likely 6–12 months from now).**

### Rationale

**The timing is wrong for ruff-sync today.** The two most critical plugins for this site — `mkdocstrings` (the API reference) and `gen-files` (the script that generates the reference page stubs) — are explicitly listed as in-progress backlog items. Until both are production-ready in Zensical, the switch would regress the API documentation section, which is currently working well.

**The trajectory is very compelling, however.** Zensical is not a risky startup replacement — it's the next phase of Material for MkDocs, built by the same team, with a deliberate compatibility-first strategy. The Rust runtime, Disco search, and modular navigation system will eventually make it substantially better than the current stack.

### Suggested action plan

1. **Now:** Track the Zensical backlog for [Backlog #4 (`mkdocstrings`)](https://github.com/zensical/backlog/issues/4) and [Backlog #8 (`gen-files`)](https://github.com/zensical/backlog/issues/8). Subscribe to the [Zensical newsletter](https://zensical.org/about/newsletter/) for progress updates.
2. **When both Tier 1/2 plugins are ready (est. 6–12 months):** Run `pip install zensical` alongside the existing setup and attempt a shadow build with `zensical build`. Compare the output.
3. **If shadow build succeeds:** Switch the CI `docs` job from `mkdocs build` to `zensical build`. Keep `mkdocs.yml` unchanged initially.
4. **Later:** Consider opting into the modern design and the new `zensical.toml` format once tooling is stable.

### For an OSS project like `ruff-sync`

Zensical Spark pricing ($249/month minimum) is not appropriate for an open-source CLI tool. The free tier (GitHub issues, public docs) is sufficient. Wait until the core product reaches feature parity before switching — you'll get the benefits without needing a paid tier.
