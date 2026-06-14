# Evidence Schema Reference

## Current Schema: FLAT (canonical)

All evidence records written since 2026-06-09 use the **flat schema**:

```json
{
  "schema": "mentor-evidence-v2",
  "run_id": "mentor-light-20260614T021815Z",
  "timestamp": "2026-06-14T02:18:15+00:00",
  "heartbeat_type": "light",
  "total_files_3d": 888,
  "new_files_ingested": 6,
  "active_skills_30d": 21,
  "ocas_skills_30d": 21,
  "evaluation_coverage": 0.2857,
  "gap_detected": false,
  "active_anomalies": 0,
  "outcome": "success",
  "notes": "..."
}
```

**All metrics are top-level keys.** There is NO nested `metrics` wrapper.

## Legacy Schema: NESTED (deprecated)

~10 entries in evidence.jsonl (written before 2026-06-09) use a nested `metrics` wrapper:

```json
{
  "schema": "mentor-evidence-v2",
  "run_id": "...",
  "metrics": {
    "total_files_3d": 882,
    "new_files_ingested": 2,
    ...
  },
  "outcome": "success"
}
```

## Reading Evidence — Defensive Pattern

When reading evidence records, check both locations:

```python
d = json.loads(line)
# Flat (canonical)
new_files = d.get("new_files_ingested")
if new_files is None:
    # Nested (legacy)
    new_files = d.get("metrics", {}).get("new_files_ingested")
```

## Schema Drift Metric

As of 2026-06-14: 96 flat, 10 nested, 1 invalid out of 107 total entries.

The nested entries are legacy and will naturally age out. No migration needed — just handle both when reading.
