# Deep Heartbeat Backup Procedure (confirmed 2026-06-29)

## Problem
The `cron-heartbeat-deep-dualpath.py` script's Python `with open()` writes to `ingestion_log.jsonl` silently fail in cron mode — same pattern as light heartbeat gotcha #27 but NOT documented in the original deep heartbeat fix (gotcha #32/dual-path). Confirmed 2026-06-29: script reported "New ingested: 665" but `wc -l` showed ingestion delta of 0.

## Root Cause
The deep heartbeat script writes to 4 targets:
1. `evidence.jsonl` — succeeded in this run
2. `ingestion_log.jsonl` — FAILED (delta=0)
3. `decisions.jsonl` — no new decisions (expected)
4. `proposals-{date}.json` — proposals directory didn't exist

Python `with open()` in cron `terminal()` is unreliable. The deep heartbeat is NOT exempt.

## Backup Procedure

### Step 1: Ensure proposals directory exists
```bash
mkdir -p /root/.hermes/profiles/indigo/commons/data/mentor/proposals
```

### Step 2: Build the full dual-path file list (if not already built)
```bash
find /root/.hermes/commons/journals/ -name "*.json" -not -path "*/.archive/*" -not -path "*/.quarantine/*" > /tmp/mentor_deep_shared.txt
find /root/.hermes/profiles/indigo/commons/journals/ -name "*.json" -not -path "*/.archive/*" -not -path "*/.quarantine/*" >> /tmp/mentor_deep_shared.txt
sort -u /tmp/mentor_deep_shared.txt > /tmp/mentor_deep_files.txt
```

### Step 3: Write ingestion backup via Python script (write to /tmp/ first)
```python
#!/usr/bin/env python3
import json, os
from datetime import datetime, timezone

DATA_DIR = "/root/.hermes/profiles/indigo/commons/data/mentor"
INGESTION_LOG = os.path.join(DATA_DIR, "ingestion_log.jsonl")

already_ingested = set()
with open(INGESTION_LOG) as f:
    for line in f:
        if not line.strip(): continue
        try:
            d = json.loads(line)
            already_ingested.add(d.get("file", d.get("source", "")))
        except: pass

with open("/tmp/mentor_deep_files.txt") as f:
    all_files = [l.strip() for l in f if l.strip()]

now_iso = datetime.now(timezone.utc).isoformat()
written = 0
with open(INGESTION_LOG, "a") as f:
    for filepath in all_files:
        if filepath not in already_ingested:
            parts = filepath.split("/")
            skill_name = ""
            for i, part in enumerate(parts):
                if part == "journals" and i+1 < len(parts):
                    skill_name = parts[i+1]; break
            record = {
                "file": filepath,
                "skill_name": skill_name,
                "ingested_at": now_iso,
                "entries": 1,
                "heartbeat_type": "deep"
            }
            f.write(json.dumps(record) + "\n")
            written += 1

print(f"Ingestion backup: {written} records written")
```

### Step 4: Verify
```bash
echo "Ingestion (profile): $(wc -l < /root/.hermes/profiles/indigo/commons/data/mentor/ingestion_log.jsonl)"
```

## Key Differences from Light Heartbeat Backup
- Deep heartbeat scans ALL journals (not just 3-day), so the file list is much larger (~18K)
- Ingestion backup writes thousands of records (not 2-3 like light heartbeat)
- Do NOT attempt to write a backup deep journal — deep journals are large and caller-written deep journals are not canonical
- The `correct_active_skills_30d.py` script reports `script=None` after deep heartbeats because the deep script uses `skills_active_30d` (not `active_skills_30d`). This is expected.

## Write Targets Verification Checklist
| Target | What to check | Backup action |
|--------|--------------|---------------|
| evidence.jsonl | `wc -l` delta ≥ 1 | Write flat evidence record via Python |
| ingestion_log.jsonl | `wc -l` delta ≥ 1 | Run `/tmp/mentor_deep_backup.py` |
| journal directory | `ls` shows recent `mentor-deep-*.json` | Do NOT back up (too large, not canonical) |
| decisions.jsonl | `wc -l` delta (may be 0 if no new decisions) | Only if delta expected but 0 |
| okr_state.json | File mtime updated | `cp` from profile to commons |
| proposals dir | Directory exists | `mkdir -p` before script run |
