# Dispatch #27 — Mentor Component (2026-06-23)

**Run ID:** mentor-light-20260623T201747Z
**Timestamp:** 2026-06-23T20:17:47Z
**Trigger:** Dispatcher (multi-skill dispatch #27)

## Results

| Metric | Value |
|--------|-------|
| Files scanned | 4,224 |
| New files ingested | 4 |
| Active skills (30d) — script | 11 |
| Active skills (30d) — corrected | 22 (OCAS: 18) |
| Evaluation coverage | 0.18 |
| Errors | 0 |

## Key Correction Pitfall

The correction script `correct_active_skills_30d.py` writes evidence with non-standard field names:
- `active_skills_30d_script` — the script's wrong stdin-based count (11)
- `active_skills_30d_true` — the true dual-path 30-day count (22)
- `active_skills_30d_true_ocas` — OCAS-only true count (18)

It does NOT write a flat `active_skills_30d` field. When verifying the correction was applied, check for `active_skills_30d_true` — NOT `active_skills_30d`. Searching for `active_skills_30d` in the last evidence record will return the script's undercount from the first evidence line, not the corrected value from the second line.

Two evidence lines per heartbeat is the expected pattern (script's version + corrected version). Confirmed 25th+ time.
