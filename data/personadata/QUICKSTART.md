# QUICKSTART — Data Portability Hackathon 2026
## AI Collective × DTI × UT Law

Welcome! This guide gets you from zero to working with the datasets in under 10 minutes.

---

## Step 1: Understand the folder structure

```
Hackathon_Datasets/
├── DATASET_SCHEMA.md          ← Full schema reference (read this next)
├── QUICKSTART.md              ← You are here
├── how_to_export_your_own_data.md  ← If you want to use real personal data
├── persona_p01/               ← Jordan Lee, 32, Senior PM
├── persona_p02/               ← Maya Patel, 26, Medical Resident
├── persona_p03/               ← Darius Webb, 41, Agency Founder
├── persona_p04/               ← Sunita Rajan, 58, Chemistry Teacher
└── persona_p05/               ← Theo Nakamura, 23, Freelance Designer
```

Each persona folder contains 10 files:
```
persona_pXX/
├── persona_profile.json   ← Who this person is (goals, pain points, personality)
├── consent.json           ← What you're allowed to do with this data
├── lifelog.jsonl          ← 150 personal reflections and activities
├── conversations.jsonl    ← AI chat history (the richest file for Track 2)
├── emails.jsonl           ← 80 work + personal emails
├── calendar.jsonl         ← 80 events: meetings, appointments, social
├── social_posts.jsonl     ← 50 posts across LinkedIn, Twitter, Instagram
├── transactions.jsonl     ← 120 financial transactions
├── files_index.jsonl      ← 40 file metadata entries (docs, photos, etc.)
└── README.md              ← Persona summary + project ideas per track
```

---

## Step 2: Which persona should I use?

| Track | Recommended Personas | Why |
|-------|---------------------|-----|
| Track 1 — Memory Infrastructure | p01, p03 | Rich multi-source data; good for building unified pipelines |
| Track 2 — AI Companions | p02, p05 | Strong AI conversation logs; emotionally resonant use cases |
| Track 3 — Personal Data Value | Any | All personas have social + transactions + AI history |

You can use multiple personas or combine them. There are no restrictions on which persona you use for which track.

---

## Step 3: Load the data

### Python

```python
import json

# Load a persona profile
with open("persona_p01/persona_profile.json") as f:
    profile = json.load(f)

print(profile["name"])        # Jordan Lee
print(profile["goals"])       # ['Get promoted...', 'Improve sleep...', ...]

# Load a JSONL file (one record per line)
with open("persona_p01/lifelog.jsonl") as f:
    lifelog = [json.loads(line) for line in f]

print(f"Loaded {len(lifelog)} lifelog entries")
print(lifelog[0])

# Filter by tag
work_entries = [e for e in lifelog if "work" in e["tags"]]
burnout_entries = [e for e in lifelog if "burnout" in e["tags"]]

# Load AI conversations
with open("persona_p01/conversations.jsonl") as f:
    conversations = [json.loads(line) for line in f]

# Load all files for a persona into a dict
import os

def load_persona(persona_id):
    folder = f"persona_{persona_id}"
    data = {}
    
    with open(f"{folder}/persona_profile.json") as f:
        data["profile"] = json.load(f)
    
    for filename in ["lifelog", "conversations", "emails", "calendar",
                     "social_posts", "transactions", "files_index"]:
        with open(f"{folder}/{filename}.jsonl") as f:
            data[filename] = [json.loads(line) for line in f]
    
    return data

jordan = load_persona("p01")
print(f"Loaded {jordan['profile']['name']} with {len(jordan['lifelog'])} lifelog entries")
```

### JavaScript / Node.js

```javascript
const fs = require('fs');

// Load a persona profile
const profile = JSON.parse(fs.readFileSync('persona_p01/persona_profile.json', 'utf8'));
console.log(profile.name); // Jordan Lee

// Load a JSONL file
const lifelog = fs.readFileSync('persona_p01/lifelog.jsonl', 'utf8')
  .split('\n')
  .filter(Boolean)
  .map(JSON.parse);

console.log(`Loaded ${lifelog.length} lifelog entries`);

// Filter by tag
const workEntries = lifelog.filter(e => e.tags.includes('work'));
const burnoutEntries = lifelog.filter(e => e.tags.includes('burnout'));

// Load all files for a persona
function loadPersona(personaId) {
  const folder = `persona_${personaId}`;
  const files = ['lifelog', 'conversations', 'emails', 'calendar',
                 'social_posts', 'transactions', 'files_index'];
  
  const data = {
    profile: JSON.parse(fs.readFileSync(`${folder}/persona_profile.json`, 'utf8'))
  };
  
  for (const file of files) {
    data[file] = fs.readFileSync(`${folder}/${file}.jsonl`, 'utf8')
      .split('\n').filter(Boolean).map(JSON.parse);
  }
  
  return data;
}

const jordan = loadPersona('p01');
console.log(`Loaded ${jordan.profile.name} with ${jordan.lifelog.length} lifelog entries`);
```

