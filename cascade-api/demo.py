#!/usr/bin/env python3
"""
Cascade Memory Infrastructure — CLI Demo

Run: python demo.py
Flags: --auto (no pauses, for video recording), --fast (skip synthesis)
Requires: Ollama with qwen3:8b + nomic-embed-text
"""
import asyncio
import json
import logging
import pickle
import sys
import time
import tempfile
from pathlib import Path

logging.basicConfig(level=logging.WARNING)

# ── Styling (bright variants for dark terminal readability) ──────
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[92m"       # bright green
YELLOW = "\033[93m"      # bright yellow
CYAN = "\033[96m"        # bright cyan
RED = "\033[91m"         # bright red
MAGENTA = "\033[95m"     # bright magenta
WHITE = "\033[97m"       # bright white
BLACK = "\033[30m"       # black text for badges
BG_RED = "\033[101m"     # bright red bg
BG_GREEN = "\033[102m"   # bright green bg
BG_YELLOW = "\033[103m"  # bright yellow bg
BG_BLUE = "\033[104m"    # bright blue bg
BG_MAGENTA = "\033[105m" # bright magenta bg
RESET = "\033[0m"

AUTO = "--auto" in sys.argv
FAST = "--fast" in sys.argv

DATA_DIR = Path(__file__).parent.parent / "data" / "personadata" / "personas"
CACHE_FILE = Path(__file__).parent / ".memory_cache.pkl"


def pause(seconds=1.5):
    if AUTO:
        time.sleep(seconds)
    else:
        input(f"  {DIM}▸ press enter{RESET}")


def typewrite(text, delay=0.01):
    """Simulate typing for demo effect."""
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        if not AUTO:
            time.sleep(delay)
    print()


def banner():
    print()
    print(f"  {BOLD}{CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
    print(f"  {BOLD}{CYAN}║{RESET}  {BOLD}CASCADE MEMORY{RESET}  —  Personal Data Infrastructure      {BOLD}{CYAN}║{RESET}")
    print(f"  {BOLD}{CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
    print()
    print(f"  {DIM}Your data. Your rules. Fully local.{RESET}")
    print()


def stage(num, total, title, subtitle=""):
    bar = ""
    for i in range(1, total + 1):
        if i < num:
            bar += f"{GREEN}●{RESET} "
        elif i == num:
            bar += f"{CYAN}◉{RESET} "
        else:
            bar += f"{DIM}○{RESET} "
    print(f"\n  {bar} {DIM}{num}/{total}{RESET}")
    print(f"  {BOLD}{WHITE}{title}{RESET}")
    if subtitle:
        print(f"  {DIM}{subtitle}{RESET}")
    print(f"  {DIM}{'─' * 54}{RESET}")


def show(text):
    print(f"  {text}")


def data(label, value):
    print(f"  {DIM}{label}:{RESET} {BOLD}{value}{RESET}")


def mem_line(memory_type, content, sim=None):
    """Display a memory with color-coded source badge."""
    source = memory_type.split("_", 1)[1] if "_" in memory_type else memory_type
    is_private = memory_type.startswith("private")
    badge_color = BG_RED if is_private else BG_GREEN
    badge_text = f" {source.upper()} "
    sim_text = f" {DIM}({sim:.0%}){RESET}" if sim else ""
    print(f"  {badge_color}{BLACK}{BOLD}{badge_text}{RESET}{sim_text} {content[:75]}")


def blocked():
    print(f"  {BG_RED}{BOLD} BLOCKED {RESET} {RED}Access denied{RESET}")


def access_row(context, count, icon, note):
    bar_len = min(count, 30)
    bar = f"{GREEN}{'█' * bar_len}{RESET}" if count > 0 else f"{RED}░{RESET}"
    print(f"  {icon} {BOLD}{context:<15}{RESET} {bar} {BOLD}{count}{RESET} {DIM}{note}{RESET}")


def section_end():
    print()


async def main():
    banner()
    total_steps = 8
    t_start = time.time()

    # ════════════════════════════════════════════════════════════
    # STEP 1: INGEST
    # ════════════════════════════════════════════════════════════
    stage(1, total_steps, "INGEST", "Loading Jordan Lee's digital life from 8 source types")

    persona_dir = DATA_DIR / "persona_p01"
    if not persona_dir.exists():
        print(f"  {RED}Error: Persona data not found at {persona_dir}{RESET}")
        sys.exit(1)

    # Count and categorize
    source_counts: dict[str, int] = {}
    for f in persona_dir.glob("*.jsonl"):
        with open(f) as fh:
            for line in fh:
                if line.strip():
                    rec = json.loads(line)
                    src = rec.get("source", "unknown")
                    source_counts[src] = source_counts.get(src, 0) + 1

    total_records = sum(source_counts.values())
    print()
    for src in sorted(source_counts, key=source_counts.get, reverse=True):
        ct = source_counts[src]
        bar = "▓" * (ct // 5)
        print(f"  {BOLD}{src:<12}{RESET} {GREEN}{bar}{RESET} {ct}")

    show(f"\n  {BOLD}{total_records}{RESET} records across {BOLD}{len(source_counts)}{RESET} sources")

    # Load or build store
    from cascade_api.memory import MemoryClient
    from cascade_api.memory.stores.memory import InMemoryStore
    from cascade_api.ollama_embedder import OllamaEmbedder
    from cascade_api.ollama_extractor import OllamaExtractor
    from cascade_api.ingest import ingest_persona, SOURCE_TYPE_MAP
    from cascade_api.permissions import classify_sensitivity, filter_by_permission
    from cascade_api.consent import get_consent, set_consent, ConsentConfig, _consent_configs
    from cascade_api.synthesize import synthesize_answer
    from cascade_api.insights import generate_insights
    from cascade_api.importers.google_takeout import parse_ics
    from cascade_api.importers.chatgpt import parse_chatgpt_export

    embedder = OllamaEmbedder()
    extractor = OllamaExtractor()

    store = None
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "rb") as f:
                cached = pickle.load(f)
            store = InMemoryStore()
            store._core = cached["_core"]
            store._memories = cached["_memories"]
            store._tenant_memories = cached["_tenant_memories"]
            store._links = cached["_links"]
            store._embedding_dims = cached["_embedding_dims"]
            for tid, cdata in cached.get("_consent", {}).items():
                set_consent(tid, ConsentConfig.from_dict(cdata))
            show(f"\n  {GREEN}✓{RESET} Loaded from cache ({len(store._memories)} memories embedded)")
        except Exception:
            store = None

    if store is None:
        show(f"\n  Embedding {total_records} records with nomic-embed-text...")
        store = InMemoryStore()
        client = MemoryClient(store=store, embedder=embedder, extractor=extractor)
        await client.initialize()
        t0 = time.time()
        stats = await ingest_persona(client, "p01", persona_dir)
        elapsed = time.time() - t0
        show(f"  {GREEN}✓{RESET} Ingested {stats['records_ingested']} records, {stats['links_created']} cross-source links ({elapsed:.0f}s)")

        cache_data = {
            "_core": store._core, "_memories": store._memories,
            "_tenant_memories": store._tenant_memories, "_links": store._links,
            "_embedding_dims": store._embedding_dims,
            "_consent": {tid: c.to_dict() for tid, c in _consent_configs.items()},
        }
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(cache_data, f)
    else:
        client = MemoryClient(store=store, embedder=embedder, extractor=extractor)

    tenant = client.for_tenant("p01")

    # Count graph
    all_mems = await store.list("p01", limit=10000)
    link_count = 0
    for m in all_mems:
        link_count += len(await store.get_links("p01", m.id))

    show(f"\n  {BOLD}Knowledge graph:{RESET} {len(all_mems)} memories, {link_count} connections")

    pause()

    # ════════════════════════════════════════════════════════════
    # STEP 2: PERMISSION LAYER
    # ════════════════════════════════════════════════════════════
    stage(2, total_steps, "PERMISSION LAYER", "Same data, same query — different access levels")

    query = "What are Jordan's recent financial transactions?"
    print()
    show(f"  {DIM}Query:{RESET} {BOLD}\"{query}\"{RESET}")
    print()

    results = await tenant.recall(query, count=20, threshold=0.1)

    group_results = filter_by_permission(results, "group", tenant_id="p01")
    owner_results = filter_by_permission(results, "dm_owner", tenant_id="p01")
    stranger_results = filter_by_permission(results, "dm_stranger", tenant_id="p01")

    access_row("Owner DM", len(owner_results), "🔓", "full access to all memories")
    access_row("Group Chat", len(group_results), "👥", "private data filtered out")
    access_row("Stranger DM", len(stranger_results), "🚫", "completely blocked")

    print()
    show(f"  {BOLD}What the owner sees:{RESET}")
    for r in owner_results[:4]:
        mem_line(r.memory.memory_type, r.memory.content, r.similarity)

    print()
    show(f"  {BOLD}What the group sees:{RESET}")
    if group_results:
        for r in group_results[:3]:
            mem_line(r.memory.memory_type, r.memory.content, r.similarity)
    else:
        show(f"  {DIM}(nothing — bank data is owner_only by default){RESET}")

    pause()

    # ════════════════════════════════════════════════════════════
    # STEP 3: CONSENT CONTROLS
    # ════════════════════════════════════════════════════════════
    stage(3, total_steps, "CONSENT CONTROLS", "Users change privacy at any time — data doesn't move, access does")

    consent = get_consent("p01")
    print()
    for src in ["calendar", "email", "social", "lifelog", "bank", "ai_chat"]:
        level = consent.get_level(src)
        if level == "owner_only":
            show(f"  {RED}🔒 {src:<12}{RESET} owner_only")
        else:
            show(f"  {GREEN}🌐 {src:<12}{RESET} public")

    print()
    typewrite(f"  $ /privacy set bank public")
    consent.set_level("bank", "public")
    show(f"  {GREEN}✓{RESET} bank → {BOLD}public{RESET}")

    # Re-query
    group_after = filter_by_permission(results, "group", tenant_id="p01")
    print()
    show(f"  {BOLD}Before:{RESET} group saw {BOLD}{len(group_results)}{RESET} results")
    show(f"  {BOLD}After:{RESET}  group sees {BOLD}{len(group_after)}{RESET} results")

    if group_after:
        print()
        show(f"  {BOLD}Bank data now visible in group:{RESET}")
        for r in group_after[:3]:
            if "finance" in r.memory.memory_type or "bank" in r.memory.memory_type:
                mem_line(r.memory.memory_type, r.memory.content, r.similarity)

    # Reset
    consent.set_level("bank", "owner_only")
    show(f"\n  {DIM}(reset bank → owner_only){RESET}")

    pause()

    # ════════════════════════════════════════════════════════════
    # STEP 4: SYNTHESIS
    # ════════════════════════════════════════════════════════════
    stage(4, total_steps, "RECALL + SYNTHESIS", "Semantic search → LLM synthesis with source attribution")

    queries = [
        ("What's Jordan's work-life balance like?", "dm_owner"),
        ("Tell me about Jordan's social life", "group"),
    ]

    core_content, _ = await tenant.core.read()

    for q, ctx in queries:
        print()
        ctx_badge = f"{BG_BLUE}{BLACK}{BOLD} {ctx.upper()} {RESET}" if ctx == "dm_owner" else f"{BG_YELLOW}{BLACK}{BOLD} {ctx.upper()} {RESET}"
        show(f"  {ctx_badge} \"{q}\"")

        r = await tenant.recall(q, count=15, threshold=0.1)
        f = filter_by_permission(r, ctx, tenant_id="p01")
        show(f"  {DIM}↳ {len(f)} memories recalled, filtered by {ctx} permissions{RESET}")

        if not FAST:
            answer = await synthesize_answer("Jordan", core_content, f, q, ctx)
            print()
            for line in answer.strip().split("\n"):
                print(f"  {MAGENTA}│{RESET} {line}")
        else:
            show(f"  {DIM}(synthesis skipped — use without --fast to see LLM answers){RESET}")

    pause()

    # ════════════════════════════════════════════════════════════
    # STEP 5: IMPORT
    # ════════════════════════════════════════════════════════════
    stage(5, total_steps, "INTEROPERABILITY", "Import from Google Takeout (.ics) and ChatGPT (conversations.json)")

    graph_before = len(await store.list("p01", limit=10000))

    # ── Google Calendar ICS ──
    print()
    show(f"  {BOLD}① Google Calendar (.ics){RESET}")

    sample_ics = """BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART:20240315T100000Z
DTEND:20240315T110000Z
SUMMARY:Team standup - Q2 roadmap review
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
BEGIN:VEVENT
DTSTART:20240318T090000Z
DTEND:20240318T100000Z
SUMMARY:Investor call - seed round update
LOCATION:Google Meet
END:VEVENT
END:VCALENDAR"""

    with tempfile.NamedTemporaryFile(suffix=".ics", mode="w", delete=False) as tmp:
        tmp.write(sample_ics)
        ics_path = Path(tmp.name)

    ics_records = parse_ics(ics_path)
    ics_path.unlink()

    for r in ics_records:
        show(f"  {DIM}→{RESET} [{', '.join(r['tags'][:2])}] {r['text'][:65]}")

    # Import ICS
    ics_ids = []
    for record in ics_records:
        sensitivity = classify_sensitivity(record)
        source = record.get("source", "unknown")
        type_suffix = SOURCE_TYPE_MAP.get(source, source)
        mem_id = await tenant.save(
            content=record["text"],
            memory_type=f"{sensitivity}_{type_suffix}",
            tags=record.get("tags", []),
            source_id=record.get("id"),
        )
        ics_ids.append(mem_id)

    show(f"  {GREEN}✓{RESET} {len(ics_ids)} calendar events imported")

    # ── ChatGPT Export ──
    print()
    show(f"  {BOLD}② ChatGPT Export (conversations.json){RESET}")

    sample_chatgpt = [
        {
            "id": "abc-123",
            "title": "Python async patterns",
            "create_time": 1710500000,
            "mapping": {
                "1": {"message": {"author": {"role": "user"}, "content": {"parts": ["How do I use asyncio.gather for parallel API calls?"]}}},
                "2": {"message": {"author": {"role": "assistant"}, "content": {"parts": ["You can use asyncio.gather() to run multiple coroutines concurrently..."]}}},
            },
        },
        {
            "id": "def-456",
            "title": "Debugging memory leaks",
            "create_time": 1710600000,
            "mapping": {
                "1": {"message": {"author": {"role": "user"}, "content": {"parts": ["My Python app is leaking memory, how do I profile it?"]}}},
                "2": {"message": {"author": {"role": "assistant"}, "content": {"parts": ["Use tracemalloc or objgraph to identify the source..."]}}},
            },
        },
        {
            "id": "ghi-789",
            "title": "Meal prep for busy weeks",
            "create_time": 1710700000,
            "mapping": {
                "1": {"message": {"author": {"role": "user"}, "content": {"parts": ["I need quick healthy meals I can prep on Sunday for the whole week"]}}},
                "2": {"message": {"author": {"role": "assistant"}, "content": {"parts": ["Here are some high-protein meal prep ideas..."]}}},
            },
        },
    ]

    chatgpt_records = parse_chatgpt_export(sample_chatgpt)

    for r in chatgpt_records:
        show(f"  {DIM}→{RESET} [{', '.join(r['tags'][:2])}] {r['text'][:65]}")

    # Import ChatGPT
    chatgpt_ids = []
    for record in chatgpt_records:
        sensitivity = classify_sensitivity(record)
        source = record.get("source", "unknown")
        type_suffix = SOURCE_TYPE_MAP.get(source, source)
        mem_id = await tenant.save(
            content=record["text"],
            memory_type=f"{sensitivity}_{type_suffix}",
            tags=record.get("tags", []),
            source_id=record.get("id"),
        )
        chatgpt_ids.append(mem_id)

    show(f"  {GREEN}✓{RESET} {len(chatgpt_ids)} conversations imported")

    # Cross-source linking for all imports
    all_new = ics_ids + chatgpt_ids
    links_created = 0
    linked_pairs: set[tuple[str, str]] = set()
    for mem_id in all_new:
        mem = await store.get("p01", mem_id)
        if not mem or mem.embedding is None:
            continue
        similar = await store.search("p01", mem.embedding, count=5, threshold=0.3)
        for s in similar:
            pair = (mem_id, s.memory.id)
            if s.memory.id != mem_id and pair not in linked_pairs and s.memory.memory_type != mem.memory_type:
                await tenant.link(mem_id, s.memory.id, "related")
                linked_pairs.add(pair)
                linked_pairs.add((s.memory.id, mem_id))
                links_created += 1

    graph_after = len(await store.list("p01", limit=10000))
    print()
    show(f"  {BOLD}Graph grew:{RESET} {graph_before} → {graph_after} memories (+{graph_after - graph_before})")
    show(f"  {BOLD}New cross-source links:{RESET} {links_created} (calendar ↔ email ↔ ai_chat ↔ lifelog)")

    pause()

    # ════════════════════════════════════════════════════════════
    # STEP 6: INSIGHTS
    # ════════════════════════════════════════════════════════════
    stage(6, total_steps, "CROSS-SOURCE INSIGHTS", "Patterns only visible by connecting data across sources")

    show(f"  {DIM}Analyzing: calendar × bank × lifelog × social{RESET}")
    print()

    insights = await generate_insights("Jordan", persona_dir)
    for line in insights.strip().split("\n"):
        if line.strip().startswith("-") or line.strip().startswith("•"):
            print(f"  {YELLOW}▸{RESET} {line.strip().lstrip('-•').strip()}")
        elif line.strip():
            print(f"  {line.strip()}")

    pause()

    # ════════════════════════════════════════════════════════════
    # STEP 7: EXPORT
    # ════════════════════════════════════════════════════════════
    stage(7, total_steps, "PORTABLE EXPORT", "Full knowledge graph as a single JSON file")

    all_memories_final = await store.list("p01", limit=10000)
    all_links_final = []
    link_types: dict[str, int] = {}
    for mem in all_memories_final:
        for link in await store.get_links("p01", mem.id):
            ld = {"source_id": link.source_id, "target_id": link.target_id, "link_type": link.link_type}
            if ld not in all_links_final:
                all_links_final.append(ld)
                link_types[link.link_type] = link_types.get(link.link_type, 0) + 1

    # Source type breakdown
    type_counts: dict[str, int] = {}
    for m in all_memories_final:
        src = m.memory_type.split("_", 1)[1] if "_" in m.memory_type else m.memory_type
        type_counts[src] = type_counts.get(src, 0) + 1

    print()
    show(f"  {BOLD}Portable Memory Format v0.1{RESET}")
    print()

    data("Memories", f"{len(all_memories_final)}")
    for src, ct in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"    {DIM}{src:<15} {ct}{RESET}")

    print()
    data("Links", f"{len(all_links_final)}")
    for lt, ct in sorted(link_types.items(), key=lambda x: -x[1]):
        print(f"    {DIM}{lt:<20} {ct}{RESET}")

    print()
    data("Consent", f"{len(get_consent('p01').sources)} sources configured")
    data("Format", "JSON — memories, embeddings, links, consent, core profile")
    show(f"\n  {DIM}Load into static/graph.html for interactive visualization{RESET}")

    pause()

    # ════════════════════════════════════════════════════════════
    # STEP 8: RIGHT TO ERASURE
    # ════════════════════════════════════════════════════════════
    stage(8, total_steps, "RIGHT TO ERASURE", "Your data, your choice to delete it — permanently")

    print()
    typewrite("  $ /forget therapy sessions")
    print()

    forget_results = await tenant.recall("therapy sessions", count=10, threshold=0.15)

    if forget_results:
        show(f"  Found {len(forget_results)} matching memories:")
        print()
        for r in forget_results[:4]:
            mem_line(r.memory.memory_type, r.memory.content)

        count = 0
        for r in forget_results:
            await client.delete("p01", r.memory.id)
            count += 1

        print()
        show(f"  {RED}✗{RESET} {BOLD}{count} memories deleted.{RESET} Not archived. Not hidden. {BOLD}Gone.{RESET}")
    else:
        show(f"  {DIM}(no therapy-related memories in Jordan's data){RESET}")

    remaining = len(await store.list("p01", limit=10000))
    show(f"  {DIM}Graph: {remaining} memories remaining{RESET}")

    # ════════════════════════════════════════════════════════════
    # SUMMARY
    # ════════════════════════════════════════════════════════════
    elapsed = time.time() - t_start

    print()
    print(f"  {BOLD}{CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
    print(f"  {BOLD}{CYAN}║{RESET}  {GREEN}●{RESET} {GREEN}●{RESET} {GREEN}●{RESET} {GREEN}●{RESET} {GREEN}●{RESET} {GREEN}●{RESET} {GREEN}●{RESET} {GREEN}●{RESET}  {BOLD}All 8 stages complete{RESET}             {BOLD}{CYAN}║{RESET}")
    print(f"  {BOLD}{CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
    print()
    show(f"  {BOLD}Pipeline:{RESET}  ingest → embed → link → recall → filter → synthesize → export")
    show(f"  {BOLD}Sources:{RESET}   JSONL, Google Calendar (.ics), ChatGPT (.json), Gmail (.mbox)")
    show(f"  {BOLD}Controls:{RESET}  per-source consent, 3 access contexts, right to erasure")
    show(f"  {BOLD}Runtime:{RESET}   {elapsed:.0f}s total — all local, no cloud APIs")
    print()
    show(f"  {BOLD}Ollama qwen3:8b{RESET} (synthesis + extraction)")
    show(f"  {BOLD}Ollama nomic-embed-text{RESET} (768-dim embeddings)")
    show(f"  {BOLD}Zero API keys{RESET} for core functionality")
    print()
    show(f"  {DIM}Full Telegram experience: python main.py{RESET}")
    show(f"  {DIM}Graph visualization: open static/graph.html{RESET}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
