# Dispatch #70 (2026-06-25): Dispatcher filename mismatch + Praxis journal eval gap

**Trigger:** `new_journals` — 1 new journal detected
**Dispatcher listed:** `ocas-mentor/2026-06-25/mentor-light-20260625T043956Z.json`
**Actual file on disk:** `mentor-light-20260625T044606Z.json` (different timestamp due to concurrent heartbeat overwriting)

## Key Pitfalls

### 1. Dispatcher filename ≠ actual filename (again)
The dispatcher's `new_files` listed `mentor-light-20260625T043956Z.json` — this file was already in `journals_evaluated.jsonl` (evaluated by a concurrent Praxis heartbeat ~30s prior). The actual new journal written by the dispatch's Mentor run was `mentor-light-20260625T044606Z.json`. Pattern: the concurrent heartbeat wrote the file first, then the dispatch's own Mentor run wrote a new one with a later timestamp.

**Correct behavior:** Always use mtime-based discovery as ground truth. The dispatcher's `new_files` is a hint from the scan moment — concurrent heartbeats can supersede it.

### 2. Praxis dispatch journal NOT auto-added to eval file
After running the dispatch ingest template, the Praxis dispatch journal (`praxis-dispatch-20260625T044806Z.json`) was NOT in `journals_evaluated.jsonl`. The ingest script only evaluates source journals — it does not add its own output journal to the eval file. 

**Mandatory step:** After writing the Praxis dispatch journal, manually add it to `journals_evaluated.jsonl`:
```bash
echo '{"journal_id":"ocas-praxis/2026-06-25/praxis-dispatch-20260625T044806Z.json","evaluated_at":"ISO_NOW","action_taken":"dispatch_output_skip"}' >> /root/.hermes/profiles/indigo/commons/data/ocas-praxis/journals_evaluated.jsonl
```

This is distinct from third-wave mitigation for Mentor/Forge journals — those are handled by the ingest script's mtime discovery. The Praxis journal is written AFTER the ingest completes and is never caught by its own mtime scan.

## Pipeline Results
- **Forge:** 0 unprocessed proposals (all 10 in intake/processed). No-op journal.
- **Mentor:** 1061 files scanned, 3 ingested, correction 9→22 (OCAS: 18). Evidence synced.
- **Praxis:** 5 journals evaluated (mtime-based), 0 events, 1 gap backfill. Eval file at 38,084.
