# Session 2026-06-16 Light Heartbeat — Routine Run, Path Confusion

**Run ID:** `mentor-light-20260616T032337Z`
**Timestamp:** 2026-06-16T03:23:37Z
**Profile:** indigo

## Summary

Routine light heartbeat. Script ingested 8 new files (4 self-referential ocas-mentor, 2 ocas-forge, 1 ocas-finch, 1 ocas-spot). Script evidence+ingestion writes silently failed (gotcha #23). Caller backup corrected both. New finding: backup evidence was initially written to commons path instead of profile path, requiring a second pass.

## Key Metrics

| Metric | Value |
|--------|-------|
| Files scanned (3d) | 2,306 |
| New files ingested (script) | 8 |
| Truly new files (cross-ref) | 10 first pass, 0 re-check |
| Active skills (30d) | 21 (corrected from 14) |
| Evaluation coverage | 0.381 |
| Gap detected | Yes (21.6 min) |
| Active anomalies | 0 |

## Path Confusion Incident

Backup evidence was written directly to commons path (`/root/.hermes/commons/data/mentor/`) instead of profile path (`/root/.hermes/profiles/indigo/commons/data/mentor/`). Commons sync then also copied script's wrong version (active_skills_30d=14). Two evidence lines for same run in commons — one wrong, one correct.

**Fix:** ALL caller writes MUST target profile path first. Commons receives data only via line-level set-difference sync. The profile path is the authoritative source.

## Gotchas Observed

- Gotcha #23: Script evidence+ingestion writes failed, journal succeeded
- Gotcha #29: active_skills_30d corrected 14 → 21
- #62 (new): Caller backup writes must target profile path, NOT commons
- Gotcha #60: Script dedup uses `file_path` key but ingestion log uses `file`