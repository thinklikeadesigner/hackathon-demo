# Cascade Memory Infrastructure

**Team:** Cascade | **Track:** Track 1 — Memory Infrastructure

> A portable, permission-gated personal memory system that ingests scattered digital history, links it semantically across sources, and lets users control who sees what — demonstrated through multi-persona Telegram bots.

---

## **[Live Graph Visualization](https://thinklikeadesigner.github.io/hackathon-demo/)** | **[Demo Video (3 min)](https://www.youtube.com/watch?v=SZO1RZ4dV8s)**


---

## What It Does

Cascade Memory takes the data a person could export today — emails, calendar events, bank transactions, AI conversations, social posts, lifelogs, file metadata — and turns it into a unified, queryable knowledge graph they actually own. Each memory is classified by sensitivity, embedded for semantic search, and linked to related memories across sources. A permission layer controls access: your therapist notes never leak into group chat answers.

<img width="700" alt="Knowledge graph visualization — 530 memories from 8 sources with consent controls and cross-source links" src="https://github.com/user-attachments/assets/c4e2e875-923b-469c-b8f4-a77e666bb2ce" />

The demo runs 4 Telegram bots, each representing a different person's memory. Ask Jordan about his calendar and the bot searches his memory, filters by permission context, and synthesizes an answer. Tell the "You" bot something new and it extracts facts, embeds them, auto-links them to related memories, and persists everything — building a living knowledge graph from conversation.

---


## Quick Start

```bash
# Clone
git clone git@github.com:thinklikeadesigner/hackathon-demo.git
cd hackathon-demo/cascade-api

# Install uv (fast Python package manager)
pip install uv

# Create and activate a virtual environment
uv venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate          # Windows

# Install project dependencies
uv pip install -e ".[dev]"

# Install Ollama models (local inference — no API keys needed for core demo)
ollama pull qwen3:8b
ollama pull nomic-embed-text

# Persona datasets are included in data/personadata/personas/

# Run the CLI demo (no Telegram setup needed — just Ollama)
python demo.py
```

### CLI Demo Options

```bash
python demo.py          # Interactive — press Enter between steps
python demo.py --auto   # Auto-advance with pauses
python demo.py --fast   # Skip LLM synthesis (quick test run)
```

The demo walks through 8 stages: ingestion, permission filtering, consent controls, LLM synthesis, Google Calendar + ChatGPT import, cross-source insights, portable export, and right to erasure.

---

## Tech Stack & Architecture

<img width="669" height="457" alt="Screenshot 2026-03-10 at 2 15 44 AM" src="https://github.com/user-attachments/assets/e88da642-d455-48b3-b0a6-6c3146fd3ccb" />

**Runtime:** Python 3.12, fully local (Ollama) — no cloud API keys required for core demo

| Component | Technology |
|-----------|-----------|
| LLM (synthesis + extraction) | Ollama / qwen3:8b (local) |
| Embeddings | Ollama / nomic-embed-text (768 dims, local) |
| Vector store | InMemoryStore with cosine similarity + pickle cache |
| Bot framework | python-telegram-bot 21+ |
| Graph visualization | D3.js force-directed graph |
| Data format | JSONL (hackathon dataset) + Portable Memory Format JSON |
| Optional cloud store | Supabase + pgvector (production path) |

---

## Datasets

