import json
import pathlib
import re
import os
from datetime import datetime, timezone

from github import Github, Auth

root = pathlib.Path(__file__).parent.resolve()
PROJECTS_CONFIG = root / "projects.json"

TOKEN = os.environ.get("GH_TOKEN", "")
ORG_NAME = "variableway"


def replace_chunk(content, marker, chunk, inline=False):
    r = re.compile(
        r"<!\-\- {} starts \-\->.*<!\-\- {} ends \-\->".format(marker, marker),
        re.DOTALL,
    )
    if not inline:
        chunk = "\n{}\n".format(chunk)
    chunk = "<!-- {} starts -->{}<!-- {} ends -->".format(marker, chunk, marker)
    return r.sub(chunk, content)


def load_tracked_projects():
    """Load tracked projects from projects.json."""
    if not PROJECTS_CONFIG.exists():
        print(f"Warning: {PROJECTS_CONFIG} not found, using empty project list")
        return []
    data = json.loads(PROJECTS_CONFIG.read_text(encoding="utf-8"))
    projects = data.get("projects", data if isinstance(data, list) else [])
    tracked = []
    for item in projects:
        if isinstance(item, str):
            repo = item
            display_name = item.split("/")[-1]
        else:
            repo = item["repo"]
            display_name = item.get("display_name", repo.split("/")[-1])
        tracked.append({"repo": repo, "display_name": display_name})
    return tracked


def fetch_latest_release(repo):
    """Return the latest non-prerelease release for a repo, or None."""
    try:
        for release in repo.get_releases():
            if release.prerelease or (release.tag_name or "").lower() == "nightly":
                continue
            title = (release.title or "").strip() or release.tag_name or "Release"
            return {
                "tag": release.tag_name or title,
                "title": title,
                "published_at": release.published_at.strftime("%Y-%m-%d"),
                "url": release.html_url,
            }
    except Exception as e:
        print(f"Error fetching releases for {repo.full_name}: {e}")
    return None


def fetch_tracked_projects(oauth_token, tracked):
    """Fetch GitHub metadata and latest release for configured projects."""
    if not tracked:
        return []

    try:
        auth = Auth.Token(oauth_token) if oauth_token else None
        g = Github(auth=auth)
        repos = []
        for item in tracked:
            repo_name = item["repo"]
            try:
                repo = g.get_repo(repo_name)
                release = fetch_latest_release(repo)
                repos.append(
                    {
                        "name": item["display_name"],
                        "url": repo.html_url,
                        "description": (repo.description or "").replace("|", "/"),
                        "stars": repo.stargazers_count,
                        "language": repo.language or "-",
                        "forks": repo.forks_count,
                        "latest_release": release["tag"] if release else "-",
                        "latest_release_url": release["url"] if release else repo.html_url,
                        "release_published_at": release["published_at"] if release else "",
                    }
                )
            except Exception as e:
                print(f"Error fetching repo {repo_name}: {e}")
        return repos
    except Exception as e:
        print(f"Error fetching tracked projects: {e}")
        return []


def fetch_org_repos(oauth_token):
    """Fetch all public non-fork repos for the organization."""
    try:
        auth = Auth.Token(oauth_token) if oauth_token else None
        g = Github(auth=auth)
        org = g.get_organization(ORG_NAME)
        repos = []
        for repo in org.get_repos(type="public"):
            if repo.fork:
                continue
            repos.append(
                {
                    "name": repo.name,
                    "url": repo.html_url,
                    "description": (repo.description or "").replace("|", "/"),
                    "stars": repo.stargazers_count,
                    "language": repo.language or "-",
                    "forks": repo.forks_count,
                }
            )
        return sorted(repos, key=lambda r: (-r["stars"], r["name"]))
    except Exception as e:
        print(f"Error fetching org repos: {e}")
        return []


def build_project_table(repos):
    """Generate markdown table from tracked repo list."""
    lines = [
        "| Name | Description | Latest Release | Stars | Language |",
        "|------|-------------|----------------|-------|----------|",
    ]
    for r in repos:
        release_cell = (
            f"[{r['latest_release']}]({r['latest_release_url']})"
            if r.get("latest_release") and r["latest_release"] != "-"
            else "-"
        )
        lines.append(
            "| [{name}]({url}) | {description} | {release} | ⭐ {stars} | {language} |".format(
                release=release_cell,
                **r,
            )
        )
    return "\n".join(lines)


def build_org_stats(repos):
    """Generate stats line."""
    total_repos = len(repos)
    total_stars = sum(r["stars"] for r in repos)
    avg_stars = round(total_stars / total_repos, 1) if total_repos else 0
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    return (
        "**Statistics**: {repos} featured repositories, {stars} total stars, {avg} average\n\n"
        "*Last updated: {now}*"
    ).format(repos=total_repos, stars=total_stars, avg=avg_stars, now=now)


def build_releases_md(repos):
    """Generate releases markdown from tracked projects."""
    releases = []
    for repo in repos:
        if not repo.get("latest_release") or repo["latest_release"] == "-":
            continue
        releases.append(
            {
                "repo": repo["name"],
                "title": repo["latest_release"],
                "url": repo["latest_release_url"],
                "published_at": repo.get("release_published_at", ""),
            }
        )
    releases.sort(key=lambda r: r["published_at"], reverse=True)
    if not releases:
        return "• No releases yet"
    lines = []
    for r in releases:
        lines.append("• [{repo} - {title}]({url}) - {published_at}".format(**r))
    return "<br>".join(lines)


def update_readme(path, repos):
    """Update a single README file with dynamic content."""
    contents = path.read_text(encoding="utf-8")

    rewritten = replace_chunk(contents, "project_list", build_project_table(repos))
    rewritten = replace_chunk(rewritten, "org_stats", build_org_stats(repos))
    rewritten = replace_chunk(rewritten, "recent_releases", build_releases_md(repos))

    path.write_text(rewritten, encoding="utf-8")
    print(f"Updated {path.relative_to(root)}")


if __name__ == "__main__":
    tracked = load_tracked_projects()
    repos = fetch_tracked_projects(TOKEN, tracked)

    if not repos:
        print("No tracked project data fetched, falling back to org repos without release info")
        repos = fetch_org_repos(TOKEN)
        for repo in repos:
            repo["latest_release"] = "-"
            repo["latest_release_url"] = repo["url"]
            repo["release_published_at"] = ""

    update_readme(root / "profile" / "README.md", repos)
