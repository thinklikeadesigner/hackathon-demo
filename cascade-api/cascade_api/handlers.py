import json
import logging
from io import BytesIO

from telegram import Update
from telegram.ext import ContextTypes

from cascade_api.memory import MemoryClient
from cascade_api.config import BotConfig
from cascade_api.consent import get_consent, extract_source_from_memory_type
from cascade_api.permissions import filter_by_permission, classify_sensitivity
from cascade_api.synthesize import synthesize_answer
from cascade_api.insights import generate_insights

# Optional: Supabase client for exporting Cascade data (goals, tasks, etc.)
_supabase_client = None
# Optional: callback to persist the memory store after writes
_save_cache_fn = None


def set_supabase_client(client):
    """Set the shared Supabase client for export enrichment."""
    global _supabase_client
    _supabase_client = client


def set_save_cache_fn(fn):
    """Set a callback to persist the memory store after new memories are saved."""
    global _save_cache_fn
    _save_cache_fn = fn

logger = logging.getLogger(__name__)


def determine_context(update: Update, config: BotConfig) -> str:
    """Determine permission context from the update."""
    chat_type = update.effective_chat.type
    user_id = update.effective_user.id

    if chat_type in ("group", "supergroup"):
        return "group"
    if chat_type == "private":
        if config.owner_chat_id and user_id == config.owner_chat_id:
            return "dm_owner"
        return "dm_stranger"
    return "group"


def make_message_handler(config: BotConfig, memory_client: MemoryClient, persona_dir=None):
    """Create a message handler closure for a specific bot/persona."""
    tenant = memory_client.for_tenant(config.tenant_id)

    export_fn = make_export_handler(config, memory_client)
    privacy_fn = make_privacy_handler(config)
    forget_fn = make_forget_handler(config, memory_client)
    import_fn = make_import_handler(config, memory_client)
    insights_fn = make_insights_handler(config, persona_dir) if persona_dir else None

    async def handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        question = update.message.text

        # Catch /export even if Telegram doesn't send it as a command entity
        if question and question.strip().lower().startswith("/export"):
            return await export_fn(update, ctx)

        # Catch /privacy as text fallback
        if question and question.strip().lower().startswith("/privacy"):
            return await privacy_fn(update, ctx)

        # Catch /forget as text fallback
        if question and question.strip().lower().startswith("/forget"):
            return await forget_fn(update, ctx)

        # Catch /import as text fallback
        if question and question.strip().lower().startswith("/import"):
            return await import_fn(update, ctx)

        # Catch /insights as text fallback
        if question and question.strip().lower().startswith("/insights"):
            if insights_fn:
                return await insights_fn(update, ctx)
            else:
                await update.message.reply_text("No persona data available for insights on this bot.")
                return

        context = determine_context(update, config)

        if context == "dm_stranger":
            await update.message.reply_text("I only talk to my user in private.")
            return

        results = await tenant.recall(question, count=20, threshold=0.1)
        logger.info(f"[{config.name}] recall store id={id(memory_client.store)}, for '{question[:50]}': {len(results)} results")
        for r in results[:5]:
            logger.info(f"  {r.memory.memory_type} sim={r.similarity:.3f} {r.memory.content[:60]}")
        filtered = filter_by_permission(results, context, tenant_id=config.tenant_id)
        logger.info(f"[{config.name}] after {context} filter: {len(filtered)} results")
        core_content, _ = await tenant.core.read()

        answer = await synthesize_answer(
            persona_name=config.name,
            core_memory=core_content,
            results=filtered,
            question=question,
            context=context,
        )

        await update.message.reply_text(answer)

        # Extract and save memories from the conversation (owner DMs only)
        if context == "dm_owner" and memory_client.extractor:
            try:
                conversation = f"User: {question}\nAssistant: {answer}"
                saved = await tenant.extract(conversation)
                if saved:
                    logger.info(f"[{config.name}] extracted {len(saved)} memories from conversation")
                    if _save_cache_fn:
                        _save_cache_fn()
            except Exception as e:
                logger.warning(f"[{config.name}] memory extraction failed: {e}")

    return handler


