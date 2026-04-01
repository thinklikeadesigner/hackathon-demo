# cascade-ingest — Design Document

**Date:** 2026-03-31
**Status:** Approved

---

## Problem

The ingestion and import logic for Cascade Memory lives inside `cascade-api`, a deployable product server. This makes it inaccessible to developers who want to build their own agent loops on top of `cascade-memory`. The vision is for Cascade to be a memory protocol any agent can plug into — that requires the data-in layer to be a standalone, installable library.

---

## Solution

Extract ingestion logic from `cascade-api` into a new PyPI package: `cascade-ingest`.

`cascade-ingest` is the bridge between real-world personal data exports and the Cascade Portable Memory Format. It handles:

- **JSONL persona ingestion** — the hackathon dataset format, with sensitivity classification, embedding, cross-reference linking, and semantic similarity linking
- **Real-world importers** — ChatGPT `conversations.json`, Google Takeout (`.zip`, `.ics`, `.mbox`)
- **Supabase ingestion** — pull goals, tasks, adaptations, tracker entries from a Cascade Supabase deployment (optional dep)
- **Consent configuration** — `ConsentConfig` and per-source sharing levels travel with the data
- **Sensitivity classification** — stamps each memory with `public_*` or `private_*` type at ingest time

---

## Package Structure

```
cascade-ingest/
├── pyproject.toml
├── README.md
└── cascade_ingest/
    ├── __init__.py              # public API: ingest_persona, ConsentConfig, classify_sensitivity
    ├── ingest.py                # JSONL persona ingestion + cross-source linking
    ├── permissions.py           # classify_sensitivity, PRIVATE_SOURCES, PUBLIC_SOURCES
    ├── consent.py               # ConsentConfig, get_consent, set_consent, SENSITIVE_TAGS
    └── importers/
        ├── __init__.py
        ├── chatgpt.py           # parse_chatgpt_export, load_chatgpt_file
        └── google_takeout.py    # parse_mbox, parse_ics, load_takeout_directory, load_takeout_zip
```

`ingest_supabase.py` is included in the package but only usable when the `supabase` optional dep is installed.

---

## Dependencies

```toml
[project]
dependencies = [
    "cascade-memory>=0.1.0",
]

[project.optional-dependencies]
supabase = [
    "supabase>=2.12.0",
]
```

Install options:
- `pip install cascade-ingest` — JSONL + ChatGPT + Google Takeout importers
- `pip install cascade-ingest[supabase]` — adds Supabase ingestion

---

## Public API Surface

```python
from cascade_ingest import ingest_persona, ConsentConfig, classify_sensitivity
from cascade_ingest.importers.chatgpt import load_chatgpt_file
from cascade_ingest.importers.google_takeout import load_takeout_zip

# Optional (requires cascade-ingest[supabase])
from cascade_ingest.ingest_supabase import ingest_from_supabase
```

---

## Repo Layout After Extraction

```
hackathon-demo/
├── cascade-api/         # Product server — depends on cascade-ingest
├── cascade-ingest/      # New: ingestion library (this package)
└── docs/plans/
```

`cascade-api` is updated to depend on `cascade-ingest` locally:

```toml
# cascade-api/pyproject.toml
dependencies = [
    "cascade-ingest @ ../cascade-ingest",
    ...
]
```

All imports in `cascade-api` that reference `cascade_api.ingest`, `cascade_api.permissions`, `cascade_api.consent`, and `cascade_api.importers` are updated to `cascade_ingest.*`.

---

## What Stays in `cascade-api`

- FastAPI routes and the full HTTP server
- LangGraph agent loop
- Telegram bot coordinator
- LLM synthesis and Ollama embedder/extractor
- Session management, observability, Stripe/payment logic

These are application-layer concerns, not library concerns.

---

## Portable Memory Format Compatibility

`cascade-ingest` produces data compatible with the Portable Memory Format v0.1. The consent config produced by `ingest_persona` is included in exports and can be loaded by `cascade-explorer` (future package).

---

## Out of Scope

- `cascade-explorer` (graph visualization) — separate package, future work
- Publishing to PyPI — design covers local extraction; PyPI release is a follow-on step
- New importers (Apple Health, Fitbit, banking CSV) — future additions
