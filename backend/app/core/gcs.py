import asyncio
from google.cloud import storage


async def fetch_object(bucket_name: str, key: str) -> bytes:
    """Fetch a GCS object and return its contents as bytes."""
    def _sync() -> bytes:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(key)
        return blob.download_as_bytes()

    return await asyncio.to_thread(_sync)
