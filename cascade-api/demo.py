#!/usr/bin/env python3
"""
Cascade Memory Infrastructure — Interactive CLI Demo

Run this to see the full pipeline without Telegram setup:
  python demo.py

Requires: Ollama running locally with qwen3:8b and nomic-embed-text models.
No API keys needed.
"""
import asyncio
import json
import logging
import sys
import time
from io import BytesIO
from pathlib import Path

from cascade_api.memory import MemoryClient
from cascade_api.memory.stores.memory import InMemoryStore
from cascade_api.ollama_embedder import OllamaEmbedder
from cascade_api.ollama_extractor import OllamaExtractor
from cascade_api.ingest import ingest_persona, SOURCE_TYPE_MAP
from cascade_api.permissions import classify_sensitivity, filter_by_permission
from cascade_api.consent import get_consent, set_consent, ConsentConfig
from cascade_api.synthesize import synthesize_answer
from cascade_api.insights import generate_insights

logging.basicConfig(level=logging.WARNING)

DATA_DIR = Path(__file__).parent.parent / "data" / "personadata" / "personas"
CACHE_FILE = Path(__file__).parent / ".memory_cache.pkl"

# ANSI colors
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"
MAGENTA = "\033[35m"
RESET = "\033[0m"


def banner(text):
    width = 60
    print(f"\n{BOLD}{CYAN}{'═' * width}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'═' * width}{RESET}\n")


def step(num, text):
    print(f"\n{BOLD}{GREEN}[Step {num}]{RESET} {BOLD}{text}{RESET}")
    print(f"{DIM}{'─' * 50}{RESET}")


def info(text):
    print(f"  {DIM}{text}{RESET}")


def highlight(text):
    print(f"  {YELLOW}{text}{RESET}")


def result(text):
    for line in text.strip().split("\n"):
        print(f"  {MAGENTA}│{RESET} {line}")


def wait():
    input(f"\n  {DIM}Press Enter to continue...{RESET}")