def make_privacy_handler(config: BotConfig):
    """Create a /privacy handler for viewing and changing consent settings."""

    async def handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        context = determine_context(update, config)
        if context != "dm_owner":
            await update.message.reply_text("Privacy settings are only available to the owner.")
            return

        text = update.message.text.strip()
        consent = get_consent(config.tenant_id)

        # /privacy set <source> <level>
        parts = text.split()
        if len(parts) >= 4 and parts[1].lower() == "set":
            source = parts[2].lower()
            level = parts[3].lower()
            if consent.set_level(source, level):
                if _save_cache_fn:
                    _save_cache_fn()
                await update.message.reply_text(
                    f"Updated: {source} → {level}\n\n{consent.summary()}"
                )
            else:
                await update.message.reply_text(
                    f"Invalid. Use: /privacy set <source> <public|owner_only>\n"
                    f"Sources: {', '.join(consent.sources.keys())}"
                )
            return

        # /privacy — show current settings
        await update.message.reply_text(consent.summary())

    return handler


def make_insights_handler(config: BotConfig, persona_dir):
    """Create an /insights handler that generates cross-source pattern analysis."""
    from pathlib import Path

    async def handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        context = determine_context(update, config)

        if context != "dm_owner":
            await update.message.reply_text("Insights are only available to the owner in a private chat.")
            return

        await update.message.reply_text("Analyzing cross-source patterns...")
        try:
            result = await generate_insights(config.name, Path(persona_dir))
            # Truncate for Telegram limit
            if len(result) > 4000:
                result = result[:4000] + "\n\n... (truncated)"
            await update.message.reply_text(result)
        except Exception as e:
            logger.error(f"[{config.name}] insights generation failed: {e}")
            await update.message.reply_text(f"Failed to generate insights: {e}")

    return handler


def make_forget_handler(config: BotConfig, memory_client: MemoryClient):
    """Create a /forget handler for right-to-erasure."""
    tenant = memory_client.for_tenant(config.tenant_id)

    async def handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        context = determine_context(update, config)

        if context != "dm_owner":
            await update.message.reply_text("Only the owner can delete memories.")
            return

        text = update.message.text.strip()
        parts = text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await update.message.reply_text(
                "Usage: /forget <query>\n"
                "Searches for matching memories and deletes them."
            )
            return

        query = parts[1].strip()
        results = await tenant.recall(query, count=10, threshold=0.15)

        if not results:
            await update.message.reply_text("No matching memories found.")
            return

        count = 0
        for r in results:
            await memory_client.delete(config.tenant_id, r.memory.id)
            count += 1

        if _save_cache_fn:
            _save_cache_fn()

        await update.message.reply_text(f"Deleted {count} matching memories.")

    return handler


