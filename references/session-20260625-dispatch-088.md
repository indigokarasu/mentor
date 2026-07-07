**Dispatch #88 (2026-06-25):** Multi-skill + email triage. Steady-state with backlog catch-up.

### Pipelines
- **Forge:** 0 unprocessed proposals (28 total). No-op journal written. **Bug:** `python3 -c` with shell heredoc produced literal `{ts}` in filename — `forge-scan-{ts}.json` instead of `forge-scan-20260625T103916Z.json`. Fixed by renaming file after detection. Root cause: `$TS` inside Python f-string in `terminal()` was not expanded by shell because the outer `$TS` consumed the variable reference, leaving `{ts}` as literal text in the filename.
- **Mentor:** 1214 files scanned, 59 ingested, correction 9→22 (confirmation #36+). All 3 writes clean.
- **Praxis:** 5 journals evaluated (0 events), **15,106 gap backfill** (accumulated backlog from prior waves' dispatch-output journals). Eval file grew from ~38,000 to ~53,600 entries. This is the expected catch-up pattern when `last_ingest_run` was not advanced for multiple dispatch cycles.
- **Email:** 8 threads triaged, 0 escalations. ARGGER shipment confirmed via DHL (47-day supplier follow-up resolved — panel shipped Jun 25 with testing photos, tracking tomorrow).

### Key Pitfall: Python f-string `$VAR` in terminal() heredoc
When composing JSON files via `python3 -c "..."` inside `terminal()`, shell variable expansion interacts with Python f-strings. A pattern like:
```python
python3 -c "with open(f'$DIR/forge-scan-{TS}.json', 'w') as f: ..."
```
The shell sees `$DIR` and tries to expand it, but `{TS}` after the `$` is interpreted as bash brace expansion or literal text depending on context. The result is a file literally named `forge-scan-{ts}.json`.

**Fix:** Always use `write_file` to write the script to `/tmp/`, then invoke with `python3 /tmp/script.py`. This avoids all shell-Python string interpolation issues.

### Gap Backfill Pattern
Large gap backfill (>1000) indicates accumulated backlog from prior waves. After the archive directory discovery (dispatch #72, 14,941 entries), subsequent waves continued catching up on non-archive unevaluated journals (ocas-lucid dream journals, etc.). 15,106 entries in dispatch #88 suggests the backlog accumulated across multiple waves since the archive catch-up. This is expected recovery behavior — eval file will stabilize once all historical journals are backfilled.
