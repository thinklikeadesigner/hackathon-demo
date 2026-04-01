import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def persona_dir(tmp_path):
    """Create a minimal persona directory with one JSONL file."""
    records = [
        {
            "id": "cal_001",
            "source": "calendar",
            "text": "Team meeting at 10am",
            "tags": ["work"],
            "refs": [],
        },
        {
            "id": "email_001",
            "source": "email",
            "text": "Re: Team meeting — confirmed",
            "tags": ["work"],
            "refs": ["cal_001"],
        },
    ]
    jsonl_path = tmp_path / "calendar.jsonl"
    with open(jsonl_path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return tmp_path


@pytest.mark.asyncio
async def test_ingest_persona_returns_stats(persona_dir):
    from unittest.mock import AsyncMock, MagicMock

    # Mock MemoryClient
    mock_client = MagicMock()
    mock_tenant = AsyncMock()
    mock_tenant.save = AsyncMock(side_effect=lambda **kwargs: f"mem_{kwargs.get('source_id', 'x')}")
    mock_tenant.link = AsyncMock()
    mock_tenant.core = AsyncMock()
    mock_client.for_tenant.return_value = mock_tenant
    mock_client.store = AsyncMock()
    mock_client.store.get = AsyncMock(return_value=None)

    from cascade_ingest.ingest import ingest_persona

    stats = await ingest_persona(mock_client, "test_tenant", persona_dir)

    assert stats["records_ingested"] == 2
    assert "links_created" in stats
