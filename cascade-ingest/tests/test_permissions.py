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
