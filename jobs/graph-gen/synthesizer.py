import asyncio
import json
import anthropic
from models import GraphOutput, Node, Edge
from sources.github import GitHubData
from sources.spotify import SpotifyData
from sources.steam import SteamData

GRAPH_TOOL = {
    "name": "emit_knowledge_graph",
    "description": "Emit a typed knowledge graph representing a person's skills, projects, experience, education, and interests.",
    "input_schema": {
        "type": "object",
        "properties": {
            "nodes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id":          {"type": "string", "description": "Stable snake_case identifier, e.g. skill-python"},
                        "type":        {"type": "string", "enum": ["skill", "project", "experience", "education", "interest"]},
                        "label":       {"type": "string"},
                        "description": {"type": "string"},
                        "metadata":    {"type": "object"},
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

SYSTEM_PROMPT = """You are a knowledge graph synthesizer. Given data about a software engineer
pulled from GitHub, Spotify, and Steam, emit a structured knowledge graph that captures their
skills, projects, experience, education, and interests as typed nodes with weighted edges.

Rules:
- Node IDs must be stable snake_case strings prefixed by type (e.g. skill-python, project-ml-tool)
- Infer skills from GitHub languages and repo topics
- Infer interest nodes from music genres and games
- Connect skills to projects they are used in (used_in edges)
- Set edge weight 0.0-1.0 based on strength of relationship
- Omit nodes you cannot confidently infer - prefer fewer, accurate nodes over many speculative ones
"""


NODE_FIELDS = {"id", "type", "label", "description", "metadata"}
EDGE_FIELDS = {"source", "target", "type", "weight"}


async def synthesize_graph(
    github: GitHubData,
    spotify: SpotifyData,
    steam: SteamData,
    api_key: str,
) -> GraphOutput:
    context = {
        "github": {
            "top_languages": github.top_languages,
            "repos": [
                {"name": r.name, "description": r.description, "topics": r.topics, "stars": r.stars}
                for r in github.repos[:20]
            ],
        },
        "spotify": {
            "top_artists": spotify.top_artists,
            "top_genres": spotify.top_genres,
            "top_tracks": spotify.top_tracks[:5],
        },
        "steam": {
            "most_played": steam.most_played[:5],
            "recently_played": steam.recently_played,
        },
    }

    client = anthropic.Anthropic(api_key=api_key)

    message = await asyncio.to_thread(
        client.messages.create,
        model="claude-opus-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[GRAPH_TOOL],
        tool_choice={"type": "tool", "name": "emit_knowledge_graph"},
        messages=[{"role": "user", "content": f"Here is my data:\n\n{json.dumps(context, indent=2)}"}],
    )

    tool_use = next(block for block in message.content if block.type == "tool_use")
    raw = tool_use.input

    nodes = [Node(**{k: v for k, v in n.items() if k in NODE_FIELDS}) for n in raw["nodes"]]
    edges = [Edge(**{**{k: v for k, v in e.items() if k in EDGE_FIELDS}, "weight": e.get("weight", 1.0)}) for e in raw["edges"]]

    return GraphOutput(nodes=nodes, edges=edges)
