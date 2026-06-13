# Dual-Path Journal Discovery Pattern

## Problem

Skill journals are split across two locations:
- `/root/.hermes/commons/journals/` (shared commons)
- `/root/.hermes/profiles/indigo/commons/journals/` (profile-scoped commons)

Scanning only one path produces incorrect active-skill counts (e.g., 14 instead of 35).

## Solution: Shell-Level Dual-Path Scan

```bash
# Step 1: Discover files in both locations
find /root/.hermes/commons/journals/ \
    -name "*.json" -mtime -3 \
    -not -path "*/.archive/*" -not -path "*/.quarantine/*" \
  > /tmp/mentor_files_shared.txt

find /root/.hermes/profiles/indigo/commons/journals/ \
    -name "*.json" -mtime -3 \
    -not -path "*/.archive/*" -not -path "*/.quarantine/*" \
  > /tmp/mentor_files_profile.txt

# Step 2: Merge, deduplicate, and pipe to parser
cat /tmp/mentor_files_shared.txt /tmp/mentor_files_profile.txt | sort -u \
    | python3 scripts/cron-heartbeat-light.py
```

## For Active-Skill Counting (30-day window)

```bash
find /root/.hermes/commons/journals/ \
    -name "*.json" -mtime -30 \
    -not -path "*/.archive/*" -not -path "*/.quarantine/*" \
  > /tmp/active_shared.txt

find /root/.hermes/profiles/indigo/commons/journals/ \
    -name "*.json" -mtime -30 \
    -not -path "*/.archive/*" -not -path "*/.quarantine/*" \
  > /tmp/active_profile.txt

# Extract unique skill names
cat /tmp/active_shared.txt /tmp/active_profile.txt | sort -u | python3 -c "
import sys, os
skills = set()
for line in sys.stdin:
    p = line.strip()
    parts = p.split('/')
    for i, part in enumerate(parts):
        if part == 'journals' and i+1 < len(parts):
            skill = parts[i+1]
            if skill not in ('.archive', '.quarantine', ''):
                skills.add(skill)
            break
print(len(skills))
"
```

## Why Not os.walk or subprocess.run?

In cron-triggered `terminal()` heredocs, Python's `os.walk()` and `subprocess.run(["find", ...])` silently return 0 results even when the filesystem is fully accessible via shell tools. Always use shell `find` piped to Python, never Python-native file discovery.

## Ingestion Dedup

The ingestion log stores absolute paths via `os.path.abspath()`. Since both `find` commands output absolute paths under different roots, the dedup check works correctly across both locations — a file at `/root/.hermes/commons/journals/ocas-elephas/run.json` and one at `/root/.hermes/profiles/indigo/commons/journals/ocas-elephas/run.json` are treated as distinct entries (which is correct since they are different files).
