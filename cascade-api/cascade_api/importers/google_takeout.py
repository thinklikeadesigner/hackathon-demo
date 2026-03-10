"""Google Takeout importer.

Parses Google Takeout exports (mbox email, ICS calendar) into Cascade JSONL-compatible records.
"""

import email
import email.policy
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


# Tag inference keywords (reused pattern from chatgpt importer)
WORK_KEYWORDS = ["meeting", "project", "deadline", "client", "presentation", "report", "strategy", "manager", "team", "review", "standup", "sprint"]
HEALTH_KEYWORDS = ["doctor", "appointment", "gym", "workout", "therapy", "dentist", "medical", "health"]
FINANCE_KEYWORDS = ["invoice", "payment", "receipt", "subscription", "billing", "bank", "tax", "salary"]
SOCIAL_KEYWORDS = ["party", "dinner", "lunch", "coffee", "birthday", "wedding", "happy hour", "meetup", "networking"]
LEARNING_KEYWORDS = ["class", "course", "workshop", "seminar", "conference", "lecture", "hackathon", "tutorial"]
TRAVEL_KEYWORDS = ["flight", "hotel", "airbnb", "boarding", "itinerary", "reservation", "trip", "travel"]


def _infer_email_tags(subject: str, body_preview: str) -> list[str]:
    """Infer tags from email subject and body preview."""
    tags = ["email"]
    text = (subject + " " + body_preview).lower()

    tag_map = [
        ("work", WORK_KEYWORDS),
        ("health", HEALTH_KEYWORDS),
        ("finance", FINANCE_KEYWORDS),
        ("social", SOCIAL_KEYWORDS),
        ("learning", LEARNING_KEYWORDS),
        ("travel", TRAVEL_KEYWORDS),
    ]

    for tag, keywords in tag_map:
        if any(kw in text for kw in keywords):
            tags.append(tag)
        if len(tags) >= 4:
            break

    return tags


def _infer_calendar_tags(summary: str, description: str, location: str) -> list[str]:
    """Infer tags from calendar event fields."""
    tags = ["calendar"]
    text = (summary + " " + description + " " + location).lower()

    tag_map = [
        ("work", WORK_KEYWORDS),
        ("health", HEALTH_KEYWORDS),
        ("social", SOCIAL_KEYWORDS),
        ("learning", LEARNING_KEYWORDS),
        ("travel", TRAVEL_KEYWORDS),
    ]

    for tag, keywords in tag_map:
        if any(kw in text for kw in keywords):
            tags.append(tag)
        if len(tags) >= 4:
            break

    return tags


