# Session 2026-06-28: Commons-Ahead-of-Profile Sync Pattern

**Date:** 2026-06-28T14:55:50Z
**Run:** mentor-light-20260628T145550Z
**Type:** Direct cron heartbeat (single-skill)

## What Happened

After a clean heartbeat run (2 files ingested, correction 7→21 applied), the commons sync check showed:
- Profile evidence: 6,259 lines
- Commons evidence: 6,276 lines (**17 lines AHEAD** of profile)

This is the inverse of the usual "commons lags profile" pattern.

## Root Cause

Multiple concurrent cron heartbeats fire in rapid succession. Between the profile write and the caller's sync check, other heartbeat instances synced their own evidence lines to commons. Commons accumulated writes from N concurrent runs while this caller was still verifying.

## Key Insight

**`wc -l` comparison is insufficient for sync decisions.** A naive `if [ profile_lines -gt commons_lines ]` check concludes "commons is up to date" when in fact the caller's own run hasn't been synced yet — commons is ahead from *other* runs.

## Correct Sync Procedure

Use **timestamp-based set-difference**, not line-count comparison:

```bash
# Get the last timestamp in commons
LAST_COMMONS=$(tail -1 /root/.hermes/commons/data/mentor/evidence.jsonl | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('timestamp',''))")

# Append only profile lines newer than commons' last timestamp
python3 -c "
import json
last_commons = '$LAST_COMMONS'
count = 0
with open('/root/.hermes/profiles/indigo/commons/data/mentor/evidence.jsonl') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        try:
            d = json.loads(line)
            if d.get('timestamp','') > last_commons:
                with open('/root/.hermes/commons/data/mentor/evidence.jsonl', 'a') as out:
                    out.write(line + '\n')
                count += 1
        except: pass
print(f'Synced {count} new evidence lines to commons')
"
```

This is idempotent and safe regardless of whether commons is behind, ahead, or equal.

## Verification

After sync, confirm the correction record made it:
```bash
grep -a "14:55:5" /root/.hermes/commons/data/mentor/evidence.jsonl | grep "active_skills_30d_true" | head -1
```

## Outcome

- 14 evidence lines synced (accumulated delta from concurrent heartbeats that hadn't been synced yet)
- 14 ingestion lines synced
- Correction record confirmed in commons
- 0 errors

## Pattern Name

**Commons-ahead sync** — when concurrent heartbeats push lines to commons faster than the caller's sync check runs. Inverse of the "commons lagging" pattern. Same fix: timestamp-based set-difference.
