# Ingestion Cross-Reference Technique

## Problem

When cross-referencing 3-day files against the ingestion log to verify `new_files_ingested`, a naive `comm -23` between the 3-day file list and the full ingestion log produces misleading results.

The ingestion log contains **all** historically ingested paths (15,000+), most of which are outside the 3-day window. When you do:

```bash
comm -23 <(sort /tmp/mentor_files_3d.txt) <(sort /tmp/ingested_paths.txt) > /tmp/truly_new_files.txt
```

The result shows 0 "new" files even when the script correctly ingested 4 new files — because all 4,772 3-day files are already in the ingestion log from prior runs.

## Ingestion Log Schema

The ingestion log uses **two different path fields** depending on entry type:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `file` | string | Absolute path to journal (most entries) | `/root/.hermes/profiles/indigo/commons/journals/ocas-mentor/2026-06-22/mentor-light-20260622T144335Z.json` |
| `source` | string | Relative path (some older entries) | `ocas-lucid/2026-05-15/dream-20260515T104600.json` |
| `paths` | list | **DOES NOT EXIST** — common misconception | N/A |

**Critical:** There is no `paths` field. Code that reads `rec.get('paths', [])` will always return empty. Always check `file` first, then `source`:

```python
ingested = set()
with open('/root/.hermes/profiles/indigo/commons/data/mentor/ingestion_log.jsonl') as f:
    for line in f:
        try:
            rec = json.loads(line.strip())
            if rec.get('file'):
                ingested.add(rec['file'])
            if rec.get('source'):
                ingested.add(rec['source'])
        except:
            pass
```

## Correct Approach

Use Python set difference between the 3-day file set and the ingested-paths set:

```python
import json

# Load 3d files
with open('/tmp/mentor_files_3d_sorted.txt') as f:
    files_3d = set(line.strip() for line in f)

# Load ingested paths (using file + source fields)
ingested = set()
with open('/root/.hermes/profiles/indigo/commons/data/mentor/ingestion_log.jsonl') as f:
    for line in f:
        try:
            rec = json.loads(line.strip())
            if rec.get('file'):
                ingested.add(rec['file'])
            if rec.get('source'):
                ingested.add(rec['source'])
        except:
            pass

# Set difference: 3d files NOT in ingestion log
truly_new = files_3d - ingested
already_ingested = files_3d & ingested

print(f'3d files: {len(files_3d)}')
print(f'Already ingested: {len(already_ingested)}')
print(f'Truly new: {len(truly_new)}')
```

If `len(truly_new)` matches the script's `new_files_ingested`, the count is verified.

## Alternative: Check for Re-Ingestion

To verify the script didn't re-ingest already-known files, check if the last N ingestion entries (where N = script's reported count) were already present BEFORE this run:

```python
import json

with open('/root/.hermes/profiles/indigo/commons/data/mentor/ingestion_log.jsonl') as f:
    lines = f.readlines()

n_new = 4  # script's reported count
new_files = []
for line in lines[-n_new:]:
    d = json.loads(line)
    new_files.append(d.get('file', ''))

prior = set()
for line in lines[:-n_new]:
    try:
        d = json.loads(line)
        prior.add(d.get('file', ''))
    except: pass

for f in new_files:
    status = "ALREADY PRESENT" if f in prior else "TRULY NEW"
    print(f'{status}: {f[-70:]}')
```

## When to Use Which

| Scenario | Method |
|----------|--------|
| Verify script's `new_files_ingested` count | Python set difference (3d files minus ingested paths) |
| Check for re-ingestion | Compare last N entries against prior entries |
| Quick sanity check | `wc -l` delta on ingestion_log before/after |

## History

- 2026-06-22: First identified — naive `comm -23` showed 0 new files despite script correctly ingesting 4. Root cause: ingestion log contains 15,384 paths (10,612 outside 3-day window), making the full-log comparison misleading.
