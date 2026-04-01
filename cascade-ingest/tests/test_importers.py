import json
import tempfile
from pathlib import Path

from cascade_ingest.importers.chatgpt import parse_chatgpt_export
from cascade_ingest.importers.google_takeout import parse_ics


def test_parse_chatgpt_export_basic():
    data = [
        {
            "id": "abc123",
            "title": "Python help",
            "create_time": 1700000000.0,
            "mapping": {
                "node1": {
                    "message": {
                        "author": {"role": "user"},
                        "content": {"parts": ["How do I use list comprehensions?"]},
                    }
                },
                "node2": {
                    "message": {
                        "author": {"role": "assistant"},
                        "content": {"parts": ["List comprehensions are a concise way..."]},
                    }
                },
            },
        }
    ]
    records = parse_chatgpt_export(data)
    assert len(records) == 1
    assert records[0]["source"] == "ai_chat"
    assert records[0]["id"] == "chatgpt_abc123"
    assert "Python help" in records[0]["text"]


def test_parse_chatgpt_export_empty_mapping():
    data = [{"id": "x", "title": "empty", "mapping": {}}]
    records = parse_chatgpt_export(data)
    assert len(records) == 0


def test_parse_ics_basic():
    ics_content = """BEGIN:VCALENDAR
BEGIN:VEVENT
SUMMARY:Team standup
DTSTART:20240115T100000Z
UID:standup-001
END:VEVENT
END:VCALENDAR"""

    with tempfile.NamedTemporaryFile(suffix=".ics", mode="w", delete=False) as f:
        f.write(ics_content)
        tmp_path = Path(f.name)

    records = parse_ics(tmp_path)
    tmp_path.unlink()

    assert len(records) == 1
    assert records[0]["source"] == "calendar"
    assert "Team standup" in records[0]["text"]
    assert records[0]["tags"][0] == "calendar"
