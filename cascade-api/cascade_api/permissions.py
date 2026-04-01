from cascade_memory import SearchResult
from cascade_ingest.consent import get_consent, ConsentConfig, extract_source_from_memory_type
from cascade_ingest.permissions import PRIVATE_SOURCES, PUBLIC_SOURCES, classify_sensitivity  # noqa: F401

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
