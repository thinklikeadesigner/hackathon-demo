"""cascade-ingest — data ingestion pipeline for cascade-memory."""

from cascade_ingest.consent import (
    ConsentConfig,
    get_consent,
    set_consent,
    SENSITIVE_TAGS,
    extract_source_from_memory_type,
)
from cascade_ingest.permissions import classify_sensitivity, PRIVATE_SOURCES, PUBLIC_SOURCES

__all__ = [
    "ConsentConfig",
    "get_consent",
    "set_consent",
    "SENSITIVE_TAGS",
    "extract_source_from_memory_type",
    "classify_sensitivity",
    "PRIVATE_SOURCES",
    "PUBLIC_SOURCES",
]
