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
                            "description": "For interest nodes set subtype to one of: artist, album, track, podcast, audiobook, movie, show, genre, playlist",
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

Given data from GitHub, Spotify, Steam, Trakt, Apple Health, and a personal bio, emit a structured
knowledge graph capturing their skills, projects, experience, education, and interests as typed nodes
with weighted edges.

You may call fetch_github_readme for up to 3 repositories to get richer project descriptions.
Once you have enough context, call emit_knowledge_graph with the final graph.

IMPORTANT: The edges array must NOT be empty. Every node must connect to at least one other node.
IMPORTANT: Emit 80-120 nodes total. More nodes = richer graph highlighting.

Node rules:
- Node IDs: stable snake_case prefixed by type (e.g. skill-python, project-ml-tool)
- For interest nodes use: interest-{subtype}-{slugified-name} (e.g. interest-artist-kendrick-lamar)
- Emit granular skill nodes: individual frameworks, tools, and languages (not just "Python" — also
  skill-fastapi, skill-nextjs, skill-pytorch, skill-terraform, etc.)
- Infer skill nodes from GitHub languages, topics, repo names, and bio content
- All cultural/media content uses type "interest" with metadata.subtype set to one of:
  artist, album, track, podcast, audiobook, movie, show, genre
- Emit up to 5 artist nodes, 3 album nodes, 3 podcast nodes, 2 audiobook nodes, 3 genre nodes
- Add movie/show nodes for Trakt history
- Add a health node if Apple Health data is present
- Emit nodes from bio content using existing types (skill, experience, education, interest);
  set metadata.source = "bio" on these nodes
- Always set metadata.url on every interest node where a URL is available
- Always set metadata.subtype on every interest node
- Prefer accuracy over speculation; use bio content to enrich descriptions

Enriched metadata — always populate when the data is present:
- project nodes: set metadata.commits_last_30d (integer) and metadata.last_pushed_at (date string)
  from github.repos[].commits_last_30d and github.repos[].last_pushed_at
- artist nodes: set metadata.recent_play_count (integer) from spotify.artist_play_counts[artist_name]
  and metadata.last_played_at (ISO string) from spotify.artist_last_played[artist_name]
- playlist nodes (subtype "playlist"): emit one node per entry in spotify.playlists; set
  metadata.track_count, metadata.top_genres (list), metadata.genre_distribution (object of top genres
  with counts), metadata.recently_added (list of {track, artist} for the last 5 additions)
- game/interest nodes for Steam: set metadata.hours_total and metadata.hours_last_2weeks from
  steam.most_played and steam.recently_played; a game appearing in recently_played is actively
  being played right now — reflect that in the description

Edge rules (apply all that are relevant — edges array must not be empty):
- skill → project: used_in edges for each language/skill used in a project
- album → artist: relates_to edge (every album node must connect to its artist node)
- genre → artist: relates_to edge (every artist node must connect to at least one genre node)
- artist/album/genre → project: relates_to edge when music taste is relevant to a project
- podcast/audiobook → skill: relates_to edge when the topic overlaps a skill
- interest → interest: relates_to edges between related interests
- playlist → artist: relates_to edge when the artist appears in the playlist
- playlist → genre: relates_to edge for top genres in a playlist
- bio-sourced nodes → relevant skill/project/experience nodes: relates_to edges
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
    bio: str = "",
    resume: str = "",
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
                    "last_pushed_at": r.last_pushed_at,
                    "commits_last_30d": r.commits_last_30d,
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
            "artist_play_counts": spotify.artist_play_counts,
            "artist_last_played": spotify.artist_last_played,
            "playlists": [
                {
                    "id": pl.id,
                    "name": pl.name,
                    "track_count": pl.track_count,
                    "url": pl.url,
                    "top_genres": pl.top_genres,
                    "genre_distribution": {
                        g: c for g, c in sorted(
                            pl.genre_distribution.items(), key=lambda x: x[1], reverse=True
                        )[:20]
                    },
                    "recently_added": [
                        {"track": t.name, "artist": t.artist, "added_at": t.added_at, "url": t.url}
                        for t in pl.recently_added
                    ],
                }
                for pl in spotify.playlists
            ],
        },
        "steam": {
            "most_played": [{"name": g.name, "hours_total": g.hours_played, "hours_last_2weeks": g.hours_last_2weeks, "url": g.store_url} for g in steam.most_played[:5]],
            "recently_played": [{"name": g.name, "hours_total": g.hours_played, "hours_last_2weeks": g.hours_last_2weeks, "url": g.store_url} for g in steam.recently_played],
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
        "bio": bio,
        "resume": resume,
    }

    client = anthropic.Anthropic(api_key=api_key)
    messages = [{"role": "user", "content": f"Here is my data:\n\n{json.dumps(context, indent=2)}"}]

    for iteration in range(MAX_ITERATIONS):
        print(f"  Iteration {iteration + 1}/{MAX_ITERATIONS}...")
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
            print(f"  No tool call on iteration {iteration + 1} — stopping.")
            break

        tool_names = [t.name for t in tool_uses]
        print(f"  Tools called: {', '.join(tool_names)}")

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
                repo = tool_use.input["repo"]
                content = await _fetch_readme(tool_use.input["owner"], repo)
                print(f"  Fetched README: {repo} ({len(content)} chars)")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": content or "README not available.",
                })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

    raise RuntimeError("Synthesizer exceeded max iterations without emitting graph")