**Primary:** Hackathon-provided synthetic persona datasets (5 personas, 8 sources each)
- Source: [Google Drive — Data Portability Hackathon 2026](https://drive.google.com/drive/folders/1TEWhdzff-FgkDNY-53IDXIWaPZQ7_5F3)
- Personas used: **p01 (Jordan Lee)**, **p02 (Maya Patel)**, **p05 (Theo Nakamura)**
- ~530 records per persona across: lifelog, email, calendar, social posts, transactions, AI conversations, file metadata
- Each record includes `refs` for cross-source linking

**Secondary:** Live Cascade user data from Supabase (goals, tasks, tracker entries, adaptations) ingested into the "You" bot's memory.

---

## How It Works

### 1. Ingestion Pipeline

Each persona's JSONL files are loaded, classified by sensitivity (`public_email`, `private_finance`, etc.), embedded via nomic-embed-text, and saved to the memory store. Cross-references from the `refs` field create explicit `cross_reference` links. A second pass samples memories and creates semantic `related` links across different source types (e.g., a calendar meeting linked to the email that scheduled it).

<img width="530" alt="Ingestion — 530 records from 8 sources embedded and cross-linked" src="https://github.com/user-attachments/assets/dda27f59-9cc1-400d-84f4-9abb1fc9a44d" />

### 2. Permission Layer

Every memory gets a type like `private_ai_chat` or `public_social`. When a query comes in, the system checks context:
- **Owner DM**: Full access to all memories
- **Group chat**: Only `public_*` memories returned
- **Stranger DM**: Blocked entirely

This means Jordan's therapy notes and bank statements never surface in group conversations — only his public calendar events and social posts.

<img width="476" alt="Telegram group chat — all 3 bots refuse to share financial data in public" src="https://github.com/user-attachments/assets/a6c659b3-6cba-4427-b590-023dd3bbcb8f" />

### 3. Consent Controls

Users change privacy settings at runtime with `/privacy set <source> <level>`. Sensitive tags (therapy, salary, medical) are always private regardless of source setting.

<img width="700" alt="Consent dashboard — per-source privacy controls" src="https://github.com/user-attachments/assets/b4cbba30-b20f-4031-84d5-731a6da2bc9a" />

### 4. Recall + Synthesis

Questions are embedded and matched against the memory store using cosine similarity, weighted by decay score and confidence. The top results are passed to a local LLM (qwen3:8b) along with the persona's core memory profile to synthesize a natural answer. Source attribution is included (calendar, email, lifelog, etc.).

<img width="527" alt="Natural language answer with source attribution" src="https://github.com/user-attachments/assets/afab999e-738b-49a4-ac4b-aafdb3909684" />

### 5. Interoperability — Import from Anywhere

Cascade imports data from multiple real-world export formats: Google Takeout (`.zip`, `.ics`, `.mbox`) and ChatGPT (`conversations.json`). Imported records are automatically classified, embedded, and cross-linked to existing memories.

<img width="486" alt="Telegram — importing a 6.6MB Google Takeout zip: 486 records imported, 11 cross-source links created" src="https://github.com/user-attachments/assets/55cc2760-9bdd-4602-92f3-2d9cef179a60" />

### 6. Memory Extraction + Auto-Linking

When the owner tells the bot something new, the conversation is sent to an extractor that pulls out facts, preferences, patterns, and goals. Each extracted memory is embedded, saved, and automatically linked to similar existing memories. The graph grows with every conversation.

### 7. Portable Export

`/export` dumps the full memory graph as JSON: core memory, all archival memories with metadata, and all links. This is the **Portable Memory Format** — a self-contained file that can be loaded into the graph visualizer or imported into another system.

<img width="526" alt="Telegram /export — full memory graph as portable JSON file" src="https://github.com/user-attachments/assets/5fc20789-02e4-4746-83d2-1b91f7890d16" />

---

## Portable Memory Format (v0.1)

```json
{
  "tenant_id": "p01",
  "persona_name": "Jordan",
  "core_memory": { "content": "## Profile\n- Name: Jordan Lee\n...", "version": 7 },
  "memories": [
    {
      "id": "uuid",
      "content": "Meeting with design team to review Q2 roadmap",
      "memory_type": "public_calendar",
      "tags": ["work", "meetings"],
      "confidence": 1.0,
      "decay_score": 0.95,
      "source_id": "cal_0042",
      "created_at": "2024-01-08T01:40:00-05:00"
    }
  ],
  "links": [
    { "source_id": "uuid1", "target_id": "uuid2", "link_type": "related" }
  ]
}
```

Link types: `cross_reference`, `related`, `part_of`, `supports`, `contradicts`, `supersedes`

---

## Known Limitations & Next Steps

### Limitations
- **In-memory store**: Demo uses pickle-cached InMemoryStore. Not suitable for production at scale (Supabase + pgvector store exists but wasn't used for the demo to keep it fully local).
- **Embedding quality**: nomic-embed-text is good but not state-of-the-art. Cross-source linking depends heavily on embedding quality.
- **No contradiction detection**: The extractor protocol supports `check_contradictions()` but it's not wired into the local Ollama pipeline yet.
- **Single-machine**: All 4 bots run in one process. Production would need separate workers.

### Next Steps
- Add contradiction detection during extraction (flag conflicting memories)
- Implement memory decay cron job (exponential decay formula exists, just needs scheduling)
- Production deployment with Supabase store + pgvector HNSW index
- Portable Memory Format spec formalization for cross-system interoperability
- Additional importers: Apple Health, Fitbit, banking CSV exports

---

## Project Structure

```
cascade-api/
├── main.py                          # Entry point: ingest, cache, run bots
├── demo.py                          # CLI demo (no Telegram needed)
├── cascade_api/
│   ├── config.py                    # Bot configs (name, tenant, token)
│   ├── handlers.py                  # Message handler (recall → filter → synthesize → extract)
│   ├── synthesize.py                # LLM answer synthesis (Ollama)
│   ├── permissions.py               # Sensitivity classification + access control
│   ├── consent.py                   # Per-tenant, per-source sharing levels
│   ├── ingest.py                    # JSONL persona ingestion + cross-source linking
│   ├── ingest_supabase.py           # Supabase data ingestion (goals, tasks, tracker)
│   ├── multi_bot.py                 # Multi-persona Telegram bot coordinator
│   ├── ollama_embedder.py           # Local embedding via Ollama/nomic-embed-text
│   ├── ollama_extractor.py          # Local memory extraction via Ollama/qwen3:8b
│   ├── insights.py                  # Cross-source pattern analysis engine
│   ├── importers/
│   │   ├── chatgpt.py               # ChatGPT conversations.json parser
│   │   └── google_takeout.py        # Google Takeout (.zip, .ics, .mbox) parser
│   └── memory/
│       ├── client.py                # MemoryClient — save, recall, extract, link, decay
│       ├── core.py                  # CoreMemory — always-in-context markdown doc
│       ├── models.py                # MemoryRecord, MemoryLink, SearchResult, ExtractedMemory
│       ├── decay.py                 # Exponential decay scoring
│       ├── protocols/               # Pluggable interfaces (Embedder, Store, Extractor)
│       ├── stores/memory.py         # InMemoryStore (cosine similarity search)
│       ├── stores/supabase.py       # SupabaseStore (pgvector, production)
│       ├── embedders/               # Gemini, Fake embedder implementations
│       └── extractors/anthropic.py  # Claude-based extraction (production)
├── static/
│   └── graph.html                   # D3.js Obsidian-style memory graph visualizer
└── data/personadata/personas/       # Hackathon synthetic persona datasets
```

---

## Team

| Name | Role | Contact |
|------|------|---------|
| Rebecca Burch | Solo Engineer | [LinkedIn](https://www.linkedin.com/in/rebecca-burch/) |

---

## Running the Telegram Bots

To run the full multi-bot system with 4 personas:

```bash
cp .env.example .env
# Edit .env with your Telegram bot tokens (see below)
python main.py
```

### Required Environment Variables (Telegram only)

```bash
# Telegram bots (create via @BotFather)
TELEGRAM_BOT_TOKEN_JORDAN=...   # Persona p01
TELEGRAM_BOT_TOKEN_MAYA=...     # Persona p02
TELEGRAM_BOT_TOKEN_THEO=...     # Persona p05
TELEGRAM_BOT_TOKEN_YOU=...      # Your personal bot
TELEGRAM_OWNER_CHAT_ID=...      # Your Telegram user ID

# Optional: Supabase (for enriched export with goals/tasks)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
```

### Reproducing the Telegram Demo

1. Create 4 Telegram bots via [@BotFather](https://t.me/BotFather) and add tokens to `.env`
2. Get your Telegram chat ID (message [@userinfobot](https://t.me/userinfobot))
3. Persona datasets are already included in `data/personadata/personas/`
4. Run `python main.py` — first run takes ~60s to ingest and embed all records
5. Message any bot in Telegram. Try:
   - Ask Jordan: *"What meetings do I have this week?"*
   - Ask Maya: *"How am I feeling about residency?"*
   - Tell You bot: *"I just signed a new client today"*
   - Run `/privacy` to view/change per-source consent settings
   - Run `/import` and attach a file (`.ics`, `.mbox`, `.zip`, or ChatGPT `conversations.json`)
   - Run `/forget therapy sessions` to exercise right-to-erasure
   - Run `/export` in DM with any bot to get the full memory JSON
   - Run `/insights` to generate cross-source pattern analysis
6. Open `static/graph.html` in a browser and load the exported JSON to visualize the memory graph

---

## License

MIT
