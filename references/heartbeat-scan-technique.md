# Heartbeat Journal Scan — Scalable Technique

## Problem

The journals directory can contain 5000+ JSON files across 100+ skill subdirectories. Naive `os.walk`-based scanning in Python:
- Silently produces wrong counts (timing out before reaching all dirs)
- Consumes excessive memory loading every inode
- Takes 30-60s+ for a full scan

## Solution: Use `find` for Active-Skill Counting

```python
import subprocess

result = subprocess.run(
    ["find", journals_dir, "-name", "*.json", "-mtime", "-30", "-type", "f"],
    capture_output=True, text=True, timeout=60
)
recent_files = [f for f in result.stdout.strip().split("\n") if f]

active_skills = set()
for f in recent_files:
    rel = os.path.relpath(f, journals_dir)
    skill = rel.split("/")[0]
    if skill and skill != ".archive":
        active_skills.add(skill)
```

This returns in <5s even with 5000+ files.

## Key Details

- **Always filter `.archive`** — It contains stale skill journals that inflate counts
- **Filter empty skill names** — `os.path.basename()` on dirs with trailing `/` returns `""`
- **Total dir counting**: Use `glob.glob(f"{journals_dir}/*/*")` and extract unique parent basenames, NOT `glob.glob(f"{journals_dir}/*/")` (basename of trailing-slash path is empty)
- **mtime threshold**: `-30` for active-skill counting, `-1` for "today" checks

## Ingestion Log Deduplication

The ingestion log has ~52K entries for ~30K unique run_ids (duplicates from re-ingestion). Build the dedup set at script start:

```python
ingested = set()
for line in open(ingestion_log_path):
    line = line.strip()
    if not line:
        continue
    try:
        rec = json.loads(line)
        ingested.add(rec.get("run_id", ""))
    except:
        pass
```

Then check `run_id not in ingested` before processing each file. Use the filename (not path) as the run_id — it's the unique key.

## Anomaly Deduplication

When resolving old anomalies for the same `(type, skill)` pair:
1. Parse the anomaly `timestamp` field
2. Only resolve entries whose timestamp is **before** the current run's start time
3. Never resolve an entry written in the same heartbeat pass — it's new data, not a duplicate
