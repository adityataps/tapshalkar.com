from pathlib import Path

BIO_PATH = Path(__file__).parent.parent / "bio.md"


def load_bio() -> str:
    """Read bio.md from the repo root of the job. Returns empty string if absent."""
    return BIO_PATH.read_text() if BIO_PATH.exists() else ""
