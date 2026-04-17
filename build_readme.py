import pathlib
import re
import os
from datetime import datetime, timezone

from github import Github, Auth

root = pathlib.Path(__file__).parent.resolve()

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


def fetch_org_releases(oauth_token):
    """Fetch latest releases across all org repos."""
    try:
        auth = Auth.Token(oauth_token) if oauth_token else None
        g = Github(auth=auth)
        org = g.get_organization(ORG_NAME)
        releases = []
        for repo in org.get_repos(type="public"):
            if repo.fork:
                continue
            try:
                repo_releases = list(repo.get_releases())
                if not repo_releases:
                    continue
                for release in repo_releases[:10]:
                    if release.prerelease or (release.tag_name or "").lower() == "nightly":
                        continue
                    title = (release.title or "").strip() or release.tag_name or "Release"
                    releases.append(
                        {
                            "repo": repo.name,
                            "repo_url": repo.html_url,
                            "title": title,
                            "published_at": release.published_at.strftime("%Y-%m-%d"),
                            "url": release.html_url,
                        }
                    )
            except Exception as e:
                print(f"Error fetching releases for {repo.name}: {e}")
        releases.sort(key=lambda r: r["published_at"], reverse=True)
        # Keep only latest release per repo
        seen = set()
        unique = []
        for r in releases:
            if r["repo"] not in seen:
                seen.add(r["repo"])
                unique.append(r)
        return unique
    except Exception as e:
        print(f"Error fetching org releases: {e}")
        return []


def build_project_table(repos):
    """Generate markdown table from repo list."""
    lines = [
        "| Name | Description | Stars | Language |",
        "|------|-------------|-------|----------|",
    ]
    for r in repos:
        lines.append(
            "| [{name}]({url}) | {description} | ⭐ {stars} | {language} |".format(**r)
        )
    return "\n".join(lines)


def build_org_stats(repos):
    """Generate stats line."""
    total_repos = len(repos)
    total_stars = sum(r["stars"] for r in repos)
    avg_stars = round(total_stars / total_repos, 1) if total_repos else 0
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    return (
        "**Statistics**: {repos} repositories, {stars} total stars, {avg} average\n\n"
        "*Last updated: {now}*"
    ).format(repos=total_repos, stars=total_stars, avg=avg_stars, now=now)


def build_releases_md(releases):
    """Generate releases markdown."""
    if not releases:
        return "• No releases yet"
    lines = []
    for r in releases[:6]:
        lines.append("• [{repo} - {title}]({url}) - {published_at}".format(**r))
    return "<br>".join(lines)


if __name__ == "__main__":
    readme_path = root / "profile" / "README.md"
    readme_contents = readme_path.open().read()

    repos = fetch_org_repos(TOKEN)
    releases = fetch_org_releases(TOKEN)

    # Update project list
    project_table = build_project_table(repos)
    rewritten = replace_chunk(readme_contents, "project_list", project_table)

    # Update org stats
    stats_text = build_org_stats(repos)
    rewritten = replace_chunk(rewritten, "org_stats", stats_text)

    # Update recent releases
    releases_md = build_releases_md(releases)
    rewritten = replace_chunk(rewritten, "recent_releases", releases_md)

    readme_path.open("w").write(rewritten)
    print("README updated successfully.")
