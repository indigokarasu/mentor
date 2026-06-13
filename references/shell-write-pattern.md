# Mentor Heartbeat — Shell Write Pattern

## The Problem

In cron-triggered `terminal()` calls, Python `with open()` writes to persistent paths are **unreliable** — they sometimes persist and sometimes silently fail, depending on invocation context. Piped `find | python3` and inline `python3 -c` are most likely to fail; `python3 /path/to/script.py` (no pipe) has been observed to succeed. Treat Python writes as best-effort and verify with `wc -l`.

**Update 2026-06-06:** Python `with open()` writes from `python3 /path/to/script.py` (no pipe) successfully persisted evidence and ingestion records (evidence 139→140 lines, ingestion 6280→6284). The blanket "ALL writes fail" claim is overstated. However, shell-level writes remain the safest pattern — use them for critical evidence/journal records, and always verify persistence.

## The Only Reliable Method

Shell-level `echo >>`, `cat >`, and `cat file >> log` operations from `terminal()` DO persist.

## Patterns

### Append a JSON line to a log file

```bash
# PREFERRED: printf guarantees a trailing newline, preventing concatenation
printf '%s\n' '{"file": "/path/to/journal.json", "skill_name": "ocas-elephas", "ingested_at": "2026-06-05T05:47:00+00:00", "entries": 1}' >> /root/.hermes/commons/data/mentor/ingestion_log.jsonl

# ALSO OK: echo with explicit newline check
echo '{"file": "/path/to/journal.json"}' >> /root/.hermes/commons/data/mentor/ingestion_log.jsonl
# Then verify the last line is valid JSON:
tail -1 /root/.hermes/commons/data/mentor/ingestion_log.jsonl | python3 -c "import sys,json; json.loads(sys.stdin.read()); print('OK')"
```

### Write a full JSON file (journal, evidence)

```bash
cat > /root/.hermes/profiles/indigo/commons/journals/ocas-mentor/2026-06-05/20260605T054713Z.json << 'EOF'
{
  "schema": "mentor-journal-v2",
  "run_id": "mentor-light-20260605T054713Z",
  "timestamp": "2026-06-05T05:47:13+00:00",
  "heartbeat_type": "light",
  "metrics": {"new_files_ingested": 9, "errors": 0},
  "outcome": "success"
}
EOF
```

### Append multiple prepared lines from a temp file

```bash
# Python writes lines to /tmp/ (tmp writes DO work)
python3 << 'PYEOF' > /tmp/mentor_ingest_lines.txt
import json, os
# ... compute records ...
for r in records:
    print(json.dumps(r))
PYEOF

# Shell appends them to persistent log
cat /tmp/mentor_ingest_lines.txt >> /root/.hermes/commons/data/mentor/ingestion_log.jsonl
```

### Verify persistence

```bash
wc -l /root/.hermes/commons/data/mentor/ingestion_log.jsonl
wc -l /root/.hermes/commons/data/mentor/evidence.jsonl
```

## What Does NOT Work

| Method | Persists? | Notes |
|--------|-----------|-------|
| `python3 -c "with open(...)"` | ❌ | Silent failure |
| `find \| python3 script.py` | ❌ | Silent failure |
| `python3 /path/to/script.py` | ⚠️ Intermittent | Sometimes persists, sometimes silently fails. No pipe makes it MORE reliable than piped variants, but still not guaranteed. Verify with `wc -l` after every run. |
| `echo >> file` | ✅ | Reliable |
| `cat > file << 'EOF'` | ✅ | Reliable |
| `cat tmpfile >> file` | ✅ | Reliable |
| Python write to `/tmp/` | ✅ | /tmp is exempt |

## Workflow for Heartbeat Ingestion