def _get_text_body(msg: email.message.EmailMessage) -> str:
    """Extract plain text body from an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        return payload.decode("utf-8", errors="replace")
                except Exception:
                    continue
        return ""
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                return payload.decode("utf-8", errors="replace")
        except Exception:
            pass
        return ""


def parse_mbox(filepath: Path, max_emails: int = 500) -> list[dict]:
    """Parse an mbox file into Cascade records.

    Args:
        filepath: Path to the .mbox file.
        max_emails: Maximum number of emails to parse (most recent first isn't
                    guaranteed in mbox, so we just take the first N).
    """
    import mailbox

    records = []
    mbox = mailbox.mbox(str(filepath))

    for i, msg in enumerate(mbox):
        if i >= max_emails:
            break

        subject = msg.get("Subject", "(no subject)")
        from_addr = msg.get("From", "unknown")
        to_addr = msg.get("To", "unknown")
        date_str = msg.get("Date", "")

        # Parse date
        ts = None
        if date_str:
            try:
                dt = email.utils.parsedate_to_datetime(date_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                ts = dt.isoformat()
            except Exception:
                pass

        # Get body preview (first 300 chars)
        body = _get_text_body(msg)
        body_preview = body[:300].strip() if body else ""
        # Clean up whitespace
        body_preview = re.sub(r"\s+", " ", body_preview)

        text = f"From: {from_addr} | To: {to_addr} | Subject: {subject}"
        if body_preview:
            text += f" | Body summary: {body_preview}"

        tags = _infer_email_tags(subject, body_preview)

        records.append({
            "id": f"gmail_{i:05d}",
            "ts": ts,
            "source": "email",
            "type": "email",
            "text": text,
            "tags": tags,
            "refs": [],
        })

    mbox.close()
    return records


def parse_ics(filepath: Path) -> list[dict]:
    """Parse an ICS calendar file into Cascade records."""
    content = filepath.read_text(encoding="utf-8", errors="replace")

    records = []
    events = content.split("BEGIN:VEVENT")

    for i, event_block in enumerate(events[1:]):  # skip preamble
        event_block = event_block.split("END:VEVENT")[0]

        def _get_field(name: str) -> str:
            # ICS fields can be multi-line (continuation lines start with space/tab)
            pattern = rf"^{re.escape(name)}[^:]*:(.*?)(?=\n[A-Z]|\nEND:|\Z)"
            match = re.search(pattern, event_block, re.MULTILINE | re.DOTALL)
            if match:
                val = match.group(1).strip()
                # Unfold continuation lines
                val = re.sub(r"\n[ \t]", "", val)
                # Unescape ICS
                val = val.replace("\\n", " ").replace("\\,", ",").replace("\\;", ";")
                return val
            return ""

        summary = _get_field("SUMMARY")
        description = _get_field("DESCRIPTION")
        location = _get_field("LOCATION")
        dtstart = _get_field("DTSTART")
        uid = _get_field("UID") or f"cal_{i:04d}"

        if not summary:
            continue

        # Parse date
        ts = None
        if dtstart:
            for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%dT%H%M%S", "%Y%m%d"):
                try:
                    dt = datetime.strptime(dtstart, fmt)
                    if fmt.endswith("Z"):
                        dt = dt.replace(tzinfo=timezone.utc)
                    ts = dt.isoformat()
                    break
                except ValueError:
                    continue

        text = f"Calendar event: {summary}"
        if location:
            text += f" | Location: {location}"
        if description:
            desc_preview = description[:200].strip()
            desc_preview = re.sub(r"\s+", " ", desc_preview)
            if desc_preview:
                text += f" | Details: {desc_preview}"

        tags = _infer_calendar_tags(summary, description, location)

        records.append({
            "id": f"gcal_{uid[:20]}_{i:04d}",
            "ts": ts,
            "source": "calendar",
            "type": "event",
            "text": text,
            "tags": tags,
            "refs": [],
        })

    return records


def load_takeout_directory(takeout_dir: Path, max_emails: int = 500) -> list[dict]:
    """Load all supported Google Takeout data from a directory.

    Scans for:
    - Mail/*.mbox files
    - Calendar/*.ics files

    Returns combined Cascade-compatible records.
    """
    records = []

    # Mail
    mail_dir = takeout_dir / "Mail"
    if mail_dir.exists():
        for mbox_file in mail_dir.glob("*.mbox"):
            records.extend(parse_mbox(mbox_file, max_emails=max_emails))

    # Calendar
    cal_dir = takeout_dir / "Calendar"
    if cal_dir.exists():
        for ics_file in cal_dir.glob("*.ics"):
            records.extend(parse_ics(ics_file))

    return records


def load_takeout_zip(filepath: Path, max_emails: int = 500) -> list[dict]:
    """Load Google Takeout data from a zip file.

    Extracts to a temp directory, processes all supported files, then cleans up.
    Handles the standard Takeout/ prefix inside the zip.
    """
    records = []

    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(filepath) as zf:
            zf.extractall(tmpdir)

        tmp = Path(tmpdir)

        # Google Takeout zips contain a "Takeout/" prefix
        takeout_dir = tmp / "Takeout"
        if not takeout_dir.exists():
            # Fallback: maybe extracted flat
            takeout_dir = tmp

        records = load_takeout_directory(takeout_dir, max_emails=max_emails)

    return records
