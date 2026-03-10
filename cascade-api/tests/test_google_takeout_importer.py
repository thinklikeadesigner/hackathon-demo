"""Tests for Google Takeout importer."""

import tempfile
from pathlib import Path

from cascade_api.importers.google_takeout import parse_ics, parse_mbox, load_takeout_directory, load_takeout_zip


SAMPLE_ICS = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
DTSTART:20260309T140000Z
DTEND:20260309T150000Z
UID:test-event-001@google.com
SUMMARY:Team Standup
LOCATION:Zoom
DESCRIPTION:Weekly sync with the engineering team
STATUS:CONFIRMED
END:VEVENT
BEGIN:VEVENT
DTSTART:20260310T180000Z
DTEND:20260310T200000Z
UID:test-event-002@google.com
SUMMARY:Birthday Dinner with Sarah
LOCATION:Uchi Austin\\, 801 S Lamar Blvd
DESCRIPTION:Celebrating Sarah's 30th!
STATUS:CONFIRMED
END:VEVENT
BEGIN:VEVENT
DTSTART:20260315
UID:test-event-003@google.com
SUMMARY:Flight to NYC
DESCRIPTION:Boarding pass in email
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR
"""

SAMPLE_MBOX = """From sender@example.com Mon Mar  9 10:00:00 2026
From: Alice <alice@example.com>
To: user@example.com
Subject: Q2 Project Kickoff
Date: Mon, 09 Mar 2026 10:00:00 +0000
Content-Type: text/plain

Hey team, let's align on Q2 priorities. The project deadline is April 15.

From sender@example.com Tue Mar 10 09:00:00 2026
From: Bob <bob@example.com>
To: user@example.com
Subject: Invoice #1234
Date: Tue, 10 Mar 2026 09:00:00 +0000
Content-Type: text/plain

Please find attached your invoice for March services. Payment due by March 30.

From sender@example.com Wed Mar 11 15:00:00 2026
From: Carol <carol@example.com>
To: user@example.com
Subject: Dinner Friday?
Date: Wed, 11 Mar 2026 15:00:00 +0000
Content-Type: text/plain

Want to grab dinner Friday? Thinking that new ramen place.

"""


def test_parse_ics():
    with tempfile.NamedTemporaryFile(suffix=".ics", mode="w", delete=False) as f:
        f.write(SAMPLE_ICS)
        path = Path(f.name)

    records = parse_ics(path)
    path.unlink()

    assert len(records) == 3

    # First event: work standup
    r0 = records[0]
    assert "Team Standup" in r0["text"]
    assert "Zoom" in r0["text"]
    assert r0["source"] == "calendar"
    assert "work" in r0["tags"]
    assert r0["ts"] is not None

    # Second event: social dinner
    r1 = records[1]
    assert "Birthday Dinner" in r1["text"]
    assert "social" in r1["tags"]

    # Third event: travel
    r2 = records[2]
    assert "Flight to NYC" in r2["text"]
    assert "travel" in r2["tags"]


def test_parse_mbox():
    with tempfile.NamedTemporaryFile(suffix=".mbox", mode="w", delete=False) as f:
        f.write(SAMPLE_MBOX)
        path = Path(f.name)

    records = parse_mbox(path)
    path.unlink()

    assert len(records) == 3

    # First: work email
    r0 = records[0]
    assert "alice@example.com" in r0["text"]
    assert "Q2 Project Kickoff" in r0["text"]
    assert r0["source"] == "email"
    assert "work" in r0["tags"]
    assert r0["ts"] is not None

    # Second: finance email
    r1 = records[1]
    assert "Invoice" in r1["text"]
    assert "finance" in r1["tags"]

    # Third: social email
    r2 = records[2]
    assert "Dinner" in r2["text"]
    assert "social" in r2["tags"]


def test_parse_mbox_max_limit():
    with tempfile.NamedTemporaryFile(suffix=".mbox", mode="w", delete=False) as f:
        f.write(SAMPLE_MBOX)
        path = Path(f.name)

    records = parse_mbox(path, max_emails=1)
    path.unlink()

    assert len(records) == 1


def test_parse_ics_empty():
    with tempfile.NamedTemporaryFile(suffix=".ics", mode="w", delete=False) as f:
        f.write("BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR\n")
        path = Path(f.name)

    records = parse_ics(path)
    path.unlink()

    assert records == []


def test_load_takeout_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        takeout = Path(tmpdir)

        # Create Calendar dir with ICS
        cal_dir = takeout / "Calendar"
        cal_dir.mkdir()
        (cal_dir / "test.ics").write_text(SAMPLE_ICS)

        # Create Mail dir with mbox
        mail_dir = takeout / "Mail"
        mail_dir.mkdir()
        (mail_dir / "test.mbox").write_text(SAMPLE_MBOX)

        records = load_takeout_directory(takeout)

    assert len(records) == 6  # 3 calendar + 3 email
    sources = {r["source"] for r in records}
    assert sources == {"calendar", "email"}


def test_load_takeout_zip():
    import zipfile

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a zip with Takeout/ prefix (matches real Google Takeout structure)
        zip_path = Path(tmpdir) / "takeout.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("Takeout/Calendar/test.ics", SAMPLE_ICS)
            zf.writestr("Takeout/Mail/test.mbox", SAMPLE_MBOX)

        records = load_takeout_zip(zip_path)

    assert len(records) == 6  # 3 calendar + 3 email
    sources = {r["source"] for r in records}
    assert sources == {"calendar", "email"}


def test_load_takeout_zip_calendar_only():
    import zipfile

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "takeout.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("Takeout/Calendar/cal.ics", SAMPLE_ICS)

        records = load_takeout_zip(zip_path)

    assert len(records) == 3
    assert all(r["source"] == "calendar" for r in records)


def test_record_format_matches_cascade():
    """Verify records have the same fields as other importers."""
    with tempfile.NamedTemporaryFile(suffix=".ics", mode="w", delete=False) as f:
        f.write(SAMPLE_ICS)
        path = Path(f.name)

    records = parse_ics(path)
    path.unlink()

    required_fields = {"id", "ts", "source", "type", "text", "tags", "refs"}
    for r in records:
        assert required_fields.issubset(r.keys()), f"Missing fields: {required_fields - r.keys()}"
        assert isinstance(r["tags"], list)
        assert isinstance(r["refs"], list)