1. **Discover files:** `find ... -name "*.json" -mtime -3 ... > /tmp/mentor_files.txt`
2. **Parse journals:** Python reads and parses, writes results to `/tmp/mentor_parse_results.json`
3. **Prepare ingestion lines:** Python writes JSON lines to `/tmp/mentor_ingest_lines.txt`
4. **Append to persistent log:** `cat /tmp/mentor_ingest_lines.txt >> ingestion_log.jsonl`
5. **Write evidence:** Use Python to construct the full JSON and write to `/tmp/`, then shell-append. **Never use `bc -l` or shell arithmetic to compute float values for JSON** — `bc` omits leading zeros (`.0285` instead of `0.0285`), producing invalid JSON. The safe pattern:
    # ALSO OK but requires validation: Write evidence JSON to /tmp/, then shell-append
    # WARNING: json.dump(record, f) with indent=None (default) produces single-line JSON — OK
    # WARNING: json.dump(record, indent=2) or json.dumps(record, indent=2) produces MULTI-LINE JSON — CORRUPTS JSONL
    # ALWAYS validate with `wc -l` before appending to any JSONL file
    python3 -c "
    import json
    from datetime import datetime, timezone
    record = {
        'schema': 'mentor-evidence-v2',
        'run_id': 'mentor-light-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'heartbeat_type': 'light',
        'metrics': {'total_files_3d': 931, 'new_files_ingested': 5, 'active_skills_30d': 35,
                    'evaluation_coverage': round(1/35, 4), 'gap_detected': False, 'active_anomalies': 0},
        'outcome': 'success',
        'notes': 'Backup via shell.'
    }
    # CRITICAL: Use json.dumps (NOT json.dump with indent) to ensure single-line output
    with open('/tmp/evidence_backup.json', 'w') as f:
        f.write(json.dumps(record) + '\n')
    print('Evidence JSON written to /tmp')
    "
    # VALIDATE before appending: /tmp file must be exactly 1 line
    if [ "$(wc -l < /tmp/evidence_backup.json)" -eq 1 ]; then
        cat /tmp/evidence_backup.json >> /root/.hermes/commons/data/mentor/evidence.jsonl
    else
        echo "ERROR: /tmp/evidence_backup.json has multiple lines — would corrupt JSONL. Abort."
        exit 1
    fi
    ```
    Then verify: `tail -1 evidence.jsonl | python3 -c "import sys,json; json.loads(sys.stdin.read()); print('OK')"`
6. **Write journal:** `cat > journals/ocas-mentor/YYYY-MM-DD/run.json << 'EOF'`
7. **Verify:** `wc -l` all persistent files to confirm deltas, then validate last line is parseable JSON:
   ```bash
   tail -1 evidence.jsonl | python3 -c "import sys,json; json.loads(sys.stdin.read()); print('OK')"
   tail -1 ingestion_log.jsonl | python3 -c "import sys,json; json.loads(sys.stdin.read()); print('OK')"
   ```

**CRITICAL: The light-heartbeat script attempts to write its own evidence record via Python `with open()`, but this write can silently fail (confirmed pattern: script reports N new files but evidence.jsonl and ingestion_log.jsonl both show 0 delta). **Partial success is possible (confirmed 2026-06-06T21:34Z):** evidence and ingestion writes can succeed while the journal write fails in the same run. The caller MUST verify persistence of ALL THREE files after the script exits AND must correct the `active_skills_30d` field.

**UPDATE 2026-06-13:** As of recent runs (2026-06-12 through 2026-06-13), multiple consecutive runs have succeeded on **first try** — all three writes (evidence, ingestion, journal) persisted without needing backup. The verify-and-backup workflow remains **mandatory** but the expected outcome has shifted from "dual failure is default" to "success on first try is now common." Do NOT skip verification — failure can return without warning. The pattern change appears to correlate with the cron sandbox stabilizing after the gateway outage resolution (2026-06-12).

**CRITICAL: ALL steps below MUST execute in a SINGLE `terminal()` call.** Shell variables (`EVIDENCE_BEFORE`, etc.) do not persist across `terminal()` calls — each call is a fresh shell. Splitting the workflow into multiple `terminal()` calls loses the pre-run baselines and makes delta verification impossible. Use a single compound shell block with `;` between steps or one heredoc. See gotcha #49.

```bash
# === MANDATORY: Pre-run counts ===
EVIDENCE_BEFORE=$(wc -l < /root/.hermes/commons/data/mentor/evidence.jsonl)
INGESTION_BEFORE=$(wc -l < /root/.hermes/commons/data/mentor/ingestion_log.jsonl)

