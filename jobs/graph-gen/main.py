import asyncio
import os
from datetime import datetime, timezone

from models import ActivityFeed, ActivityItem, NowSnapshot
from sources.github import fetch_github
from sources.spotify import fetch_spotify
from sources.steam import fetch_steam
from sources.trakt import fetch_trakt, TraktData
from sources.apple_health import fetch_apple_health
from synthesizer import synthesize_graph
from writer import write_outputs, build_currently


def _build_activity_feed(github, spotify, steam):
    items = []

    for track in spotify.recently_played[:5]:
        items.append(ActivityItem(
            type="track",
            title=track.name,
            subtitle=track.artist,
            timestamp=track.played_at,
        ))

    # Steam games are excluded from the activity feed: the Steam API provides
    # no per-game timestamps (only a 2-week playtime aggregate), so we cannot
    # reliably order them relative to Spotify tracks.

    items.sort(key=lambda i: i.timestamp, reverse=True)
    return ActivityFeed(items=items[:10])


def _build_now(github, spotify, steam):
    return NowSnapshot(
        current_projects=[r.name for r in github.repos[:3]],
        listening_to=[a.name for a in spotify.top_artists[:3]],
        recently_played_games=[g.name for g in steam.recently_played[:3]],
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


async def run():
    bucket = os.environ["GCS_BUCKET"]
    api_key = os.environ["ANTHROPIC_API_KEY"]
    health_prefix = os.environ.get("APPLE_HEALTH_PREFIX", "data/ephemeral/apple-health/")

    print("Fetching sources in parallel...")
    github, spotify, steam, health = await asyncio.gather(
        fetch_github(username=os.environ["GITHUB_USERNAME"], token=os.environ["GITHUB_TOKEN"]),
        fetch_spotify(
            client_id=os.environ["SPOTIFY_CLIENT_ID"],
            client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
            refresh_token=os.environ["SPOTIFY_REFRESH_TOKEN"],
        ),
        fetch_steam(api_key=os.environ["STEAM_API_KEY"], user_id=os.environ["STEAM_USER_ID"]),
        fetch_apple_health(bucket_name=bucket, prefix=health_prefix),
    )

    trakt = TraktData(history=[], watchlist=[], watching=None)
    if os.environ.get("TRAKT_CLIENT_ID"):
        try:
            trakt = await fetch_trakt(
                client_id=os.environ["TRAKT_CLIENT_ID"],
                client_secret=os.environ["TRAKT_CLIENT_SECRET"],
                refresh_token=os.environ["TRAKT_REFRESH_TOKEN"],
            )
        except Exception as e:
            print(f"Trakt fetch failed (skipping): {e}")

    print(f"Fetched: {len(github.repos)} repos, {len(spotify.top_artists)} artists, "
          f"{len(steam.most_played)} games, {len(trakt.history)} trakt items, "
          f"steps={health.avg_daily_steps}")

    print("Synthesising knowledge graph with Claude...")
    graph = await synthesize_graph(
        github=github, spotify=spotify, steam=steam,
        trakt=trakt, health=health, api_key=api_key,
    )
    print(f"Graph: {len(graph.nodes)} nodes, {len(graph.edges)} edges")

    feed = _build_activity_feed(github, spotify, steam)
    now = _build_now(github, spotify, steam)
    currently = build_currently(github, spotify, steam, trakt)

    print("Writing outputs to GCS...")
    await write_outputs(bucket=bucket, graph=graph, feed=feed, now=now, currently=currently)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(run())
