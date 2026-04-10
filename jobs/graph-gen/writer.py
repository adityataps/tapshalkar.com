import asyncio
import json
from dataclasses import asdict
from google.cloud import storage
from models import GraphOutput, ActivityFeed, NowSnapshot


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
) -> None:
    uploads = {
        "graph.json": _serialise(graph),
        "activity-feed.json": _serialise(feed),
        "now.json": _serialise(now),
    }
    await asyncio.to_thread(_sync_upload, bucket, uploads)
