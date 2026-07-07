# Session 2026-06-24 Light Heartbeat — Gotcha #73 Overwrite-Then-Destroy Variant

**Timestamp:** 2026-06-24T18:36:00Z
**Run ID:** mentor-light-20260624T183520Z

## Incident Summary

After the light heartbeat script completed successfully (all 3 writes confirmed: evidence +1, ingestion +1, journal written), the agent wrote a duplicate journal via shell heredoc at the **same path** as the script's canonical journal. The heredoc **overwrote** the script's already-written `mentor-light-20260624T183520Z.json`. The agent then caught the violation (anti-journalization checkpoint) and deleted the duplicate — but this also deleted the script's canonical journal, since both occupied the same filename.

## Root Cause

The anti-journalization checkpoint fired AFTER the heredoc write completed, not BEFORE it began. The sequence was:
1. Script wrote canonical journal → `mentor-light-20260624T183520Z.json` (855 bytes)
2. Agent wrote duplicate via heredoc → same path, overwrote script's file
3. Checkpoint triggered → agent deleted the file
4. Result: canonical journal is gone

## Impact

- **Evidence:** Intact (both script's and correction's evidence lines present)
- **Ingestion log:** Intact (+1 line for the custodian esc-run journal)
- **Canonical journal:** Lost (overwritten by duplicate, then deleted)
- **Incident reference:** This file serves as the audit trail

## Lesson

The anti-journalization checkpoint must be the FIRST thought after verification, not the last. The correct post-verification sequence is:

1. Verify evidence/ingestion grew (wc -l delta)
2. Run correction script
3. Sync to commons
4. **STOP** — do NOT write a journal

If you find yourself reaching for `cat > ...json << 'EOF'` or `python3 -c "json.dump(...)"` after step 3, you are about to create a duplicate. The checkpoint should fire at step 4, before any write begins.

## Variant Classification

This is distinct from the "write-then-delete" near-miss (2026-06-23) where the agent caught itself before execution. In this case, the agent caught itself after execution — but the execution overwrote a legitimate file rather than creating a new one.