def make_import_handler(config: BotConfig, memory_client: MemoryClient):
    """Create an /import handler for importing external data exports."""
    tenant = memory_client.for_tenant(config.tenant_id)

    async def handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        logger.info(f"[{config.name}] import handler triggered by user {update.effective_user.id}, chat type: {update.effective_chat.type}, has doc: {bool(update.message.document)}")
        context = determine_context(update, config)
        logger.info(f"[{config.name}] import context: {context} (owner_chat_id: {config.owner_chat_id})")

        if context != "dm_owner":
            await update.message.reply_text("Import is only available to the owner.")
            return

        if not update.message.document:
            await update.message.reply_text(
                "Usage: /import (attach a file)\n\n"
                "Supported formats:\n"
                "- Google Takeout zip (.zip)\n"
                "- Google Calendar (.ics)\n"
                "- Gmail archive (.mbox)\n"
                "- ChatGPT export (conversations.json)"
            )
            return

        await update.message.reply_text("Processing your file...")

        try:
            file = await ctx.bot.get_file(update.message.document.file_id)
            raw = await file.download_as_bytearray()
        except Exception as e:
            logger.error(f"[{config.name}] import download failed: {e}")
            await update.message.reply_text(f"Failed to read file: {e}")
            return

        # Detect format by filename extension
        filename = update.message.document.file_name or ""
        if filename.lower().endswith(".zip"):
            import tempfile
            from pathlib import Path as _Path
            from cascade_api.importers.google_takeout import load_takeout_zip
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                tmp.write(raw)
                tmp_path = _Path(tmp.name)
            try:
                records = load_takeout_zip(tmp_path)
            finally:
                tmp_path.unlink(missing_ok=True)
        elif filename.lower().endswith(".ics"):
            import tempfile
            from pathlib import Path as _Path
            from cascade_api.importers.google_takeout import parse_ics
            with tempfile.NamedTemporaryFile(suffix=".ics", delete=False) as tmp:
                tmp.write(raw)
                tmp_path = _Path(tmp.name)
            records = parse_ics(tmp_path)
            tmp_path.unlink(missing_ok=True)
        elif filename.lower().endswith(".mbox"):
            import tempfile
            from pathlib import Path as _Path
            from cascade_api.importers.google_takeout import parse_mbox
            with tempfile.NamedTemporaryFile(suffix=".mbox", delete=False) as tmp:
                tmp.write(raw)
                tmp_path = _Path(tmp.name)
            records = parse_mbox(tmp_path)
            tmp_path.unlink(missing_ok=True)
        else:
            # Try JSON formats (ChatGPT export)
            try:
                data = json.loads(raw.decode("utf-8"))
            except Exception as e:
                await update.message.reply_text(f"Failed to parse file: {e}")
                return
            if isinstance(data, list) and data and isinstance(data[0], dict) and "mapping" in data[0]:
                from cascade_api.importers.chatgpt import parse_chatgpt_export
                records = parse_chatgpt_export(data)
            else:
                await update.message.reply_text("Unrecognized file format. Supported: .json (ChatGPT), .ics (Google Calendar), .mbox (Gmail)")
                return

        if not records:
            await update.message.reply_text("No records found in the file.")
            return

        count = 0
        new_memory_ids = []
        sources_seen = set()
        for record in records:
            sensitivity = classify_sensitivity(record)
            source = record.get("source", "unknown")
            sources_seen.add(source)
            from cascade_api.ingest import SOURCE_TYPE_MAP
            type_suffix = SOURCE_TYPE_MAP.get(source, source)
            memory_type = f"{sensitivity}_{type_suffix}"

            memory_id = await tenant.save(
                content=record["text"],
                memory_type=memory_type,
                tags=record.get("tags", []),
                source_id=record.get("id"),
            )
            new_memory_ids.append(memory_id)
            count += 1

        # Cross-source linking: find similar memories across different types
        import random
        sample_size = min(100, len(new_memory_ids))
        sampled = random.sample(new_memory_ids, sample_size) if len(new_memory_ids) > sample_size else new_memory_ids
        links_created = 0
        linked_pairs: set[tuple[str, str]] = set()

        for mem_id in sampled:
            mem = await memory_client.store.get(config.tenant_id, mem_id)
            if not mem or mem.embedding is None:
                continue
            try:
                similar = await memory_client.store.search(config.tenant_id, mem.embedding, count=6, threshold=0.3)
                for result in similar:
                    other_id = result.memory.id
                    if other_id == mem_id:
                        continue
                    if (mem_id, other_id) in linked_pairs:
                        continue
                    if result.memory.memory_type != mem.memory_type:
                        await tenant.link(mem_id, other_id, "related")
                        linked_pairs.add((mem_id, other_id))
                        linked_pairs.add((other_id, mem_id))
                        links_created += 1
            except Exception as e:
                logger.warning(f"[{config.name}] cross-link failed for {mem_id[:8]}: {e}")

        # Update consent config with new sources
        from cascade_api.consent import get_consent, set_consent, ConsentConfig
        from cascade_api.permissions import PRIVATE_SOURCES
        consent = get_consent(config.tenant_id)
        for src in sources_seen:
            if src not in consent.sources:
                consent.sources[src] = "owner_only" if src in PRIVATE_SOURCES else "public"
        set_consent(config.tenant_id, consent)

        if _save_cache_fn:
            _save_cache_fn()

        await update.message.reply_text(f"Imported {count} records, created {links_created} cross-source links.")

    return handler


