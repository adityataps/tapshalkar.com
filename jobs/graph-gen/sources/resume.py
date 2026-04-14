import asyncio
from google.cloud import storage

RESUME_OBJECT = "resume_parsed.md"


def _sync_fetch(bucket_name: str) -> str:
    client = storage.Client()
    blob = client.bucket(bucket_name).blob(RESUME_OBJECT)
    if not blob.exists():
        return ""
    return blob.download_as_text()


async def fetch_resume(bucket_name: str) -> str:
    """Fetch the parsed resume from GCS. Returns empty string if not yet generated."""
    try:
        text = await asyncio.to_thread(_sync_fetch, bucket_name)
        if text:
            print(f"Loaded {RESUME_OBJECT} ({len(text)} chars)")
        else:
            print(f"{RESUME_OBJECT} not found in GCS — skipping")
        return text
    except Exception as e:
        print(f"Failed to load {RESUME_OBJECT}: {e}")
        return ""
