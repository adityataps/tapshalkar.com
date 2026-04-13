import asyncio
import json
import httpx
import anthropic
from models import GraphOutput, Node, Edge, TraktItem, HealthSummary
from sources.github import GitHubData
from sources.spotify import SpotifyData
from sources.steam import SteamData
from sources.trakt import TraktData

MAX_ITERATIONS = 10

README_TOOL = {
    "name": "fetch_github_readme",
    "description": "Fetch the README for a GitHub repository to get a richer description for a project node.",
    "input_schema": {
        "type": "object",
        "properties": {
            "owner": {"type": "string", "description": "GitHub username or org"},
            "repo":  {"type": "string", "description": "Repository name"},
        },
        "required": ["owner", "repo"],
    },
}

GRAPH_TOOL = {
    "name": "emit_knowledge_graph",
    "description": "Emit the final typed knowledge graph. Call this when you have gathered enough context.",
    "input_schema": {
        "type": "object",
        "properties": {
            "nodes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id":          {"type": "string"},
                        "type":        {"type": "string", "enum": ["skill", "project", "experience", "education", "interest", "health"]},
                        "label":       {"type": "string"},
                        "description": {"type": "string"},
                        "metadata": {
                            "type": "object",
                            "description": "For interest nodes set subtype to one of: artist, album, track, podcast, audiobook, movie, show, genre",
                        },
                    },
                    "required": ["id", "type", "label"],
                },
            },
            "edges": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "target": {"type": "string"},
                        "type":   {"type": "string", "enum": ["used_in", "worked_on", "studied_at", "interested_in", "relates_to"]},
                        "weight": {"type": "number"},
                    },
                    "required": ["source", "target", "type"],
                },
            },
        },
        "required": ["nodes", "edges"],
    },
}

SYSTEM_PROMPT = """You are a knowledge graph synthesizer for a software engineer's portfolio.

Given data from GitHub, Spotify, Steam, Trakt, and Apple Health, emit a structured knowledge graph
capturing their skills, projects, experience, education, and interests as typed nodes with weighted edges.

You may call fetch_github_readme for up to 3 repositories to get richer project descriptions.
Once you have enough context, call emit_knowledge_graph with the final graph.

IMPORTANT: The edges array must NOT be empty. Every node must connect to at least one other node.

Node rules:
- Node IDs: stable snake_case prefixed by type (e.g. skill-python, project-ml-tool)
- For interest nodes use: interest-{subtype}-{slugified-name} (e.g. interest-artist-kendrick-lamar, interest-genre-hip-hop)
- Infer skill nodes from GitHub languages and topics
- All cultural/media content uses type "interest" with metadata.subtype set to one of:
  artist, album, track, podcast, audiobook, movie, show, genre
- Emit up to 5 artist nodes, 3 album nodes, 3 podcast nodes, 2 audiobook nodes, 3 genre nodes
- Add movie/show nodes (as interest nodes with subtype movie/show) for Trakt history
- Add a health node if Apple Health data is present
- Always set metadata.url on every interest node where a URL is available
- Always set metadata.subtype on every interest node
- Prefer fewer accurate nodes over many speculative ones

Edge rules (apply all that are relevant — edges array must not be empty):
- skill → project: used_in edges for each language/skill used in a project
- album → artist: relates_to edge (every album node must connect to its artist node)
- genre → artist: relates_to edge (every artist node must connect to at least one genre node)
- artist/album/genre → project: relates_to edge when music taste is relevant to a project
- podcast/audiobook → skill: relates_to edge when the topic overlaps a skill (e.g. an ML podcast → skill-python)
- interest → interest: relates_to edges between related interests (e.g. genre → artist, artist → album)
- Edge weight 0.0–1.0 based on relationship strength
"""


NODE_FIELDS = {"id", "type", "label", "description", "metadata"}
EDGE_FIELDS = {"source", "target", "type", "weight"}


