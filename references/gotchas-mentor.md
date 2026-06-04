# Mentor — Full Gotcha Catalog

## Heartbeat Execution

1. **`outcome`/`status` can be str OR dict** — Always `isinstance(outcome, str)` before using as dict key. `TypeError: unhashable type: 'dict'` will crash if you skip this.
2. **Most journals (~80–90%) lack explicit `outcome` fields** — Default absent outcomes to `success` when no `error` key is present. Tag with `outcome_reporting_rate`.
3. **`duration_ms` vs `duration_seconds` naming varies** — Values < 100 are likely seconds → multiply by 1000.
4. **`run_id` can be empty string** — Use file path as fallback identifier for ingestion tracking.
5. **`error` can be str or dict** — Convert to string with `str()` before logging/truncating.
6. **Config may be incomplete** — Merge defaults on init, don't assume full schema.
7. **`evaluation_coverage` uses active-skill denominator** — Active = produced a journal in last 30 days. This OKR is informational, not pass/fail.

## Proposal and Anomaly Management

8. **Proposal stall loop** — If ≥3 consecutive proposals target same skill+issue without Fellow evaluation, write a VariantDecision with `auto_approved: true` or escalate. Stop re-proposing.
9. **Anomaly staleness** — Track anomalies across heartbeats. If unchanged for ≥5 consecutive heartbeats, add `stale: true` flag. Do not simply re-report identical anomalies.

## Cron Mode

10. **`execute_code` is blocked in cron mode** — All heartbeat processing MUST use `terminal()` with heredoc or inline Python.
11. **`execute_code` sandbox temp files are not persistent** — Write intermediate state to `{agent_root}/commons/data/ocas-mentor/tmp/`.
12. **Heartbeat gap logic for cron** — If gap > 15min (light) or > 24h (deep), note it and continue. Don't assume quiet hours unless 22:00-08:00 PT confirmed.
13. **Heartbeat gap >2h during active hours** — Check if gateway was down or job suppressed. See `references/heartbeat-gap-debugging.md`.

## Script Structure

14. **Cron-mode forward-reference guard** — Define ALL helper functions before `main()` in top-down Python scripts.
15. **F-string backslash escaping** — Cannot contain backslash-escaped quotes in `terminal(command="python3 -c '...'")`. Use `.format()` or write script to file first.

## Journal Schema

16. **Journal files come in THREE formats** — Not just `.json` vs `.jsonl`. Actual formats encountered:
    - `.jsonl`: one JSON dict per line (JSON Lines)
    - `.json` single object: multi-line pretty-printed dict (e.g., lucid journals)
    - `.json` array: multi-line JSON array of dicts
    - Corrupted/truncated: some `.json` files contain concatenated objects or truncated entries
    - Use the `load_journal_entries()` function from `scripts/cron-heartbeat-deep.py` which handles all three formats with a parse-fallback chain: try JSONL first, then single JSON, then array, then quarantine.

## Ingestion and Recovery

16a. **`ingestion_log.jsonl` can be empty while other state files exist** — Evidence, decisions, and OKR state may be present from prior runs while `ingestion_log.jsonl` has 0 entries (reset, truncation, fresh install). The file-hash+mtime dedup strategy still works for first-run catch-up, but the first heartbeat after a log reset will re-ingest everything. This is safe (idempotent) but time-consuming with 5000+ journal files.

16b. **File-mtime dedup means re-ingestion on file touch** — The dedup key `md5(filepath)_mtime` means touching or moving a journal file triggers re-ingestion. Acceptable for correctness, but bulk operations (like `find -exec touch`) will inflate counts.

## Scalability

17. **`os.walk` on journals directory is unreliable at scale** — With 5000+ journal files across 100+ skill dirs, `os.walk` can silently produce wrong counts or hit timeouts. Use `subprocess.run(["find", journals_dir, "-name", "*.json", "-mtime", "-30"])` for active-skill counting. It's faster and doesn't load every inode into Python memory.
18. **Active-skill counting must exclude `.archive`** — The `.archive/` directory under journals/ contains stale skill journals. Always filter `skill != ".archive"` when computing coverage denominators and active-skill sets.
19. **Anomaly dedup must not resolve same-run entries** — When deduplicating anomalies by `(type, skill)`, only resolve entries from *previous* runs. Entries written in the current heartbeat pass are new data, not duplicates. Check `timestamp` against the current run timestamp before resolving.
