# Session 2026-06-21 Dispatch #17 — Multi-Skill Dispatch, Heredoc Corruption

**Time:** 2026-06-21T20:25–20:30Z  
**Trigger:** Dispatcher detected 5 new journal files  
**Pipelines:** Forge + Mentor + Praxis

## What Happened

### Forge Scan
- Clean scan — no unprocessed vp_*.json or vd_*.json files
- Journal written: `forge-scan-20260621T203005Z.json`

### Mentor Light Heartbeat
- 4,475 dual-path 3-day files scanned
- 2 new files ingested (both mentor-light dispatches)
- All outcomes: success (2/2), 0 errors, 0 anomalies
- `active_skills_30d` correction: script reported 14 (stdin 3d count), corrected to 22 (dual-path 30d)
- Evidence: 3687 → 3690 (script record + correction record + dedup cleanup)

### Praxis Journal Ingest
- 4 new journals found since `last_ingest_run` (2026-06-21T20:22:15Z)
- All 4 were routine no-signals: 1 forge clean scan + 3 mentor-light heartbeats + 1 praxis self-ref
- 0 events recorded, cap at 12/12

## New Gotcha: `$VAR` Inside `'PYEOF'` Heredoc

**Problem:** When writing a correction evidence record via `python3 << 'PYEOF'`, the shell variable `$RUN_ID` was used inside the Python code as a string literal (`run_id = "$RUN_ID"`). Since the heredoc is single-quoted (`'PYEOF'`), the shell does NOT expand `$RUN_ID`. Python receives the literal string `$RUN_ID`.

**Result:** Evidence record written with `"run_id": "$RUN_ID"` — valid JSON but semantically corrupt.

**Detection:** `tail -1 evidence.jsonl` showed the literal `$RUN_ID` string.

**Fix:** Removed the corrupted tail line and re-wrote with the hardcoded value `mentor-light-20260621T202544Z`.

**Key Distinction:** This is different from gotcha #54 (env var returns empty string). Here the Python `open().write()` *succeeds* — the file grows by 1 line — but the *content* is wrong because the shell never expanded the variable.

**Prevention:** Never use shell variable interpolation (`$VAR`) inside single-quoted Python heredocs (`'PYEOF'`). Hardcode the value or compute it inside Python.

## Deduplication Note

The `gotchas-mentor.md` file had accumulated 3 duplicate #55a entries and 2 duplicate section headers. Cleaned up via `replace_all=true` patch — 4 replacements made.

## Cross-Pipeline Timing

Successfully captured `last_ingest_run` from Praxis state BEFORE running Mentor heartbeat, preventing the cross-pipeline state collision. The captured timestamp `2026-06-21T20:22:15.630770+00:00` was used for Praxis mtime discovery instead of re-reading the state file after Mentor updated it.
