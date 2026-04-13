# Phase 2a: Graph Enrichment + bio.md Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `bio.md` personal bio source to the graph-gen job, enrich the synthesizer to produce 60–80 nodes with more granular skills, and upload `bio.md` to GCS so the backend chat endpoint can load it.

**Architecture:** New `sources/bio.py` reads `bio.md` from the repo. `main.py` passes bio text to the synthesizer and uploads it to GCS. The synthesizer context gains a `"bio"` key and updated prompts for richer node emission. `writer.py` gains a `_upload_text` helper for non-JSON files.

**Tech Stack:** Python 3.13, google-cloud-storage, uv, pytest

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `jobs/graph-gen/bio.md` | Create | Personal bio in free-form markdown |
| `jobs/graph-gen/sources/bio.py` | Create | `load_bio() -> str` — reads bio.md from disk |
| `jobs/graph-gen/synthesizer.py` | Modify | Add `bio: str` param, richer node instructions |
| `jobs/graph-gen/writer.py` | Modify | Add `_upload_text` + bio upload in `write_outputs` |
| `jobs/graph-gen/main.py` | Modify | Load bio, pass to synthesizer, pass to write_outputs |
| `jobs/graph-gen/tests/test_bio.py` | Create | Test bio loading (file present + missing) |
| `jobs/graph-gen/tests/test_synthesizer.py` | Modify | Pass `bio="test bio"` to `synthesize_graph` |

---

### Task 1: `sources/bio.py` + tests

**Files:**
- Create: `jobs/graph-gen/sources/bio.py`
- Create: `jobs/graph-gen/tests/test_bio.py`

- [ ] **Step 1: Write the failing tests**

```python
# jobs/graph-gen/tests/test_bio.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd jobs/graph-gen && uv run pytest tests/test_bio.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'sources.bio'`

- [ ] **Step 3: Create `sources/bio.py`**

```python
# jobs/graph-gen/sources/bio.py
from pathlib import Path

BIO_PATH = Path(__file__).parent.parent / "bio.md"


def load_bio() -> str:
    """Read bio.md from the repo root of the job. Returns empty string if absent."""
    return BIO_PATH.read_text() if BIO_PATH.exists() else ""
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd jobs/graph-gen && uv run pytest tests/test_bio.py -v
```

Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add jobs/graph-gen/sources/bio.py jobs/graph-gen/tests/test_bio.py
git commit -m "feat(graph-gen): add bio source module"
```

---

### Task 2: Create `bio.md`

**Files:**
- Create: `jobs/graph-gen/bio.md`

- [ ] **Step 1: Create the file with starter content**

```markdown
# About Aditya Tapshalkar

I'm a software engineer focused on machine learning, AI systems, and the products built on top of them. I'm based in Atlanta, GA.

## Background

I studied Computer Science and have worked across early-stage startups and larger engineering teams. Most of my career has been at the intersection of applied ML and product engineering — building systems that are both technically rigorous and actually useful to people.

## What I work on

I gravitate toward problems where language models, knowledge representation, or real-time data can unlock something meaningfully better than what existed before. I care a lot about the full stack — from the model and data pipeline down to the interface the user actually touches.

## Outside work

Music is a big part of how I think and recharge — I listen across a lot of genres but hip-hop and electronic are home bases. I follow film seriously, mostly through directors and cinematographers I return to. I'm an active gamer (mostly PC), and I pay close attention to how games handle narrative and interactivity as a medium.

## Values

