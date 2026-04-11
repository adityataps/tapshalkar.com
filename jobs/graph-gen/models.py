from dataclasses import dataclass, field


@dataclass
class Node:
    id: str           # snake_case, e.g. "skill-python"
    type: str         # skill | project | experience | education | interest
    label: str
    description: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class Edge:
    source: str       # node id
    target: str       # node id
    type: str         # used_in | worked_on | studied_at | interested_in | relates_to
    weight: float = 1.0


@dataclass
class GraphOutput:
    nodes: list[Node]
    edges: list[Edge]


@dataclass
class ActivityItem:
    type: str         # "commit" | "track" | "game"
    title: str
    subtitle: str
    timestamp: str    # ISO 8601
    url: str = ""


@dataclass
class ActivityFeed:
    items: list[ActivityItem]


@dataclass
class NowSnapshot:
    current_projects: list[str]
    listening_to: list[str]      # top 3 Spotify artists
    recently_played_games: list[str]
    updated_at: str              # ISO 8601


@dataclass
class TraktItem:
    title: str
    year: int
    media_type: str    # "movie" or "show"
    trakt_url: str
    genres: list[str] = field(default_factory=list)
    status: str = ""   # "watched" | "watching" | "watchlist"
