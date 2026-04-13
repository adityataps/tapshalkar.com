import pytest
from pathlib import Path
from unittest.mock import patch
from sources.bio import load_bio


def test_load_bio_returns_content(tmp_path):
    bio_file = tmp_path / "bio.md"
    bio_file.write_text("# About me\nI build things.")
    with patch("sources.bio.BIO_PATH", bio_file):
        result = load_bio()
    assert result == "# About me\nI build things."


def test_load_bio_returns_empty_string_when_missing(tmp_path):
    missing = tmp_path / "bio.md"
    with patch("sources.bio.BIO_PATH", missing):
        result = load_bio()
    assert result == ""
