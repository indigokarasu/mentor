# Dispatch #60 (2026-06-25): Multi-Skill + Taste, `new_files` Timestamp Mismatch Pitfall

**Time:** 02:08Z - 02:13Z

## Dispatch Trigger
- `new_journals`: 5 new files detected (latest_mtime 1782352932, latest_ts 2026-06-25T02:02:12Z)
- `taste_new_data`: 2 signals detected

## Execution

### Phase 1 — Forge
- 0 unprocessed proposals/decisions
- No-op journal: `forge-scan-20260625T020850Z.json`

### Phase 2 — Mentor
- 1010 files scanned (dual-path)
- 2 ingested, 0 errors
- `active_skills_30d` correction: 9 → 22 (OCAS: 18)
- Evidence delta: +1, Ingestion delta: +2
- Journal: `mentor-light-20260625T020902Z.json` (actual filename — dispatcher said T020800Z)

### Phase 2.5 — Taste
- Token repair required: both accounts had timezone suffix (`+00:00`)
- 2 signals created: Next Level VG ($76.66), Lavash ($64.60) — both DoorDash
- Journal: `taste-scan-20260625T021045Z.json`

### Phase 3 — Praxis
- Dispatcher `new_files` grep returned 1 NOT_EVALUATED: `praxis-dispatch-20260625T015715Z.json`
- **False negative**: Python mtime discovery found 5 unevaluated journals; the praxis file WAS in eval file (line 37990, `self_referential_skip`) — grep on dispatcher's exact filename missed it because the eval entry format included the full path
- Actual unevaluated journals: 5 (all from this dispatch wave)
- 2 gap backfill entries
- 0 behavioral events
- Journal: `praxis-dispatch-20260625T021344Z.json`

## Key Pitfall: `new_files` Timestamp Mismatch → False "Not Evaluated"

### Problem
The dispatcher's `new_files` list contains filenames with timestamps that may differ from the actual files on disk due to `$(date)` rollover between the dispatcher's scan and the journal's write. When Praxis naively greps the dispatcher's stated filename against `journals_evaluated.jsonl`:

1. **False negative**: A journal IS in the eval file but under the actual filename (e.g., `mentor-light-20260625T020902Z.json`) — the dispatcher's stated filename (`mentor-light-20260625T020800Z.json`) doesn't match → Praxis thinks it's unevaluated → duplicate re-ingestion risk
2. **False positive**: A journal is listed in `new_files` and IS in the eval file under the dispatcher's filename, but the actual file on disk has a different timestamp → the eval entry doesn't correspond to the real file

### Root Cause
The `cron-heartbeat-light.py` script calls `datetime.now()`/`strftime()` twice internally: once for the `run_id` field, once for the filename. If the clock rolls over between these calls, the filename timestamp differs from the `run_id` timestamp. The dispatcher captures the file by its filename, but the eval file may reference the `run_id`-based timestamp or vice versa.

### Mandatory Fix
1. **Always use mtime-based discovery** as ground truth for Praxis ingest (never dispatcher's `new_files` list)
2. **After finding unevaluated journals via mtime**, extract actual filenames from disk, then `grep <actual_filename>` against eval file
3. **Never grep dispatcher's stated filename** directly — it may be off by seconds/minutes

### Confirmed
- Dispatcher listed `mentor-light-20260625T020800Z.json` but actual file was `mentor-light-20260625T020902Z.json` (62-second discrepancy)
- Dispatcher listed `praxis-dispatch-20260625T015715Z.json` — this WAS in eval file (line 37990) but naive grep on the full path returned false because the eval entry format used the path as-is

## System State
- Eval file: 37,999 entries
- `last_ingest_run`: 2026-06-25T02:13:23.724810+00:00
- Gap backfill: 2 (stable, down from 14,772 on prior wave — the large backfill was from accumulated prior-wave journals)
- All pipelines clean
