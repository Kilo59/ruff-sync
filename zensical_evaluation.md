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

The plugins `literate-nav` and `mkdocstrings` are Tier 1 items on Zensical's backlog. `gen-files` is Tier 2 but **not relevant** — `ruff-sync` is a CLI tool that doesn't benefit from auto-generated API reference pages.

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
| `gen-files` | Tier 2 | ➡️ N/A — not needed (no API autodocs for this CLI tool) |
| `literate-nav` | Tier 1 | ✅ On backlog; eventually superseded by modular nav |
| `mkdocstrings` | Tier 1 | ✅ On backlog (Backlog #4) — low value for CLI docs anyway |

> [!NOTE]
> `ruff-sync` is a CLI tool — the auto-generated API reference (`gen-files` + `mkdocstrings`) is low value and could be removed entirely to simplify the stack. Neither is a migration blocker.

### What would NOT require changes (by design)

- All markdown content in `docs/` — same Python Markdown dialect
- All existing pymdownx extensions (admonitions, code blocks, tabs, mermaid, etc.) — fully listed as supported
- `mkdocs.yml` configuration structure
- GitHub Pages deployment
- Template overrides (Jinja2 → MiniJinja, same template structure)
- Custom CSS/JS

### What would need testing

- `literate-nav` SUMMARY.md-driven navigation
- Pygments/syntax highlighting behavior (the pinned version issue may resurface differently)
- The `tasks.py` `docs` invoke task (would swap `mkdocs` → `zensical`)

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
`literate-nav` (Tier 1) is still in progress. Until it lands in Zensical, the SUMMARY.md-driven navigation would need to be manually inlined into `mkdocs.yml` — a one-time low-effort change, but still a required step.

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
| **Key plugins** | All working today | `literate-nav` still in progress |
| **Search** | lunr-based (basic) | Disco (next-gen, Rust) |
| **Config** | `mkdocs.yml` | `mkdocs.yml` now → `zensical.toml` later |
| **Cost** | Free | Free core, $249–999/month for support |
| **Support** | GitHub Issues, community | GitHub + paid Spark tiers |
| **GitHub Pages deployment** | First-class | Should be identical (same static output) |
| **API docs (`mkdocstrings`)** | Working (low value for CLI) | Tier 1 backlog, in progress |

---

## Recommendation

> [!IMPORTANT]
> **Do not switch to Zensical yet, but it's a viable migration target within ~3–6 months — sooner than initially estimated.**

### Revised rationale

**`gen-files` is irrelevant** — `ruff-sync` is a CLI tool and doesn't need auto-generated API reference pages. The existing `gen_ref_pages.py` + `mkdocstrings` setup could simply be dropped or replaced with a hand-authored API summary page, which is arguably better for a user-facing CLI tool anyway.

The **actual migration risk is now just `literate-nav`** (Tier 1, actively in progress). The current docs site uses a `SUMMARY.md` to drive navigation. If Zensical doesn't support this when you try a shadow build, you'd need to inline the nav into `mkdocs.yml` — a one-time, low-effort change.

**The trajectory is very compelling.** Zensical is not a risky startup replacement — it's the next phase of Material for MkDocs, built by the same team, with a deliberate compatibility-first strategy. The Rust runtime, Disco search, and modular navigation system will eventually make it substantially better than the current stack.

### Suggested action plan

1. **Now:** Track the Zensical backlog for [Backlog #13 (`literate-nav`)](https://github.com/zensical/backlog/issues/13). Subscribe to the [Zensical newsletter](https://zensical.org/about/newsletter/) for progress updates.
2. **Simplify the current stack:** Drop `gen-files` + `mkdocstrings` and replace the auto-generated API reference with a hand-authored page. This removes a maintenance burden and makes a future Zensical migration trivially simple.
3. **When `literate-nav` lands (est. 3–6 months):** Run `pip install zensical && zensical build` as a shadow build. Compare the output.
4. **If shadow build succeeds:** Switch the CI `docs` job from `mkdocs build` to `zensical build`. Keep `mkdocs.yml` unchanged initially.
5. **Later:** Consider opting into the modern design and the new `zensical.toml` format once tooling is stable.

### For an OSS project like `ruff-sync`

Zensical Spark pricing ($249/month minimum) is not appropriate for an open-source CLI tool. The free tier (GitHub issues, public docs) is sufficient. Wait until the core product reaches feature parity before switching — you'll get the benefits without needing a paid tier.

---

## MkDocs Catalog Plugins Worth Considering

Scanned [mkdocs/catalog](https://github.com/mkdocs/catalog) for plugins that are:
- Not already in use
- Relevant to a CLI tool docs site (not API docs, notebooks, or enterprise-only)
- Well-maintained and compatible with Material for MkDocs
- On or planned for Zensical's backlog (low Zensical switching risk)

### 🟢 Strongly Recommended

#### [`mkdocs-git-revision-date-localized`](https://github.com/timvink/mkdocs-git-revision-date-localized-plugin)

Adds a "last updated" date (and optionally git author info) to the bottom of every page, pulled from git history. This is a **Tier 2 item on Zensical's backlog** (Backlog #18).

```yaml
plugins:
  - git-revision-date-localized:
      enable_creation_date: true
      type: timeago  # e.g. "3 weeks ago"
```

**Why:** The docs cover actively developing features. Showing "Updated 2 days ago" builds reader trust and makes staleness immediately visible. Very low maintenance — zero config needed after the initial setup. Widely supported; used by dozens of major OSS projects.

**Zensical impact:** On the Tier 2 backlog — not a blocker. If you switch before it lands, you simply remove this plugin.

---

#### [`mkdocs-redirects`](https://github.com/mkdocs/mkdocs-redirects)

Manages URL redirects when pages are moved or renamed, preventing broken links.

```yaml
plugins:
  - redirects:
      redirect_maps:
        'old-page.md': 'new-page.md'
```

**Why:** As the docs evolve (e.g., if CI integration or URL resolution pages get reorganized), redirects prevent dead links in the wild — especially important because external sites, README snippets, and pre-commit hooks may link directly to doc pages. This is a **Tier 1 item on Zensical's backlog** (Backlog #23).

**Zensical impact:** Tier 1 — will be supported.

---

### 🟡 Worth Considering

#### [`mkdocs-minify-plugin`](https://github.com/byrnereese/mkdocs-minify-plugin)

Minifies HTML, CSS, and JS output for faster page loads.

```yaml
plugins:
  - minify:
      minify_html: true
```

**Why:** Free performance win on GitHub Pages with zero ongoing maintenance. This is a **Tier 1 item on Zensical's backlog** (Backlog #15). Zensical's Rust runtime will eventually make this obsolete (it does optimization natively), so it's only a temporary addition.

**Zensical impact:** Tier 1 — will be replaced by native optimization.

---

#### [`mkdocs-llmstxt`](https://github.com/pawamoy/mkdocs-llmstxt)

Generates an `/llms.txt` file at build time — a standardized machine-readable summary of the site's content for LLM consumption (see [llmstxt.org](https://llmstxt.org/)).

```yaml
plugins:
  - llmstxt:
      full_output: true  # also emit /llms-full.txt with all page content
```

**Why:** `ruff-sync` already includes an "Agent Skill" feature in its docs. Making the full doc content available via `/llms.txt` is a natural complement — agents and LLMs can directly consume the docs without scraping. This is a new addition to the catalog (by pawamoy, who also maintains `mkdocstrings`) and is **not yet on Zensical's backlog**, so it's a slight risk.

**Zensical impact:** Not yet in the backlog. If you switch to Zensical before it's supported, you'd need to drop or replace this — low stakes since it's a nice-to-have.

---

### 🔴 Not Recommended (for this project)

| Plugin | Reason to skip |
|---|---|
| `mkdocs-htmlproofer` | Validates all URLs at build time — catches broken links but dramatically slows the build. The existing `pymdownx.snippets: check_paths: true` already catches internal broken references. |
| `git-authors` | Shows per-page git author list — overkill for a single-maintainer OSS project. |
| `blog` (Material built-in) | Not relevant; this is not a blog. |
| `mkdocs-coverage` | Shows test coverage inline in docs — interesting but adds complexity; coverage is already tracked with Codecov. |
| `social` (Material built-in) | Auto-generates social card images per page. Nice but needs Cairo/Pillow system dependencies and adds CI complexity. |

### Effect on the Zensical evaluation

Adopting `git-revision-date-localized` and `mkdocs-redirects` **slightly increases** the Zensical switching cost in the short term — both are on the backlog but not yet released as Zensical modules. However, both are **Tier 1 or Tier 2** items, and `git-revision-date-localized` could simply be disabled during a shadow build.

`mkdocs-llmstxt` is the only one not on Zensical's backlog yet, and it's optional — easy to drop before a Zensical migration.
