# Gap Backfill Auto-Corrects Wrong Filenames

**Confirmed 2026-06-25 dispatch #104.**

When the `cron-heartbeat-light.py` script's `$(date)` rolls over between its internal calls, the script stdout reports a filename that doesn't match the actual file on disk. If the caller uses the stdout filename for third-wave mitigation, a wrong entry gets added to `journals_evaluated.jsonl`.

**The gap backfill auto-corrects this.** The subsequent Praxis gap backfill walk uses `os.walk()` to find actual files on disk. It discovers the real filename (which differs from the stdout claim) and adds it with `action_taken: "backfill"`. Result: both entries exist in the eval file:

- `ocas-mentor/2026-06-25/mentor-light-20260625T145011Z.json` → third-wave mitigation (wrong, from stdout)
- `ocas-mentor/2026-06-25/mentor-light-20260625T145111Z.json` → gap backfill (correct, from disk)

**The wrong-filename phantom entry is inert.** The dispatcher never lists that filename in its `new_files` output (because no file with that timestamp was ever written), so it will never be re-detected. No cleanup is needed.

**Implication:** If you discover a phantom entry in the eval file after a dispatch, do NOT attempt to remove it. It is harmless and attempting removal risks deleting the correct entry. Just verify that the correct filename is also present (via gap backfill) and move on.

**Related:** See `references/session-20260625-dispatch-104-mentor.md` for the full incident report.
