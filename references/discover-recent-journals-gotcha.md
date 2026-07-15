# discover_recent_journals.py — gotchas & fixes

## Bug fixed 2026-07-13: silent skips of non-mentor run_id / generated_at journals
- **Symptom:** `discover_recent_journals.py --window-minutes 5` returned 0 even
  though a journal generated ~5 min before the nominal heartbeat start existed
  on disk.
- **Root cause:** `parse_ts()` only stripped `mentor-light-` / `mentor-deep-`
  prefixes, and the key-scan list omitted `generated_at`. Journals like
  `praxis-cron-20260713T053531Z.json` (uses `generated_at`; `run_id` prefix
  `praxis-cron-`) could not be timestamped → silently excluded.
- **Fix (in script):** `generated_at` added to the key scan; `parse_ts` now
  regex-extracts the embedded `YYYYMMDDThhmmssZ` token from ANY `run_id` prefix
  (`re.search(r"\d{8}T\d{6}Z", s)`), so future prefixes are covered too.
- **Lesson:** when a tight discovery window returns 0, VERIFY against the
  content timestamps of the newest candidate files before trusting it. A 0 can
  mean "genuinely empty" OR "discovery can't read the timestamp field." Read
  the newest candidates' actual timestamp fields directly when suspicious.

## Execution-time clock drift (cutoff measured at script runtime)
- The cutoff is computed inside the discover script at execution time:
  `cutoff = now - window`. Building the candidate list (`find -mmin -450`) and
  any prior setup consume wall-clock seconds/minutes. A journal generated within
  N minutes of the *nominal* heartbeat start can fall just outside the computed
  cutoff if execution drifted.
- **Observed 2026-07-13:** nominal start ~05:40, execution drifted to ~05:43,
  cutoff became 05:37:21, excluding a journal generated at 05:35:31 (within 5
  min of nominal but ~8 min before actual).
- **Mitigations (pick per context):**
  1. **Catch-up-since-last-heartbeat:** filter candidates to
     `content_ts > last mentor-light evidence timestamp`. Guarantees no gap;
     correct heartbeat semantics when cadence > window.
  2. **Widen the window** a few minutes to absorb drift (e.g. 8–10 instead of 5).
     Cheap; ingestion is idempotent so over-inclusion is harmless.
  3. **Capture nominal start** before any work and pass it as `now` — precise,
     more code.
- Ingestion is idempotent (re-ingestions harmless), so over-inclusion is safe;
  under-inclusion creates permanent gaps. When in doubt, widen.

## Always regenerate the candidate/input file
- A cron job may advertise a fixed input path (e.g. `/tmp/mentor_files_3d.txt`)
  that is STALE (dated previous day, wrong contents). Never trust a pre-existing
  `/tmp` input file in a cron heartbeat — regenerate it from a fresh `find` each
  run.
