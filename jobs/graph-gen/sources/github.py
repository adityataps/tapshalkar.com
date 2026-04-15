import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
import httpx


@dataclass
class RepoData:
    name: str
    description: str
    languages: dict[str, int]
    stars: int
    url: str
    topics: list[str]
    last_pushed_at: str = ""
    commits_last_30d: int = 0


@dataclass
class GitHubData:
    repos: list[RepoData]
    top_languages: list[str]     # sorted by total bytes across all repos


async def _fetch_repo_languages(client: httpx.AsyncClient, username: str, repo_name: str) -> dict[str, int]:
    r = await client.get(f"https://api.github.com/repos/{username}/{repo_name}/languages")
    r.raise_for_status()
    return r.json()


async def _fetch_commit_stats(client: httpx.AsyncClient, username: str) -> dict[str, int]:
    """One GraphQL call → per-repo commit counts for the last 30 days."""
    to_dt = datetime.now(timezone.utc)
    from_dt = to_dt - timedelta(days=30)
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          commitContributionsByRepository(maxRepositories: 30) {
            contributions { totalCount }
            repository { name }
          }
        }
      }
    }
    """
    r = await client.post(
        "https://api.github.com/graphql",
        json={
            "query": query,
            "variables": {
                "login": username,
                "from": from_dt.isoformat(),
                "to": to_dt.isoformat(),
            },
        },
    )
    r.raise_for_status()
    contribs = (
        r.json()
        .get("data", {})
        .get("user", {})
        .get("contributionsCollection", {})
        .get("commitContributionsByRepository", [])
    )
    return {c["repository"]["name"]: c["contributions"]["totalCount"] for c in contribs}


async def fetch_github(username: str, token: str) -> GitHubData:
    headers = {"Authorization": f"Bearer {token}", "X-GitHub-Api-Version": "2022-11-28"}

    async with httpx.AsyncClient(headers=headers, timeout=30) as client:
        r = await client.get(
            f"https://api.github.com/users/{username}/repos",
            params={"sort": "updated", "per_page": 30, "type": "public"},
        )
        r.raise_for_status()
        raw_repos = r.json()

        language_tasks = [
            _fetch_repo_languages(client, username, repo["name"])
            for repo in raw_repos
        ]
        all_languages, commit_stats = await asyncio.gather(
            asyncio.gather(*language_tasks),
            _fetch_commit_stats(client, username),
        )

    repos = [
        RepoData(
            name=raw["name"],
            description=raw.get("description") or "",
            languages=langs,
            stars=raw.get("stargazers_count", 0),
            url=raw.get("html_url", ""),
            topics=raw.get("topics", []),
            last_pushed_at=raw.get("pushed_at", ""),
            commits_last_30d=commit_stats.get(raw["name"], 0),
        )
        for raw, langs in zip(raw_repos, all_languages)
    ]

    lang_totals: dict[str, int] = {}
    for repo in repos:
        for lang, bytes_count in repo.languages.items():
            lang_totals[lang] = lang_totals.get(lang, 0) + bytes_count

    top_languages = sorted(lang_totals, key=lambda l: lang_totals[l], reverse=True)[:10]

    return GitHubData(repos=repos, top_languages=top_languages)