---

## Step 4: Understand the record format

Every JSONL file uses the same base structure:

```json
{
  "id": "ll_0001",
  "ts": "2024-04-13T08:12:00-05:00",
  "source": "lifelog",
  "type": "reflection",
  "text": "Woke up tired again. Mind already on the roadmap review.",
  "tags": ["sleep", "work", "anxiety"],
  "refs": ["cal_0014"],
  "pii_level": "synthetic"
}
```

| Field | Description |
|-------|-------------|
| `id` | Unique record ID. Prefix indicates file: `ll_` lifelog, `c_` conversations, `e_` emails, `cal_` calendar, `s_` social, `t_` transactions, `f_` files |
| `ts` | ISO 8601 timestamp, Austin timezone (-05:00) |
| `source` | Origin system: `lifelog`, `ai_chat`, `email`, `calendar`, `social`, `bank`, `files` |
| `type` | Record subtype (e.g., `reflection`, `activity`, `milestone`, `inbox`, `sent`, `event`, `post`, `transaction`) |
| `text` | The human-readable content |
| `tags` | Thematic tags for filtering and search |
| `refs` | Cross-references to related record IDs in other files |
| `pii_level` | Always `"synthetic"` — confirms no real personal data |

---

## Step 5: Quick queries to get started

```python
import json
from collections import Counter
from datetime import datetime

with open("persona_p01/lifelog.jsonl") as f:
    lifelog = [json.loads(line) for line in f]

with open("persona_p01/conversations.jsonl") as f:
    conversations = [json.loads(line) for line in f]

with open("persona_p01/transactions.jsonl") as f:
    transactions = [json.loads(line) for line in f]

# What are the most common themes in this person's life?
all_tags = [tag for entry in lifelog for tag in entry["tags"]]
print(Counter(all_tags).most_common(10))

# What does this person talk to AI about most?
ai_tags = [tag for c in conversations for tag in c["tags"]]
print(Counter(ai_tags).most_common(10))

# What are their biggest spending categories?
spend_tags = [tag for t in transactions for tag in t["tags"]]
print(Counter(spend_tags).most_common(10))

# Build a simple timeline across all sources
with open("persona_p01/emails.jsonl") as f:
    emails = [json.loads(line) for line in f]

with open("persona_p01/calendar.jsonl") as f:
    calendar = [json.loads(line) for line in f]

all_events = lifelog + conversations + emails + calendar
all_events.sort(key=lambda x: x["ts"])
print(f"Full timeline: {len(all_events)} events from {all_events[0]['ts']} to {all_events[-1]['ts']}")
```

---

## Step 6: Use AI to generate more data (optional)

If you want additional synthetic personas beyond the 5 provided, generate them using this prompt pattern:

```
Generate a lifelog dataset for a fictional [age]-year-old [job] in [city] as JSONL.
150 lines spanning 24 months. Fields exactly: id, ts, source="lifelog",
type (reflection|activity|milestone), text, tags[], refs[], pii_level="synthetic".
Use ISO timestamps with -05:00 timezone. id format: ll_0001, ll_0002, etc.
Include themes: [list your themes]. Output JSONL only. No commentary.
```

Follow the same pattern for conversations, emails, calendar, etc. Use the schema in `DATASET_SCHEMA.md` as your reference.

---

## Consent reminder

Before building, read `consent.json` in each persona folder. All data is:
- ✅ Allowed: hackathon demos, model prompting, local analysis, team collaboration within the event
- ❌ Not allowed: attempting re-identification, sharing outside the event, commercial use, training production models
- 🗑️ Delete after: March 31, 2026

---

## Need help?

Post in the **#datasets** channel in Slack or ask a mentor during office hours.

*Data Portability Hackathon 2026 — AI Collective × DTI × UT Law*
