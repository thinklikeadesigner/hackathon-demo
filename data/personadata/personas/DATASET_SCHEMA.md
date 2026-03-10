# DATASET_SCHEMA.md — Data Portability Hackathon 2026

## Overview
This folder contains 5 fully synthetic personal memory personas for use in the Data Portability Hackathon. Each persona represents a fictional individual with a coherent life story, consistent across all data files.

All data is **100% synthetic**. No real individuals are represented.

---

## Personas at a Glance

| ID  | Name          | Age | Job                        | Key Themes                          |
|-----|---------------|-----|----------------------------|-------------------------------------|
| p01 | Jordan Lee    | 32  | Senior Product Manager     | Burnout, promotion, relationship guilt, house savings |
| p02 | Maya Patel    | 26  | Medical Resident           | Exhaustion, debt, isolation, career decisions |
| p03 | Darius Webb   | 41  | Agency Founder/CEO         | Post-divorce rebuild, co-parenting, book writing |
| p04 | Sunita Rajan  | 58  | AP Chemistry Teacher       | Pre-retirement, family caregiving, late tech adopter |
| p05 | Theo Nakamura | 23  | Freelance Designer         | ADHD, undercharging, debt payoff, creative growth |

---

## File Structure (per persona)

```
persona_pXX/
├── persona_profile.json    # Who this person is
├── consent.json            # Data use permissions
├── lifelog.jsonl           # 150 personal reflections and activities
├── conversations.jsonl     # 7-10 AI chat sessions
├── emails.jsonl            # 80 work + personal emails
├── calendar.jsonl          # 80 calendar events
├── social_posts.jsonl      # 50 social media posts
├── transactions.jsonl      # 120 financial transactions
├── files_index.jsonl       # 40 file metadata entries
└── README.md               # Persona summary + project ideas per track
```

---

## JSONL Record Format

All `.jsonl` files use one JSON object per line. Common fields:

| Field       | Type     | Description                                  |
|-------------|----------|----------------------------------------------|
| `id`        | string   | Unique record ID (e.g., `ll_0001`, `e_0042`) |
| `ts`        | string   | ISO 8601 timestamp with -05:00 offset        |
| `source`    | string   | Origin system (lifelog, email, calendar, etc)|
| `type`      | string   | Record subtype                               |
| `text`      | string   | Human-readable content                       |
| `tags`      | string[] | Thematic tags for filtering                  |
| `refs`      | string[] | Cross-references to related record IDs       |
| `pii_level` | string   | Always "synthetic"                           |

### ID Prefixes by File
- `ll_` — lifelog entries
- `c_` — AI conversations
- `e_` — emails
- `cal_` — calendar events
- `s_` — social posts
- `t_` — transactions
- `f_` — files index

---

## Loading Data (Quick Start)

### Python
```python
import json

# Load a JSONL file
with open("persona_p01/lifelog.jsonl") as f:
    lifelog = [json.loads(line) for line in f]

# Filter by tag
work_entries = [e for e in lifelog if "work" in e["tags"]]

# Load profile
with open("persona_p01/persona_profile.json") as f:
    profile = json.load(f)
```

### JavaScript
```javascript
const fs = require('fs');
const lifelog = fs.readFileSync('persona_p01/lifelog.jsonl', 'utf8')
  .split('\n').filter(Boolean).map(JSON.parse);
```

---

## Track Guidance

**Track 1 — Memory Infrastructure**
Use p01 or p03. Focus on moving data between files, building APIs that unify the sources, or designing consent flows using `consent.json` as a starting point.

**Track 2 — AI Companions with Purpose**
Use p02 or p05. The `conversations.jsonl` + `lifelog.jsonl` combination gives the narrative depth agents need. Build something that responds to *this person's* specific patterns.

**Track 3 — Personal Data, Personal Value**
Any persona works. Combine `social_posts.jsonl`, `transactions.jsonl`, and `conversations.jsonl` to build a service that surfaces insights the individual couldn't easily see on their own.

---

## Using Your Own Data (Optional)
Participants may also choose to build with their own exported personal data:
- **Google Takeout**: takeout.google.com — exports Gmail, Calendar, Drive, Location History
- **ChatGPT export**: Settings → Data Controls → Export Data
- **Instagram/Facebook**: Settings → Your Activity → Download Your Information

If you use real personal data: process it locally, remove sensitive content before any sharing, and you are responsible for what you disclose.

---

*All synthetic personas created for the Data Portability Hackathon 2026. AI Collective × DTI × UT Law.*
