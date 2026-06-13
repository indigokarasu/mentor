# Mentor Evidence Record Schema

## Flat Structure (as of v2.8.11+)

The `cron-heartbeat-light.py` script writes evidence records as **flat JSON objects** — there is no nested `metrics` wrapper.

### Schema

```json
{
  "timestamp": "2026-06-09T04:57:17.770106+00:00",
  "heartbeat_type": "light",
  "total_files_scanned": 1071,
  "new_files_ingested": 5,
  "new_entries": 5,
  "outcome_counts": {
    "completed": 1,
    "scan_complete_no_work": 1,
    "success": 3
  },
  "errors": 0,
  "error_skills": [],
  "skills_with_new_entries": 4,
  "active_skills_30d": 15,
  "evaluation_coverage": 0.2667,
  "gap_detected": false,
  "gap_minutes": 8.3,
  "active_anomalies": 0,
  "parse_failures": 0
}
```

### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | ISO 8601 UTC |
| `total_files_scanned` | int | All files from stdin (dual-path, 3-day) |
| `new_files_ingested` | int | Files not in ingestion_log |
| `active_skills_30d` | int | **WRONG in script output** — only counts skills in stdin (3d) |
| `evaluation_coverage` | float | Recalculate after fixing active_skills_30d |

## Required Corrections After Every Light Heartbeat

The script's `active_skills_30d` only reflects skills found in its stdin (3-day file list), NOT the true 30-day active count.

1. Compute true count via dual-path 30-day `find` (see `references/dual-path-journal-discovery.md`)
2. Correct: `record['active_skills_30d'] = true_count`
3. Recalculate: `record['evaluation_coverage'] = round(skills_with_new / true_count, 4)`

### Correct Python Access (FLAT schema)

```python
last['active_skills_30d'] = 35  # correct
last['evaluation_coverage'] = round(last['skills_with_new_entries'] / 35, 4)
```

### WRONG Access (will KeyError)

```python
last['metrics']['active_skills_30d'] = 35  # KeyError — no 'metrics' key
```

## File Locations

| File | Path |
|------|------|
| Evidence log | `/root/.hermes/commons/data/mentor/evidence.jsonl` |
| Ingestion log | `/root/.hermes/commons/data/mentor/ingestion_log.jsonl` |
| Anomalies | `/root/.hermes/commons/data/mentor/anomalies.jsonl` |
| Decisions | `/root/.hermes/commons/data/mentor/decisions.jsonl` |
| OKR state | `/root/.hermes/commons/data/mentor/okr_state.json` |
| Journals | `/root/.hermes/profiles/indigo/commons/journals/ocas-mentor/YYYY-MM-DD/` |