I prefer direct communication, working in small focused teams, and shipping things. I'm skeptical of complexity for its own sake and try to find the simplest solution that actually solves the problem.
```

- [ ] **Step 2: Verify the file reads correctly**

```bash
cd jobs/graph-gen && uv run python -c "from sources.bio import load_bio; bio = load_bio(); print(len(bio), 'chars'); print(bio[:100])"
```

Expected: prints char count > 0 and first 100 chars of the bio

- [ ] **Step 3: Commit**

```bash
git add jobs/graph-gen/bio.md
git commit -m "feat(graph-gen): add personal bio.md"
```

---

### Task 3: Update synthesizer to accept bio + richer node instructions

**Files:**
- Modify: `jobs/graph-gen/synthesizer.py`
- Modify: `jobs/graph-gen/tests/test_synthesizer.py`

- [ ] **Step 1: Update the test to pass bio to synthesize_graph**

In `jobs/graph-gen/tests/test_synthesizer.py`, change the `synthesize_graph` call signature:

```python
# Add bio="test bio" to the call — find the existing call and update it:
result = await synthesize_graph(
    github=SAMPLE_GITHUB,
    spotify=SAMPLE_SPOTIFY,
    steam=SAMPLE_STEAM,
    trakt=SAMPLE_TRAKT,
    health=SAMPLE_HEALTH,
    api_key="test-key",
    bio="test bio",
)
```

- [ ] **Step 2: Run existing test to confirm it still passes (baseline)**

```bash
cd jobs/graph-gen && uv run pytest tests/test_synthesizer.py -v
```

Expected: PASS (it passes before our change since `bio` is not yet in the signature)

- [ ] **Step 3: Update `synthesizer.py`**

Add `bio: str = ""` parameter to `synthesize_graph` and update `SYSTEM_PROMPT` and context:

```python
# jobs/graph-gen/synthesizer.py
# Replace the existing SYSTEM_PROMPT with:

SYSTEM_PROMPT = """You are a knowledge graph synthesizer for a software engineer's portfolio.

Given data from GitHub, Spotify, Steam, Trakt, Apple Health, and a personal bio, emit a structured
knowledge graph capturing their skills, projects, experience, education, and interests as typed nodes
with weighted edges.

You may call fetch_github_readme for up to 3 repositories to get richer project descriptions.
Once you have enough context, call emit_knowledge_graph with the final graph.

IMPORTANT: The edges array must NOT be empty. Every node must connect to at least one other node.
IMPORTANT: Emit 60-80 nodes total. More nodes = richer graph highlighting.

Node rules:
- Node IDs: stable snake_case prefixed by type (e.g. skill-python, project-ml-tool)
- For interest nodes use: interest-{subtype}-{slugified-name} (e.g. interest-artist-kendrick-lamar)
- Emit granular skill nodes: individual frameworks, tools, and languages (not just "Python" — also
  skill-fastapi, skill-nextjs, skill-pytorch, skill-terraform, etc.)
- Infer skill nodes from GitHub languages, topics, repo names, and bio content
- All cultural/media content uses type "interest" with metadata.subtype set to one of:
  artist, album, track, podcast, audiobook, movie, show, genre
- Emit up to 5 artist nodes, 3 album nodes, 3 podcast nodes, 2 audiobook nodes, 3 genre nodes
- Add movie/show nodes for Trakt history
- Add a health node if Apple Health data is present
- Emit nodes from bio content using existing types (skill, experience, education, interest);
  set metadata.source = "bio" on these nodes
- Always set metadata.url on every interest node where a URL is available
- Always set metadata.subtype on every interest node
- Prefer accuracy over speculation; use bio content to enrich descriptions

Edge rules (apply all that are relevant — edges array must not be empty):
- skill → project: used_in edges for each language/skill used in a project
- album → artist: relates_to edge (every album node must connect to its artist node)
- genre → artist: relates_to edge (every artist node must connect to at least one genre node)
- artist/album/genre → project: relates_to edge when music taste is relevant to a project
- podcast/audiobook → skill: relates_to edge when the topic overlaps a skill
- interest → interest: relates_to edges between related interests
- bio-sourced nodes → relevant skill/project/experience nodes: relates_to edges
- Edge weight 0.0–1.0 based on relationship strength
"""
```

Also update `synthesize_graph` signature and context:

```python
async def synthesize_graph(
    github: GitHubData,
    spotify: SpotifyData,
    steam: SteamData,
    trakt: TraktData,
    health: HealthSummary,
    api_key: str,
    bio: str = "",
) -> GraphOutput:
    context = {
        # ... existing keys unchanged ...
        "bio": bio,  # add this at the end
    }
```

The `context` dict structure stays the same as before — just append `"bio": bio` after the existing `"health"` key.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd jobs/graph-gen && uv run pytest tests/test_synthesizer.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add jobs/graph-gen/synthesizer.py jobs/graph-gen/tests/test_synthesizer.py
git commit -m "feat(graph-gen): add bio context and richer node instructions to synthesizer"
```