async def _fetch_readme(owner: str, repo: str) -> str:
    """Fetch README content via GitHub API."""
    url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, headers={"Accept": "application/vnd.github.raw"})
        if r.status_code == 200:
            return r.text[:2000]  # cap at 2000 chars
        return ""


async def synthesize_graph(
    github: GitHubData,
    spotify: SpotifyData,
    steam: SteamData,
    trakt: TraktData,
    health: HealthSummary,
    api_key: str,
) -> GraphOutput:
    context = {
        "github": {
            "top_languages": github.top_languages,
            "repos": [
                {
                    "name": r.name,
                    "description": r.description,
                    "topics": r.topics,
                    "stars": r.stars,
                    "url": r.url,
                }
                for r in github.repos[:20]
            ],
        },
        "spotify": {
            "top_artists": [{"name": a.name, "url": a.url, "genres": a.genres} for a in spotify.top_artists],
            "top_genres": spotify.top_genres,
            "top_tracks": [{"name": t.name, "artist": t.artist, "url": t.url} for t in spotify.top_tracks[:5]],
            "saved_shows": [{"name": s.name, "publisher": s.publisher, "url": s.url, "description": s.description} for s in spotify.saved_shows],
            "saved_audiobooks": [{"name": a.name, "author": a.author, "url": a.url} for a in spotify.saved_audiobooks],
            "recent_albums": [{"name": a.name, "artist": a.artist, "url": a.url} for a in spotify.recent_albums],
        },
        "steam": {
            "most_played": [{"name": g.name, "hours": g.hours_played, "url": g.store_url} for g in steam.most_played[:5]],
            "recently_played": [g.name for g in steam.recently_played],
        },
        "trakt": {
            "history": [{"title": i.title, "type": i.media_type, "year": i.year, "url": i.trakt_url, "genres": i.genres} for i in trakt.history[:20]],
            "watchlist": [{"title": i.title, "type": i.media_type} for i in trakt.watchlist[:10]],
            "watching": {"title": trakt.watching.title, "type": trakt.watching.media_type} if trakt.watching else None,
        },
        "health": {
            "avg_daily_steps": health.avg_daily_steps,
            "avg_active_energy_kcal": health.avg_active_energy_kcal,
            "avg_sleep_hours": health.avg_sleep_hours,
            "last_workout": f"{health.last_workout_type} {health.last_workout_duration_min}min" if health.last_workout_type else None,
        },
    }

    client = anthropic.Anthropic(api_key=api_key)
    messages = [{"role": "user", "content": f"Here is my data:\n\n{json.dumps(context, indent=2)}"}]

    for _ in range(MAX_ITERATIONS):
        message = await asyncio.to_thread(
            client.messages.create,
            model="claude-opus-4-6",
            max_tokens=16384,
            system=SYSTEM_PROMPT,
            tools=[README_TOOL, GRAPH_TOOL],
            messages=messages,
        )

        tool_uses = [b for b in message.content if b.type == "tool_use"]
        if not tool_uses:
            break

        # Append assistant turn
        messages.append({"role": "assistant", "content": message.content})

        tool_results = []
        for tool_use in tool_uses:
            if tool_use.name == "emit_knowledge_graph":
                raw = tool_use.input
                nodes = [Node(**{k: v for k, v in n.items() if k in NODE_FIELDS}) for n in raw.get("nodes", [])]
                edges = [Edge(**{**{k: v for k, v in e.items() if k in EDGE_FIELDS}, "weight": e.get("weight", 1.0)}) for e in raw.get("edges", [])]
                # Return immediately — no tool_result needed since we don't continue the loop.
                return GraphOutput(nodes=nodes, edges=edges)

            elif tool_use.name == "fetch_github_readme":
                content = await _fetch_readme(tool_use.input["owner"], tool_use.input["repo"])
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": content or "README not available.",
                })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

    raise RuntimeError("Synthesizer exceeded max iterations without emitting graph")
