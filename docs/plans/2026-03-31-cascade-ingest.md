# cascade-ingest Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract ingestion logic from `cascade-api` into a standalone `cascade-ingest` PyPI package that any agent can install to bring personal data exports into the Cascade Portable Memory Format.

**Architecture:** Create `cascade-ingest/` as a new top-level sibling directory with its own `pyproject.toml`. Copy `ingest.py`, `permissions.py`, `consent.py`, and `importers/` from `cascade-api` into `cascade_ingest/`, update their internal imports, then update `cascade-api` to depend on `cascade-ingest` and rewrite its imports. Supabase ingestion is an optional extra.

**Tech Stack:** Python 3.11+, hatchling (build backend), cascade-memory (core dep), supabase>=2.12.0 (optional dep), pytest + pytest-asyncio (tests)

---

### Task 1: Scaffold the package directory

**Files:**
- Create: `cascade-ingest/pyproject.toml`
- Create: `cascade-ingest/README.md`
- Create: `cascade-ingest/cascade_ingest/__init__.py`
- Create: `cascade-ingest/cascade_ingest/importers/__init__.py`

**Step 1: Create the directory structure**

```bash
mkdir -p cascade-ingest/cascade_ingest/importers
mkdir -p cascade-ingest/tests
```

**Step 2: Create `cascade-ingest/pyproject.toml`**

```toml
[project]
name = "cascade-ingest"
version = "0.1.0"
description = "Data ingestion pipeline for cascade-memory — imports personal data exports into the Cascade Portable Memory Format"
requires-python = ">=3.11"
dependencies = [
    "cascade-memory>=0.1.0",
]

[project.optional-dependencies]
supabase = [
    "supabase>=2.12.0",
]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.25.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Step 3: Create `cascade-ingest/README.md`**

```markdown
# cascade-ingest

