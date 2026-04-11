import asyncio
import json
from dataclasses import asdict
from datetime import datetime, timezone
from google.cloud import storage
from models import GraphOutput, ActivityFeed, NowSnapshot
from sources.spotify import SpotifyData
from sources.steam import SteamData
from sources.trakt import TraktData
from sources.github import GitHubData


def build_currently(
    github: GitHubData,
    spotify: SpotifyData,
    steam: SteamData,
    trakt: TraktData,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()

    result: dict = {"generated_at": now}

    # working_on: top 2 recently-updated public repos
    result["working_on"] = [
        {"name": r.name, "url": r.url}
        for r in github.repos[:2]
        if r.url
    ]

    # listening_to: most recently played track
    if spotify.recently_played:
        track = spotify.recently_played[0]
        result["listening_to"] = {"artist": track.artist, "track": track.name, "url": track.url}
    elif spotify.top_tracks:
        t = spotify.top_tracks[0]
        result["listening_to"] = {"artist": t.artist, "track": t.name, "url": t.url}

    # playing: most recently played Steam game
    if steam.recently_played:
        g = steam.recently_played[0]
        result["playing"] = {"name": g.name, "hours": g.hours_played, "url": g.store_url}
    elif steam.most_played:
        g = steam.most_played[0]
        result["playing"] = {"name": g.name, "hours": g.hours_played, "url": g.store_url}

    # watching: currently watching show, else most recent history item
    if trakt.watching:
        w = trakt.watching
        entry: dict = {"title": w.title, "url": w.trakt_url}
        if w.media_type == "show":
            entry["season"] = None  # season unknown from /watching endpoint
        result["watching"] = entry
    elif trakt.history:
        item = trakt.history[0]
        entry = {"title": item.title, "url": item.trakt_url}
        result["watching"] = entry

    return result


def _serialise(obj) -> str:
    return json.dumps(asdict(obj), indent=2, default=str)


def _sync_upload(bucket_name: str, uploads: dict[str, str]) -> None:
    client = storage.Client()
    gcs_bucket = client.bucket(bucket_name)
    for key, content in uploads.items():
        blob = gcs_bucket.blob(key)
        blob.cache_control = "public, max-age=300"
        blob.upload_from_string(content, content_type="application/json")


async def write_outputs(
    bucket: str,
    graph: GraphOutput,
    feed: ActivityFeed,
    now: NowSnapshot,
    currently: dict,
) -> None:
    uploads = {
        "graph.json": _serialise(graph),
        "activity-feed.json": _serialise(feed),
        "now.json": _serialise(now),
        "currently.json": json.dumps(currently, indent=2),
    }
    await asyncio.to_thread(_sync_upload, bucket, uploads)