def make_export_handler(config: BotConfig, memory_client: MemoryClient):
    """Create an /export handler that sends the user's memory as JSON."""
    tenant = memory_client.for_tenant(config.tenant_id)

    async def handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        context = determine_context(update, config)

        if context != "dm_owner":
            await update.message.reply_text("Export is only available to my user in a private chat.")
            return

        core_content, core_version = await tenant.core.read()
        logger.info(f"[{config.name}] export: store id={id(memory_client.store)}, tenant={config.tenant_id}")
        logger.info(f"[{config.name}] export: tenant_memories keys={list(getattr(memory_client.store, '_tenant_memories', {}).keys())}")
        logger.info(f"[{config.name}] export: k2 count={len(getattr(memory_client.store, '_tenant_memories', {}).get('k2', []))}")
        memories = await memory_client.store.list(config.tenant_id, limit=10000)
        logger.info(f"[{config.name}] export: list returned {len(memories)} memories")

        all_links = []
        for mem in memories:
            links = await memory_client.store.get_links(config.tenant_id, mem.id)
            for link in links:
                link_dict = {"source_id": link.source_id, "target_id": link.target_id, "link_type": link.link_type}
                if link_dict not in all_links:
                    all_links.append(link_dict)

        consent = get_consent(config.tenant_id)

        export = {
            "tenant_id": config.tenant_id,
            "persona_name": config.name,
            "consent": consent.to_dict(),
            "core_memory": {"content": core_content, "version": core_version},
            "memories": [
                {
                    "id": m.id,
                    "content": m.content,
                    "memory_type": m.memory_type,
                    "tags": m.tags,
                    "confidence": m.confidence,
                    "decay_score": m.decay_score,
                    "source_id": m.source_id,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in memories
            ],
            "links": all_links,
        }

        # Include Cascade data (goals, tasks, tracker, adaptations) if available
        if _supabase_client:
            try:
                goals = _supabase_client.table("goals").select("*").eq("tenant_id", config.tenant_id).execute()
                export["goals"] = goals.data or []

                tasks = _supabase_client.table("tasks").select("*").eq("tenant_id", config.tenant_id).execute()
                export["tasks"] = tasks.data or []

                tracker = _supabase_client.table("tracker_entries").select("*").eq("tenant_id", config.tenant_id).order("date", desc=True).execute()
                export["tracker_entries"] = tracker.data or []

                adaptations = _supabase_client.table("adaptations").select("*").eq("tenant_id", config.tenant_id).execute()
                export["adaptations"] = adaptations.data or []
            except Exception as e:
                logger.warning(f"[{config.name}] failed to fetch Cascade data for export: {e}")

        total_items = len(memories) + len(export.get("goals", [])) + len(export.get("tasks", [])) + len(export.get("tracker_entries", []))
        export_json = json.dumps(export, indent=2, default=str)
        buf = BytesIO(export_json.encode())
        buf.name = f"memory_export_{config.tenant_id}.json"
        await update.message.reply_document(
            document=buf,
            caption=f"Your memory export — {len(memories)} memories, {len(all_links)} connections, {len(export.get('goals', []))} goals, {len(export.get('tasks', []))} tasks, {len(export.get('tracker_entries', []))} tracker entries.",
        )

    return handler
