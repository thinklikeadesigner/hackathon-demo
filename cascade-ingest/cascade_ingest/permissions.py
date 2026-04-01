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