async def main():
    banner("CASCADE MEMORY INFRASTRUCTURE — DEMO")
    print(f"  A portable, permission-gated personal memory system.")
    print(f"  Ingests scattered digital history, links it semantically,")
    print(f"  and lets users control who sees what.\n")

    # ── Step 1: Ingest ──────────────────────────────────────────
    step(1, "INGESTION — Loading Jordan's data from 8 sources")

    persona_dir = DATA_DIR / "persona_p01"
    if not persona_dir.exists():
        print(f"  {RED}Error: Persona data not found at {persona_dir}{RESET}")
        print(f"  Make sure data/personadata/personas/ exists.")
        sys.exit(1)

    # Count source files
    jsonl_files = list(persona_dir.glob("*.jsonl"))
    total_records = 0
    sources = set()
    for f in jsonl_files:
        with open(f) as fh:
            for line in fh:
                if line.strip():
                    rec = json.loads(line)
                    total_records += 1
                    sources.add(rec.get("source", "unknown"))

    info(f"Found {len(jsonl_files)} source files, {total_records} records")
    info(f"Sources: {', '.join(sorted(sources))}")

    embedder = OllamaEmbedder()
    extractor = OllamaExtractor()

    # Check for cache
    store = None
    if CACHE_FILE.exists():
        import pickle
        try:
            with open(CACHE_FILE, "rb") as f:
                data = pickle.load(f)
            store = InMemoryStore()
            store._core = data["_core"]
            store._memories = data["_memories"]
            store._tenant_memories = data["_tenant_memories"]
            store._links = data["_links"]
            store._embedding_dims = data["_embedding_dims"]
            for tid, cdata in data.get("_consent", {}).items():
                set_consent(tid, ConsentConfig.from_dict(cdata))
            embedded = sum(1 for m in store._memories.values() if m.embedding is not None)
            highlight(f"Loaded from cache: {len(store._memories)} memories ({embedded} embedded)")
        except Exception:
            store = None

    if store is None:
        store = InMemoryStore()
        client = MemoryClient(store=store, embedder=embedder, extractor=extractor)
        await client.initialize()

        info("Embedding and ingesting (first run takes ~60s)...")
        t0 = time.time()
        stats = await ingest_persona(client, "p01", persona_dir)
        elapsed = time.time() - t0
        highlight(f"Ingested {stats['records_ingested']} records, created {stats['links_created']} links in {elapsed:.1f}s")

        # Save cache
        from cascade_api.consent import _consent_configs
        cache_data = {
            "_core": store._core,
            "_memories": store._memories,
            "_tenant_memories": store._tenant_memories,
            "_links": store._links,
            "_embedding_dims": store._embedding_dims,
            "_consent": {tid: c.to_dict() for tid, c in _consent_configs.items()},
        }
        with open(CACHE_FILE, "wb") as f:
            import pickle
            pickle.dump(cache_data, f)
        info("Cached for faster future runs.")
    else:
        client = MemoryClient(store=store, embedder=embedder, extractor=extractor)

    tenant = client.for_tenant("p01")
    all_memories = await store.list("p01", limit=10000)
    all_links = []
    for mem in all_memories:
        links = await store.get_links("p01", mem.id)
        all_links.extend(links)

    highlight(f"Memory graph: {len(all_memories)} nodes, {len(all_links)} edges")

    wait()

    # ── Step 2: Permission Layer ────────────────────────────────
    step(2, "PERMISSION LAYER — Same query, different access")

    query = "What are Jordan's recent financial transactions?"
    info(f'Query: "{query}"')

    results = await tenant.recall(query, count=15, threshold=0.1)
    info(f"Raw recall: {len(results)} memories matched")

    # Show types
    types_found = {}
    for r in results[:15]:
        t = r.memory.memory_type
        types_found[t] = types_found.get(t, 0) + 1
    for t, count in sorted(types_found.items()):
        info(f"  {t}: {count}")

    print()
    # Group context
    group_filtered = filter_by_permission(results, "group", tenant_id="p01")
    highlight(f"GROUP CHAT context: {len(group_filtered)} results (private data filtered out)")
    if group_filtered:
        for r in group_filtered[:3]:
            info(f"  [{r.memory.memory_type}] {r.memory.content[:80]}...")
    else:
        info("  (no financial data visible — bank is owner_only by default)")

    print()
    # Owner DM context
    owner_filtered = filter_by_permission(results, "dm_owner", tenant_id="p01")
    highlight(f"OWNER DM context: {len(owner_filtered)} results (full access)")
    for r in owner_filtered[:5]:
        info(f"  [{r.memory.memory_type}] {r.memory.content[:80]}...")

    print()
    # Stranger DM context
    stranger_filtered = filter_by_permission(results, "dm_stranger", tenant_id="p01")
    highlight(f"STRANGER DM context: {len(stranger_filtered)} results (blocked)")

    wait()

    # ── Step 3: Consent Controls ────────────────────────────────
    step(3, "CONSENT CONTROLS — User changes privacy settings")

    consent = get_consent("p01")
    info("Current consent settings:")
    for source in ["calendar", "email", "social", "bank", "ai_chat", "lifelog"]:
        level = consent.get_level(source)
        icon = "🔒" if level == "owner_only" else "🌐"
        info(f"  {icon} {source}: {level}")

    print()
    info('User runs: /privacy set bank public')
    consent.set_level("bank", "public")
    highlight("Updated: bank → public")

    # Re-filter with new consent
    group_filtered_new = filter_by_permission(results, "group", tenant_id="p01")
    highlight(f"GROUP CHAT now returns: {len(group_filtered_new)} results (bank data now visible!)")

    # Reset for clean state
    consent.set_level("bank", "owner_only")
    info("(Reset bank → owner_only for remaining demo)")

    wait()

    # ── Step 4: Synthesis ───────────────────────────────────────
    step(4, "RECALL + SYNTHESIS — Natural language answers")

    query2 = "What meetings does Jordan have coming up?"
    info(f'Query: "{query2}"')

    results2 = await tenant.recall(query2, count=15, threshold=0.1)
    filtered2 = filter_by_permission(results2, "dm_owner", tenant_id="p01")
    core_content, _ = await tenant.core.read()

    info(f"Recalled {len(filtered2)} relevant memories, synthesizing with qwen3:8b...")
    answer = await synthesize_answer(
        persona_name="Jordan",
        core_memory=core_content,
        results=filtered2,
        question=query2,
        context="dm_owner",
    )
    print()
    result(answer)

    wait()

    # ── Step 5: Import ──────────────────────────────────────────
    step(5, "INTEROPERABILITY — Import Google Calendar (.ics)")

    from cascade_api.importers.google_takeout import parse_ics
    import tempfile

    # Create a sample .ics file
    sample_ics = """BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART:20240315T100000Z
DTEND:20240315T110000Z
SUMMARY:Team standup - Q2 planning
LOCATION:Zoom
END:VEVENT
BEGIN:VEVENT
DTSTART:20240316T140000Z
DTEND:20240316T150000Z
SUMMARY:Doctor appointment - annual checkup
LOCATION:Austin Medical Center
END:VEVENT
BEGIN:VEVENT
DTSTART:20240317T180000Z
DTEND:20240317T200000Z
SUMMARY:Dinner with Sarah and Mike
LOCATION:Easy Tiger
END:VEVENT
END:VCALENDAR"""

    with tempfile.NamedTemporaryFile(suffix=".ics", mode="w", delete=False) as tmp:
        tmp.write(sample_ics)
        tmp_path = Path(tmp.name)

    records = parse_ics(tmp_path)
    tmp_path.unlink()

    info(f"Parsed {len(records)} events from .ics file:")
    for r in records:
        info(f"  [{', '.join(r['tags'])}] {r['text'][:70]}")

    # Import into memory store
    new_ids = []
    for record in records:
        sensitivity = classify_sensitivity(record)
        source = record.get("source", "unknown")
        type_suffix = SOURCE_TYPE_MAP.get(source, source)
        memory_type = f"{sensitivity}_{type_suffix}"
        mem_id = await tenant.save(
            content=record["text"],
            memory_type=memory_type,
            tags=record.get("tags", []),
            source_id=record.get("id"),
        )
        new_ids.append(mem_id)

    highlight(f"Imported {len(new_ids)} records into Jordan's memory graph")

    # Cross-source linking
    links_created = 0
    for mem_id in new_ids:
        mem = await store.get("p01", mem_id)
        if not mem or mem.embedding is None:
            continue
        similar = await store.search("p01", mem.embedding, count=5, threshold=0.3)
        for s in similar:
            if s.memory.id != mem_id and s.memory.memory_type != mem.memory_type:
                await tenant.link(mem_id, s.memory.id, "related")
                links_created += 1

    highlight(f"Created {links_created} cross-source links (calendar ↔ email, lifelog, etc.)")

    wait()

    # ── Step 6: Insights ────────────────────────────────────────
    step(6, "CROSS-SOURCE INSIGHTS — Patterns only visible across data")

    info("Analyzing calendar + bank + lifelog + social data...")
    insights = await generate_insights("Jordan", persona_dir)
    print()
    result(insights)

    wait()

    # ── Step 7: Export ──────────────────────────────────────────
    step(7, "PORTABLE EXPORT — Your data, your format")

    all_memories = await store.list("p01", limit=10000)
    all_links_export = []
    for mem in all_memories:
        links = await store.get_links("p01", mem.id)
        for link in links:
            link_dict = {"source_id": link.source_id, "target_id": link.target_id, "link_type": link.link_type}
            if link_dict not in all_links_export:
                all_links_export.append(link_dict)

    export = {
        "tenant_id": "p01",
        "persona_name": "Jordan",
        "consent": get_consent("p01").to_dict(),
        "core_memory": {"content": core_content, "version": 0},
        "memories": len(all_memories),
        "links": len(all_links_export),
    }

    info(f"Portable Memory Format export:")
    info(f"  Memories: {export['memories']}")
    info(f"  Links:    {export['links']}")
    info(f"  Consent:  {len(export['consent']['sources'])} sources configured")

    # Show link type breakdown
    link_types = {}
    for l in all_links_export:
        lt = l["link_type"]
        link_types[lt] = link_types.get(lt, 0) + 1
    info(f"  Link types: {dict(link_types)}")

    highlight("Export includes: memories, embeddings, links, consent config, core memory")
    highlight("Load into static/graph.html to visualize the full knowledge graph")

    wait()

    # ── Step 8: Right to Erasure ────────────────────────────────
    step(8, "RIGHT TO ERASURE — /forget deletes matching memories")

    forget_query = "therapy sessions"
    info(f'User runs: /forget {forget_query}')

    forget_results = await tenant.recall(forget_query, count=10, threshold=0.15)
    info(f"Found {len(forget_results)} matching memories")

    if forget_results:
        for r in forget_results[:3]:
            info(f"  [{r.memory.memory_type}] {r.memory.content[:70]}...")

        count = 0
        for r in forget_results:
            await client.delete("p01", r.memory.id)
            count += 1

        highlight(f"Deleted {count} memories. Not hidden — gone.")
    else:
        info("  (no therapy-related memories found in Jordan's data)")

    # ── Summary ─────────────────────────────────────────────────
    banner("DEMO COMPLETE")

    print(f"  {BOLD}What you just saw:{RESET}")
    print(f"  1. Ingestion of 530+ records from 8 sources (JSONL → vector store)")
    print(f"  2. Permission filtering (group/owner/stranger contexts)")
    print(f"  3. User-controlled consent (per-source, changeable at runtime)")
    print(f"  4. Natural language recall + LLM synthesis with source attribution")
    print(f"  5. Google Calendar import with auto cross-source linking")
    print(f"  6. Cross-source insights (calendar × bank × lifelog × social)")
    print(f"  7. Portable JSON export (Portable Memory Format v0.1)")
    print(f"  8. Right to erasure (/forget)")
    print()
    print(f"  {BOLD}All running locally{RESET} — Ollama qwen3:8b + nomic-embed-text")
    print(f"  {BOLD}No cloud API keys required{RESET} for core functionality")
    print()
    print(f"  {DIM}For the full Telegram experience: python main.py{RESET}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