---

### Task 4: Update `writer.py` to upload `bio.md`

**Files:**
- Modify: `jobs/graph-gen/writer.py`

- [ ] **Step 1: Check existing writer test**

```bash
cd jobs/graph-gen && uv run pytest tests/test_writer.py -v
```

Expected: PASS (baseline)

- [ ] **Step 2: Update `writer.py`**

Add `_upload_text` helper and a `bio` parameter to `write_outputs`:

```python
# jobs/graph-gen/writer.py
# Add after the existing _sync_upload function:

def _upload_text(bucket_name: str, key: str, content: str) -> None:
    client = storage.Client()
    gcs_bucket = client.bucket(bucket_name)
    blob = gcs_bucket.blob(key)
    blob.cache_control = "public, max-age=300"
    blob.upload_from_string(content, content_type="text/plain")


# Update write_outputs signature and body:
async def write_outputs(
    bucket: str,
    graph: GraphOutput,
    feed: ActivityFeed,
    now: NowSnapshot,
    currently: dict,
    bio: str = "",
) -> None:
    uploads = {
        "graph.json": _serialise(graph),
        "activity-feed.json": _serialise(feed),
        "now.json": _serialise(now),
        "currently.json": json.dumps(currently, indent=2),
    }
    await asyncio.to_thread(_sync_upload, bucket, uploads)
    if bio:
        await asyncio.to_thread(_upload_text, bucket, "bio.md", bio)
```

- [ ] **Step 3: Run writer tests**

```bash
cd jobs/graph-gen && uv run pytest tests/test_writer.py -v
```

Expected: PASS (bio param defaults to "" so existing test is unaffected)

- [ ] **Step 4: Commit**

```bash
git add jobs/graph-gen/writer.py
git commit -m "feat(graph-gen): upload bio.md to GCS alongside graph outputs"
```

---

### Task 5: Wire bio into `main.py`

**Files:**
- Modify: `jobs/graph-gen/main.py`

- [ ] **Step 1: Update `main.py`**

```python
# jobs/graph-gen/main.py
# Add import at top:
from sources.bio import load_bio

# In run(), after the existing imports, add bio loading before the fetch calls:
async def run():
    bucket = os.environ["GCS_BUCKET"]
    api_key = os.environ["ANTHROPIC_API_KEY"]
    health_prefix = os.environ.get("APPLE_HEALTH_PREFIX", "data/ephemeral/apple-health/")

    bio = load_bio()
    if bio:
        print(f"Loaded bio.md ({len(bio)} chars)")
    else:
        print("No bio.md found — skipping bio context")

    print("Fetching sources in parallel...")
    # ... existing fetch calls unchanged ...

    print("Synthesising knowledge graph with Claude...")
    graph = await synthesize_graph(
        github=github, spotify=spotify, steam=steam,
        trakt=trakt, health=health, api_key=api_key,
        bio=bio,
    )
    print(f"Graph: {len(graph.nodes)} nodes, {len(graph.edges)} edges")

    feed = _build_activity_feed(github, spotify, steam)
    now = _build_now(github, spotify, steam)
    currently = build_currently(github, spotify, steam, trakt)

    print("Writing outputs to GCS...")
    await write_outputs(bucket=bucket, graph=graph, feed=feed, now=now, currently=currently, bio=bio)
    print("Done.")
```

- [ ] **Step 2: Run full test suite**

```bash
cd jobs/graph-gen && uv run pytest -v
```

Expected: all tests PASS

- [ ] **Step 3: Smoke test locally (dry run)**

```bash
cd jobs/graph-gen && uv run python -c "
from sources.bio import load_bio
from synthesizer import synthesize_graph
bio = load_bio()
print('Bio loaded:', len(bio), 'chars')
print('First line:', bio.splitlines()[0] if bio else '(empty)')
"
```

Expected: prints bio char count and first line

- [ ] **Step 4: Commit**

```bash
git add jobs/graph-gen/main.py
git commit -m "feat(graph-gen): wire bio.md into synthesis and GCS upload"
```
