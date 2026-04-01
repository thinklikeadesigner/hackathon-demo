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
