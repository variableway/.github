# Org Profile Analysis: Applying tw93 Mechanism to variableway

## 1. tw93 Mechanism Analysis

tw93 uses a fully automated GitHub Actions + Python script pipeline to keep their GitHub profile README dynamically updated.

### Core Components

| File | Purpose |
|------|---------|
| `build_readme.py` | Python script that fetches data and updates README |
| `.github/workflows/build.yml` | GitHub Actions workflow that runs the script on schedule |
| `requirements.txt` | Python dependencies (requests, feedparser, PyGithub) |
| `README.md` | Profile README with comment markers for dynamic content |

### Data Sources

tw93's script fetches data from:

1. **GitHub API** (via PyGithub) — Releases, stars, forks, followers
2. **Blog RSS Feed** — `tw93.fun/en/feed.xml` — latest blog posts
3. **Weekly RSS Feed** — `weekly.tw93.fun/en/rss.xml` — newsletter posts

### Update Mechanism

The README uses **comment markers** as placeholders. The script replaces content between matching marker pairs:

```
<!-- recent_releases starts -->...<!-- recent_releases ends -->
<!-- blog starts -->...<!-- blog ends -->
<!-- github_stats starts -->...<!-- github_stats ends -->
```

The `replace_chunk()` function uses regex to find and replace content between these markers.

---

## 2. Flow Chart

```
+---------------------------+
|     Trigger Events        |
|  - Push to repo           |
|  - Manual dispatch        |
|  - Cron: every 6 hours    |
+------------+--------------+
             |
             v
+---------------------------+
|   GitHub Actions Workflow |
|   (build.yml)             |
+------------+--------------+
             |
             v
+---------------------------+
|  1. Checkout repository   |
|  2. Setup Python 3.8      |
|  3. Install dependencies  |
|     (pip install)         |
+------------+--------------+
             |
             v
+---------------------------+
|   Run build_readme.py     |
|   with GH_TOKEN env var   |
+------------+--------------+
             |
             +-----------------------------+
             |                             |
             v                             v
+------------------------+   +------------------------+
| fetch_github_stats()   |   | fetch_releases()       |
| - PyGithub API         |   | - PyGithub API         |
| - Get org repos        |   | - Get all org repos    |
| - Sum stars/forks      |   | - Filter out forks/    |
| - Get followers        |   |   private/prerelease   |
+------------------------+   | - Normalize titles     |
             |               | - Sort by date desc    |
             |               +------------------------+
             |                             |
             +--+--------------------------+
             |  |
             v  v
+---------------------------+
|   Read current README.md  |
+------------+--------------+
             |
             v
+---------------------------+
|  Replace content between  |
|  comment markers:         |
|                           |
|  <!-- github_stats -->    |
|  <!-- recent_releases --> |
|  <!-- blog -->            |
+------------+--------------+
             |
             v
+---------------------------+
|  Write updated README.md  |
+------------+--------------+
             |
             v
+---------------------------+
|  Git diff / Commit / Push |
|  (only if changed)        |
|  Author: github-actions   |
+---------------------------+
```

### Key Design Patterns

1. **Marker-based template** — Static content stays, dynamic parts are wrapped in markers
2. **Graceful degradation** — Fallback to cached values if API fails
3. **Deduplication** — Only keeps latest release per repo
4. **Text normalization** — Strips emoji, truncates long titles
5. **Conditional commit** — Only pushes when content actually changed (`|| exit 0`)

---

## 3. Plan for variableway Org Profile

### Current State

- Static README with manually maintained project list
- No automation, no workflows
- Content: org description + project table with stats
- Last updated manually: 2026-04-07

### What to Adapt from tw93

| tw93 Feature | Adaptation for variableway |
|---|---|
| Fetch releases from user repos | Fetch releases from **org repos** via `g.get_organization("variableway")` |
| Blog RSS feed | Not applicable (no org blog) — **skip** |
| Weekly RSS feed | Not applicable — **skip** |
| GitHub stats (followers, stars, forks) | Fetch org stats: total repos, total stars, total forks |
| Comment markers for dynamic sections | Use markers for: `project_list`, `org_stats` |
| Cron every 6 hours | Cron every 6 hours — **same** |

### Proposed Dynamic Sections

1. **`<!-- project_list -->`** — Auto-generated table of all org repos with name, description, stars, language
2. **`<!-- org_stats -->`** — Total repos, total stars, average stars, last updated timestamp
3. **`<!-- recent_releases -->`** — Latest releases across org repos (if any)

### Proposed README Template

```markdown
# variableway

This is Org for Projects created by Learning AI Agent.

- Spark-\*\*\* projects are personal daily work projects.
- innate-\*\*\* projects are products created by Learning AI Agent.

## Stats

<!-- org_stats starts -->
<!-- org_stats ends -->

## Project List

<!-- project_list starts -->
<!-- project_list ends -->

## Latest Releases

<!-- recent_releases starts -->
<!-- recent_releases ends -->
```

---

## 4. Task List

### Phase 1: Setup Script

- [ ] **Task 1.1**: Create `build_readme.py` in repo root (`.github/` level)
  - Adapt tw93's `fetch_releases()` to use `g.get_organization("variableway").get_repos()`
  - Create `fetch_org_stats()` to compute total repos, stars, forks
  - Create `fetch_project_list()` to generate markdown table of all repos
  - Use same `replace_chunk()` marker mechanism

- [ ] **Task 1.2**: Create `requirements.txt` with dependencies:
  - `PyGithub>=1.55`
  - `requests>=2.25.0`
  - (No `feedparser` needed — no RSS feeds)

### Phase 2: Update README Template

- [ ] **Task 2.1**: Update `profile/README.md` with comment markers for dynamic sections
- [ ] **Task 2.2**: Update root `README.md` to match or point to `profile/README.md`

### Phase 3: GitHub Actions Workflow

- [ ] **Task 3.1**: Create `.github/workflows/build.yml`
  - Same trigger: push, dispatch, cron `0 */6 * * *`
  - Python 3.8 setup
  - Run `build_readme.py`
  - Commit and push if changed

- [ ] **Task 3.2**: Add `GH_TOKEN` secret to repository secrets
  - Needs a Personal Access Token with `repo` scope
  - Or use the default `GITHUB_TOKEN` with appropriate permissions

### Phase 4: Cleanup

- [ ] **Task 4.1**: Remove duplicate root `README.md` content (keep only `profile/README.md` as the org profile source)
- [ ] **Task 4.2**: Test the workflow manually via `workflow_dispatch`

---

## 5. Key Differences from tw93

| Aspect | tw93 | variableway |
|--------|------|-------------|
| Account type | Personal user | Organization |
| API calls | `g.get_user()` | `g.get_organization("variableway")` |
| Blog/Weekly | Yes (RSS feeds) | No |
| Stats | followers, stars, forks | repos count, stars, forks |
| Profile location | `README.md` in user profile repo | `profile/README.md` in `.github` repo |
| Content focus | Releases + Blog | Project list + Stats + Releases |