# === Run the heartbeat script (with 3-day file list) ===
cat /tmp/mentor_files_3d.txt | python3 scripts/cron-heartbeat-light.py

# === MANDATATE: Post-run verification ===
EVIDENCE_AFTER=$(wc -l < /root/.hermes/commons/data/mentor/evidence.jsonl)
INGESTION_AFTER=$(wc -l < /root/.hermes/commons/data/mentor/ingestion_log.jsonl)

# === MANDATORY: Compute TRUE active_skills_30d (dual-path) ===
# The script's active_skills_30d reflects only its stdin (3-day files), NOT the true 30-day count.
TRUE_ACTIVE_30D=$(
  cat /tmp/active_shared.txt /tmp/active_profile.txt 2>/dev/null | sort -u | python3 -c "
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
)

# === MANDATORY: Write backup evidence if script's write failed ===
if [ "$EVIDENCE_AFTER" -eq "$EVIDENCE_BEFORE" ]; then
    # Script self-journaling failed — write corrected evidence via shell
    TRUE_NEW=$((INGESTION_AFTER - INGESTION_BEFORE))
    # If ingestion also failed, use cross-referenced count from /tmp/mentor_truly_new.txt
    if [ "$TRUE_NEW" -eq 0 ] && [ -f /tmp/mentor_truly_new.txt ]; then
        TRUE_NEW=$(wc -l < /tmp/mentor_truly_new.txt)
    fi
    printf '%s\\n' "{\"schema\":\"mentor-evidence-v2\",\"run_id\":\"$RUN_ID\",\"timestamp\":\"$TIMESTAMP\",\"heartbeat_type\":\"light\",\"metrics\":{\"total_files_3d\":$TOTAL_3D,\"new_files_ingested\":$TRUE_NEW,\"active_skills_30d\":$TRUE_ACTIVE_30D,\"ocas_skills_30d\":$TRUE_OCAS_30D,\"evaluation_coverage\":0,\"gap_detected\":false,\"active_anomalies\":0},\"outcome\":\"success\",\"notes\":\"Script self-journaling failed (0 delta); backup written via shell. active_skills_30d corrected from stdin-count to true dual-path 30d count.\"}" >> /root/.hermes/commons/data/mentor/evidence.jsonl
fi

# === MANDATORY: If ingestion_log also didn't grow but we have truly new files ===
if [ "$INGESTION_AFTER" -eq "$INGESTION_BEFORE" ] && [ -f /tmp/mentor_truly_new.txt ]; then
    # Write ingestion records for truly new files via shell
    python3 -c "
import json, os
from datetime import datetime, timezone
now = datetime.now(timezone.utc).isoformat()
lines = []
with open('/tmp/mentor_truly_new.txt') as f:
    for line in f:
        p = line.strip()
        parts = p.split('/')
        skill = 'unknown'
        for i, part in enumerate(parts):
            if part == 'journals' and i+1 < len(parts):
                skill = parts[i+1]
                break
        entry_count = 0
        try:
            with open(p) as jf:
                data = json.load(jf)
                entry_count = len(data) if isinstance(data, list) else 1
        except: pass
        lines.append(json.dumps({'file': p, 'skill_name': skill, 'ingested_at': now, 'entries': entry_count}))
with open('/tmp/mentor_ingest_backfill.txt', 'w') as out:
    for l in lines:
        out.write(l + '\n')
"
    cat /tmp/mentor_ingest_backfill.txt >> /root/.hermes/commons/data/mentor/ingestion_log.jsonl
fi