Data ingestion pipeline for [cascade-memory](https://pypi.org/project/cascade-memory/).

Parses personal data exports into the Cascade Portable Memory Format — the bridge between your scattered digital history and a unified, queryable knowledge graph.

## Install

```bash
pip install cascade-ingest

# With Supabase support
pip install cascade-ingest[supabase]
```

## Supported Sources

- **JSONL persona files** — lifelog, email, calendar, social, transactions, AI conversations, file metadata
- **ChatGPT** — `conversations.json` export
- **Google Takeout** — `.zip`, `.mbox`, `.ics` files

## Quick Start

```python
from pathlib import Path
from cascade_memory import MemoryClient  # your configured client
from cascade_ingest import ingest_persona

stats = await ingest_persona(client, tenant_id="alice", persona_dir=Path("./alice"))
print(stats)  # {"records_ingested": 530, "links_created": 47}
```
```

**Step 4: Create `cascade-ingest/cascade_ingest/__init__.py`**

```python
"""cascade-ingest — data ingestion pipeline for cascade-memory."""

from cascade_ingest.ingest import ingest_persona
from cascade_ingest.consent import (
    ConsentConfig,
    get_consent,
    set_consent,
    SENSITIVE_TAGS,
    extract_source_from_memory_type,
)
from cascade_ingest.permissions import classify_sensitivity, PRIVATE_SOURCES, PUBLIC_SOURCES

__all__ = [
    "ingest_persona",
    "ConsentConfig",
    "get_consent",
    "set_consent",
    "SENSITIVE_TAGS",
    "extract_source_from_memory_type",
    "classify_sensitivity",
    "PRIVATE_SOURCES",
    "PUBLIC_SOURCES",
]
```

**Step 5: Create `cascade-ingest/cascade_ingest/importers/__init__.py`**

```python
"""cascade-ingest importers — parse real-world export formats into Cascade records."""
```

**Step 6: Commit**

```bash
git add cascade-ingest/
git commit -m "feat(cascade-ingest): scaffold package structure"
```

---

### Task 2: Copy and update `consent.py`

**Files:**
- Create: `cascade-ingest/cascade_ingest/consent.py`
- Reference: `cascade-api/cascade_api/consent.py`

**Step 1: Write a failing test**

Create `cascade-ingest/tests/test_consent.py`:

```python
from cascade_ingest.consent import ConsentConfig, SENSITIVE_TAGS, extract_source_from_memory_type


def test_consent_config_defaults():
    config = ConsentConfig()
    assert config.get_level("bank") == "owner_only"
    assert config.get_level("calendar") == "public"


def test_consent_config_custom_sources():
    config = ConsentConfig(sources={"bank": "public"})
    assert config.get_level("bank") == "public"


def test_sensitive_tags_override():
    config = ConsentConfig()
    assert config.is_public("calendar", tags=["therapy"]) is False
    assert config.is_public("calendar", tags=["work"]) is True


def test_extract_source_from_memory_type():
    assert extract_source_from_memory_type("public_email") == "email"
    assert extract_source_from_memory_type("private_ai_chat") == "ai_chat"
    assert extract_source_from_memory_type("fact") == "fact"


def test_consent_round_trip():
    config = ConsentConfig(sources={"social": "owner_only"})
    d = config.to_dict()
    restored = ConsentConfig.from_dict(d)
    assert restored.get_level("social") == "owner_only"
```

**Step 2: Run test to verify it fails**

```bash
cd cascade-ingest
pytest tests/test_consent.py -v
```

Expected: `ModuleNotFoundError: No module named 'cascade_ingest'`

**Step 3: Copy `consent.py` from `cascade-api`**

Copy `cascade-api/cascade_api/consent.py` to `cascade-ingest/cascade_ingest/consent.py`.

The file has no internal `cascade_api` imports — no changes needed to the file content itself.

**Step 4: Install the package in editable mode**

```bash
cd cascade-ingest
pip install -e ".[dev]"
```

Note: This will fail if `cascade-memory` is not installed. If so, install it first:
```bash
pip install cascade-memory
# or if working locally:
pip install -e ../cascade-memory
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_consent.py -v
```

Expected: 5 PASSED

**Step 6: Commit**

```bash
git add cascade-ingest/cascade_ingest/consent.py cascade-ingest/tests/test_consent.py
git commit -m "feat(cascade-ingest): add consent module with tests"
```

---

### Task 3: Copy and update `permissions.py`

**Files:**
- Create: `cascade-ingest/cascade_ingest/permissions.py`
- Reference: `cascade-api/cascade_api/permissions.py`

**Step 1: Write a failing test**

Create `cascade-ingest/tests/test_permissions.py`:

```python
from cascade_ingest.permissions import classify_sensitivity, PRIVATE_SOURCES, PUBLIC_SOURCES


def test_private_source():
    record = {"source": "bank", "tags": []}
    assert classify_sensitivity(record) == "private"


def test_public_source():
    record = {"source": "social", "tags": []}
    assert classify_sensitivity(record) == "public"


def test_private_tag_overrides_neutral_source():
    record = {"source": "lifelog", "tags": ["therapy"]}
    assert classify_sensitivity(record) == "private"


def test_neutral_source_no_sensitive_tags():
    record = {"source": "calendar", "tags": ["work"]}
    assert classify_sensitivity(record) == "public"


def test_private_sources_set():
    assert "bank" in PRIVATE_SOURCES
    assert "ai_chat" in PRIVATE_SOURCES


def test_public_sources_set():
    assert "social" in PUBLIC_SOURCES
    assert "files" in PUBLIC_SOURCES
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_permissions.py -v
```

Expected: `ModuleNotFoundError: No module named 'cascade_ingest.permissions'`

**Step 3: Create `cascade-ingest/cascade_ingest/permissions.py`**

The original `cascade_api/permissions.py` imports from `cascade_api.memory` and `cascade_api.consent`. The new version only needs `classify_sensitivity` and the source sets — `filter_by_permission` stays in `cascade-api` since it depends on `SearchResult` from `cascade-memory` and is an API-layer concern, not an ingestion concern.

```python
from cascade_ingest.consent import SENSITIVE_TAGS

PRIVATE_SOURCES = {"bank", "ai_chat"}
PUBLIC_SOURCES = {"social", "files"}


def classify_sensitivity(record: dict) -> str:
    """Classify a record's sensitivity during ingestion.

    Returns 'private' or 'public'. Consent doesn't change what's stored,
    only what's shared — so we stamp the source type at ingest time.
    """
    source = record.get("source", "")
    tags = set(record.get("tags", []))

    if source in PRIVATE_SOURCES:
        return "private"
    if source in PUBLIC_SOURCES:
        return "public"
    if tags & SENSITIVE_TAGS:
        return "private"
    return "public"
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_permissions.py -v
```

Expected: 6 PASSED

**Step 5: Commit**

```bash
git add cascade-ingest/cascade_ingest/permissions.py cascade-ingest/tests/test_permissions.py
git commit -m "feat(cascade-ingest): add permissions/sensitivity classification with tests"
```

---

### Task 4: Copy and update importers

**Files:**
- Create: `cascade-ingest/cascade_ingest/importers/chatgpt.py`
- Create: `cascade-ingest/cascade_ingest/importers/google_takeout.py`
- Reference: `cascade-api/cascade_api/importers/chatgpt.py`
- Reference: `cascade-api/cascade_api/importers/google_takeout.py`

**Step 1: Write failing tests**

Create `cascade-ingest/tests/test_importers.py`:

```python
import json
import tempfile
from pathlib import Path

from cascade_ingest.importers.chatgpt import parse_chatgpt_export
from cascade_ingest.importers.google_takeout import parse_ics


def test_parse_chatgpt_export_basic():
    data = [
        {
            "id": "abc123",
            "title": "Python help",
            "create_time": 1700000000.0,
            "mapping": {
                "node1": {
                    "message": {
                        "author": {"role": "user"},
                        "content": {"parts": ["How do I use list comprehensions?"]},
                    }
                },
                "node2": {
                    "message": {
                        "author": {"role": "assistant"},
                        "content": {"parts": ["List comprehensions are a concise way..."]},
                    }
                },
            },
        }
    ]
    records = parse_chatgpt_export(data)
    assert len(records) == 1
    assert records[0]["source"] == "ai_chat"
    assert records[0]["id"] == "chatgpt_abc123"
    assert "Python help" in records[0]["text"]


def test_parse_chatgpt_export_empty_mapping():
    data = [{"id": "x", "title": "empty", "mapping": {}}]
    records = parse_chatgpt_export(data)
    assert len(records) == 0


def test_parse_ics_basic():
    ics_content = """BEGIN:VCALENDAR
BEGIN:VEVENT
SUMMARY:Team standup
DTSTART:20240115T100000Z
UID:standup-001
END:VEVENT
END:VCALENDAR"""

    with tempfile.NamedTemporaryFile(suffix=".ics", mode="w", delete=False) as f:
        f.write(ics_content)
        tmp_path = Path(f.name)

    records = parse_ics(tmp_path)
    tmp_path.unlink()

    assert len(records) == 1
    assert records[0]["source"] == "calendar"
    assert "Team standup" in records[0]["text"]
    assert records[0]["tags"][0] == "calendar"
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_importers.py -v
```

Expected: `ModuleNotFoundError: No module named 'cascade_ingest.importers.chatgpt'`

**Step 3: Copy importers**

Copy `cascade-api/cascade_api/importers/chatgpt.py` to `cascade-ingest/cascade_ingest/importers/chatgpt.py`.

Copy `cascade-api/cascade_api/importers/google_takeout.py` to `cascade-ingest/cascade_ingest/importers/google_takeout.py`.

Neither file has any `cascade_api` imports — no changes needed.

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_importers.py -v
```

Expected: 3 PASSED

**Step 5: Commit**

```bash
git add cascade-ingest/cascade_ingest/importers/ cascade-ingest/tests/test_importers.py
git commit -m "feat(cascade-ingest): add chatgpt and google_takeout importers with tests"
```

---

### Task 5: Copy and update `ingest.py`

**Files:**
- Create: `cascade-ingest/cascade_ingest/ingest.py`
- Reference: `cascade-api/cascade_api/ingest.py`

**Step 1: Write a failing test**

Add to `cascade-ingest/tests/test_ingest.py`:

```python
import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def persona_dir(tmp_path):
    """Create a minimal persona directory with one JSONL file."""
    records = [
        {
            "id": "cal_001",
            "source": "calendar",
            "text": "Team meeting at 10am",
            "tags": ["work"],
            "refs": [],
        },
        {
            "id": "email_001",
            "source": "email",
            "text": "Re: Team meeting — confirmed",
            "tags": ["work"],
            "refs": ["cal_001"],
        },
    ]
    jsonl_path = tmp_path / "calendar.jsonl"
    with open(jsonl_path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return tmp_path


@pytest.mark.asyncio
async def test_ingest_persona_returns_stats(persona_dir):
    from unittest.mock import AsyncMock, MagicMock

    # Mock MemoryClient
    mock_client = MagicMock()
    mock_tenant = AsyncMock()
    mock_tenant.save = AsyncMock(side_effect=lambda **kwargs: f"mem_{kwargs.get('source_id', 'x')}")
    mock_tenant.link = AsyncMock()
    mock_tenant.core = AsyncMock()
    mock_client.for_tenant.return_value = mock_tenant
    mock_client.store = AsyncMock()
    mock_client.store.get = AsyncMock(return_value=None)

    from cascade_ingest.ingest import ingest_persona

    stats = await ingest_persona(mock_client, "test_tenant", persona_dir)

    assert stats["records_ingested"] == 2
    assert "links_created" in stats
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_ingest.py -v
```

Expected: `ModuleNotFoundError: No module named 'cascade_ingest.ingest'`

**Step 3: Create `cascade-ingest/cascade_ingest/ingest.py`**

Copy `cascade-api/cascade_api/ingest.py` to `cascade-ingest/cascade_ingest/ingest.py`, then update the imports:

Change:
```python
from cascade_api.memory import MemoryClient
from cascade_api.consent import ConsentConfig, set_consent
from cascade_api.permissions import classify_sensitivity, PRIVATE_SOURCES
```

To:
```python
from cascade_memory import MemoryClient
from cascade_ingest.consent import ConsentConfig, set_consent
from cascade_ingest.permissions import classify_sensitivity, PRIVATE_SOURCES
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_ingest.py -v
```

Expected: 1 PASSED

**Step 5: Run all tests**

```bash
pytest -v
```

Expected: All tests PASSED

**Step 6: Commit**

```bash
git add cascade-ingest/cascade_ingest/ingest.py cascade-ingest/tests/test_ingest.py
git commit -m "feat(cascade-ingest): add JSONL persona ingest pipeline with tests"
```

---

### Task 6: Add optional Supabase ingester

**Files:**
- Create: `cascade-ingest/cascade_ingest/ingest_supabase.py`
- Reference: `cascade-api/cascade_api/ingest_supabase.py`

**Step 1: Copy `ingest_supabase.py`**

Copy `cascade-api/cascade_api/ingest_supabase.py` to `cascade-ingest/cascade_ingest/ingest_supabase.py`.

Update the import:

Change:
```python
from cascade_api.memory import MemoryClient
```

To:
```python
from cascade_memory import MemoryClient
```

**Step 2: Verify the optional dep guard**

The file imports `from supabase import Client as SupabaseClient` at the top level. This is correct — if a user doesn't have `supabase` installed and tries to import `cascade_ingest.ingest_supabase`, they'll get a clear `ModuleNotFoundError`. No guard needed since the optional dep pattern is standard.

**Step 3: Commit**

```bash
git add cascade-ingest/cascade_ingest/ingest_supabase.py
git commit -m "feat(cascade-ingest): add optional supabase ingester"
```

---

### Task 7: Update `cascade-api` to depend on `cascade-ingest`

**Files:**
- Modify: `cascade-api/pyproject.toml`
- Modify: `cascade-api/cascade_api/ingest.py` (delete — now in cascade-ingest)
- Modify: `cascade-api/cascade_api/ingest_supabase.py` (delete — now in cascade-ingest)
- Modify: `cascade-api/cascade_api/permissions.py` (update imports)
- Modify: `cascade-api/cascade_api/consent.py` (delete — re-export from cascade-ingest)
- Modify: any `cascade-api` file that imports from the moved modules

**Step 1: Find all files in `cascade-api` that import the moved modules**

```bash
grep -r "from cascade_api\.\(ingest\|permissions\|consent\|importers\)" cascade-api/cascade_api/ --include="*.py" -l
```

Note the list of files returned — these all need import updates.

**Step 2: Add `cascade-ingest` as a dependency in `cascade-api/pyproject.toml`**

Add to the `dependencies` list:
```toml
"cascade-ingest @ ../cascade-ingest",
```

**Step 3: Update imports in each affected file**

For each file found in Step 1, change:
- `from cascade_api.ingest import ...` → `from cascade_ingest.ingest import ...`
- `from cascade_api.ingest_supabase import ...` → `from cascade_ingest.ingest_supabase import ...`
- `from cascade_api.permissions import ...` → `from cascade_ingest.permissions import ...`
- `from cascade_api.consent import ...` → `from cascade_ingest.consent import ...`
- `from cascade_api.importers.chatgpt import ...` → `from cascade_ingest.importers.chatgpt import ...`
- `from cascade_api.importers.google_takeout import ...` → `from cascade_ingest.importers.google_takeout import ...`

**Step 4: Update `cascade-api/cascade_api/permissions.py`**

The existing `permissions.py` in `cascade-api` has `filter_by_permission` which stays there (it depends on `SearchResult`), but `classify_sensitivity` and the source sets now come from `cascade-ingest`. Update it to re-export from `cascade_ingest`:

```python
from cascade_memory import SearchResult
from cascade_ingest.consent import get_consent, ConsentConfig, extract_source_from_memory_type
from cascade_ingest.permissions import PRIVATE_SOURCES, PUBLIC_SOURCES, classify_sensitivity

# Re-export for backward compat within cascade-api
__all__ = ["classify_sensitivity", "PRIVATE_SOURCES", "PUBLIC_SOURCES", "filter_by_permission"]


def filter_by_permission(
    results: list[SearchResult],
    context: str,
    tenant_id: str | None = None,
) -> list[SearchResult]:
    if context == "dm_stranger":
        return []
    if context == "dm_owner":
        return results

    consent = get_consent(tenant_id) if tenant_id else ConsentConfig()
    filtered = []
    for r in results:
        source = extract_source_from_memory_type(r.memory.memory_type)
        if consent.is_public(source, r.memory.tags):
            filtered.append(r)
    return filtered
```

**Step 5: Delete the now-redundant files from `cascade-api`**

```bash
rm cascade-api/cascade_api/ingest.py
rm cascade-api/cascade_api/ingest_supabase.py
rm cascade-api/cascade_api/consent.py
rm -r cascade-api/cascade_api/importers/
```

**Step 6: Reinstall `cascade-api` to pick up the new dep**

```bash
cd cascade-api
pip install -e ".[dev]"
```

**Step 7: Run `cascade-api` tests to verify nothing broke**

```bash
cd cascade-api
pytest -v
```

Expected: All existing tests PASSED

**Step 8: Commit**

```bash
git add cascade-api/
git commit -m "refactor(cascade-api): consume cascade-ingest instead of owning ingest logic"
```

---

### Task 8: Final verification

**Step 1: Run all tests across both packages**

```bash
cd cascade-ingest && pytest -v
cd ../cascade-api && pytest -v
```

Expected: All PASSED in both packages

**Step 2: Verify the public API works end-to-end**

```python
# Quick smoke test in a Python shell
from cascade_ingest import ingest_persona, ConsentConfig, classify_sensitivity
from cascade_ingest.importers.chatgpt import parse_chatgpt_export
from cascade_ingest.importers.google_takeout import load_takeout_zip

record = {"source": "bank", "tags": []}
assert classify_sensitivity(record) == "private"
print("cascade-ingest smoke test passed")
```

**Step 3: Verify the package builds cleanly**

```bash
cd cascade-ingest
pip install build
python -m build --sdist
```

Expected: `Successfully built cascade_ingest-0.1.0.tar.gz`

**Step 4: Commit if any fixes were needed**

```bash
git add -A
git commit -m "fix(cascade-ingest): address any final issues from verification"
```
