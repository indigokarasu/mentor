# Mandatory `active_skills_30d` Correction Workflow

**Why:** The `cron-heartbeat-light.py` script counts only files from its stdin pipe (3-day window, single path). This produces `active_skills_30d` of 9–14 instead of the true 18–22. The correction is MANDATORY every time the heartbeat runs, regardless of whether the script succeeded on all its writes.

**Confirmed:** 41+ times (2026-06-19 through 2026-06-25). The script has NEVER self-corrected.

## Workflow (after every light heartbeat)

```bash
# ALWAYS run this after the heartbeat script, even if script reports "success"
/usr/bin/python3 /root/.hermes/profiles/indigo/skills/ocas-mentor/scripts/correct_active_skills_30d.py
```

**Output:** `active_skills_30d correction: script=9 → true=22 (OCAS: 18)`

## Two evidence lines per heartbeat is the expected pattern

| Line | Source | `active_skills_30d` value | Purpose |
|------|--------|--------------------------|---------|
| 1 | `cron-heartbeat-light.py` | 9–14 (wrong) | Script's stdin-based count |
| 2 | `correct_active_skills_30d.py` | 22 (correct) | Caller's dual-path 30d count |

## Verification

```bash
# Check the last evidence record has the corrected value
python3 -c "
import json
with open('/root/.hermes/profiles/indigo/commons/data/mentor/evidence.jsonl') as f:
    lines = [json.loads(l) for l in f if l.strip()]
last = lines[-1]
print(f'active_skills_30d_true: {last.get(\"active_skills_30d_true\", \"MISSING\")}')
print(f'active_skills_30d_script: {last.get(\"active_skills_30d_script\", \"MISSING\")}')
"
```

## Field names in corrected evidence

- `active_skills_30d_true` — the corrected total count (all skills, 30-day)
- `active_skills_30d_true_ocas` — OCAS-only subset
- `active_skills_30d_script` — script's original (wrong) count

Do NOT look for `active_skills_30d` alone — that field contains the script's wrong value.
