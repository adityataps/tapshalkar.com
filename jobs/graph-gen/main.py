import asyncio
import os
from datetime import datetime, timezone

from models import ActivityFeed, ActivityItem, NowSnapshot
from sources.github import fetch_github
from sources.spotify import fetch_spotify
from sources.steam import fetch_steam
from synthesizer import synthesize_graph
from writer import write_outputs


def _build_activity_feed(github, spotify, steam):
    items = []

    for track in spotify.recently_played[:5]:
        items.append(ActivityItem(
            type="track",
            title=track.name,
            subtitle=track.artist,
            timestamp=track.played_at,
        ))

    for game in steam.recently_played[:3]:
        items.append(ActivityItem(
            type="game",
            title=game,
            subtitle="Steam",
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))

    items.sort(key=lambda i: i.timestamp, reverse=True)
    return ActivityFeed(items=items[:10])


def _build_now(github, spotify, steam):
    return NowSnapshot(
        current_projects=[r.name for r in github.repos[:3]],
        listening_to=spotify.top_artists[:3],
        recently_played_games=steam.recently_played[:3],
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


async def run():
    bucket = os.environ["GCS_BUCKET"]
    api_key = os.environ["ANTHROPIC_API_KEY"]

    print("Fetching sources in parallel...")
    github, spotify, steam = await asyncio.gather(
        fetch_github(username=os.environ["GITHUB_USERNAME"], token=os.environ["GITHUB_TOKEN"]),
        fetch_spotify(
            client_id=os.environ["SPOTIFY_CLIENT_ID"],
            client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
            refresh_token=os.environ["SPOTIFY_REFRESH_TOKEN"],
        ),
        fetch_steam(api_key=os.environ["STEAM_API_KEY"], user_id=os.environ["STEAM_USER_ID"]),
    )
    print(f"Fetched: {len(github.repos)} repos, {len(spotify.top_artists)} artists, {len(steam.most_played)} games")

    print("Synthesising knowledge graph with Claude...")
    graph = await synthesize_graph(github=github, spotify=spotify, steam=steam, api_key=api_key)
    print(f"Graph: {len(graph.nodes)} nodes, {len(graph.edges)} edges")

    feed = _build_activity_feed(github, spotify, steam)
    now = _build_now(github, spotify, steam)

    print("Writing outputs to GCS...")
    await write_outputs(bucket=bucket, graph=graph, feed=feed, now=now)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(run())