# === MANDATORY: Verify final state ===
tail -1 /root/.hermes/commons/data/mentor/evidence.jsonl | python3 -c "import sys,json; json.loads(sys.stdin.read()); print('Evidence OK')" || echo "EVIDENCE CORRUPT"
tail -1 /root/.hermes/commons/data/mentor/ingestion_log.jsonl | python3 -c "import sys,json; json.loads(sys.stdin.read()); print('Ingestion OK')" || echo "INGESTION CORRUPT"
echo "Final: evidence=$EVIDENCE_AFTER ingestion=$INGESTION_AFTER active_skills_30d=$TRUE_ACTIVE_30D"
```

**The `active_skills_30d` correction is NOT optional.** Without it, the evidence record will report ~15 (the number of unique skills that happened to have journals in the last 3 days) instead of the true 35 (all skills active in the last 30 days). This makes evaluation_coverage artificially high and misleading.

If the count did change, do NOT append a duplicate entry. See `references/gotchas-mentor.md` gotcha #26–28.

## Path Normalization for Ingestion Dedup

The ingestion log stores paths in TWO formats: (a) relative `ocas-xxx/YYYY-MM-DD/file.json` and (b) absolute `/root/.hermes/commons/journals/ocas-xxx/...`. Profile-scoped paths use `/root/.hermes/profiles/indigo/commons/journals/ocas-xxx/...`. A naive `comm` between `find` output and ingestion log will show 800+ false "new" files. Fix:

```bash
# Extract and normalize all ingested paths to absolute
python3 -c "
import json
paths = set()
with open('/root/.hermes/commons/data/mentor/ingestion_log.jsonl') as f:
    for line in f:
        try:
            d = json.loads(line)
            src = d.get('source') or d.get('file', '')
            if src:
                if not src.startswith('/'):
                    src = '/root/.hermes/commons/journals/' + src
                paths.add(src)
        except: pass
for p in sorted(paths):
    print(p)
" > /tmp/ingested_paths.txt

# Now comm works correctly
comm -23 <(sort /tmp/mentor_files_3d.txt) <(sort /tmp/ingested_paths.txt) > /tmp/new_files_3d.txt
```

## Active Skills 30d — OCAS-Only Count

The dual-path 30-day `find` returns ALL skill directories (289+), not just OCAS skills. For `evaluation_coverage` denominator, filter to ocas-* prefixes:

```bash
ACTIVE_OCAS_30D=$(find /root/.hermes/commons/journals/ /root/.hermes/profiles/indigo/commons/journals/ -name "*.json" -mtime -30 2>/dev/null | grep -oP 'ocas-[a-z]+' | sort -u | wc -l)
```

## Pipe Truncation Cross-Reference

When `find | python3 script.py` reports N new files but you need the ground truth:

```bash
# 1. Get all candidate files (dual-path, deduped)
cat /tmp/mentor_files_shared.txt /tmp/mentor_files_profile.txt | sort -u > /tmp/mentor_files_3d.txt

# 2. Count how many are already in ingestion log
ALREADY_INGESTED=$(python3 -c "
import json, os
ingested = set()
with open('/root/.hermes/commons/data/mentor/ingestion_log.jsonl') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        try:
            rec = json.loads(line)
            fp = rec.get('file', '')
            if fp.startswith('/'): ingested.add(fp)
            elif fp.startswith('commons/'): ingested.add(os.path.join('/root/.hermes/profiles/indigo', fp))
            else: ingested.add(os.path.abspath(fp) if fp else fp)
        except: pass
new_count = 0
with open('/tmp/mentor_files_3d.txt') as f:
    for line in f:
        p = line.strip()
        canonical = p if p.startswith('/') else os.path.abspath(p)
        if canonical not in ingested: new_count += 1
print(new_count)
")

TOTAL_3D=$(wc -l < /tmp/mentor_files_3d.txt)
TRUE_NEW=$ALREADY_INGESTED
echo "Total 3d: $TOTAL_3D | Already ingested: $((TOTAL_3D - TRUE_NEW)) | True new: $TRUE_NEW"
```

If `TRUE_NEW` > script's reported count, backfill the missing ingestion records via the `/tmp/mentor_ingest_backfill.txt` pattern (see step 4 in the Workflow section above — write records via Python to `/tmp/`, then `cat >>` to persistent log).

Each step uses shell for the persistent write. Python is used only for computation, writing to `/tmp/`.
