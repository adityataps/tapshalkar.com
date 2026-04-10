import pytest
import respx
import httpx
from sources.github import fetch_github, GitHubData


REPOS_RESPONSE = [
    {
        "name": "cool-project",
        "description": "A cool ML project",
        "language": "Python",
        "stargazers_count": 12,
        "html_url": "https://github.com/adityataps/cool-project",
        "topics": ["machine-learning", "python"],
    }
]

LANGUAGES_RESPONSE = {"Python": 8000, "TypeScript": 2000}


@pytest.mark.anyio
async def test_fetch_github_returns_repos():
    with respx.mock:
        respx.get("https://api.github.com/users/adityataps/repos").mock(
            return_value=httpx.Response(200, json=REPOS_RESPONSE)
        )
        respx.get("https://api.github.com/repos/adityataps/cool-project/languages").mock(
            return_value=httpx.Response(200, json=LANGUAGES_RESPONSE)
        )

        data = await fetch_github(username="adityataps", token="test-token")

    assert isinstance(data, GitHubData)
    assert len(data.repos) == 1
    assert data.repos[0].name == "cool-project"
    assert "Python" in data.repos[0].languages
