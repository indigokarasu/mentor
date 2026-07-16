# CRITICAL: Use `write_file` to write script to `/tmp/` then invoke as `python3 /tmp/script.py` for backup writes — Shell `<< 'PYEOF'` heredocs in `terminal()` trigger background detection (exit_code=-1). The safe pattern for writing evidence/ingestion backups is:
```bash
# Write the Python script to /tmp/ first (via write_file tool), then:
python3 /tmp/mentor_write_evidence.py
```
NEVER use `python3 << 'PYEOF'` inside `terminal()` — the `<<` heredoc delimiter triggers background detection. For simple appends, `echo >> file` or `printf '%s\n' '...' >> file` are reliable.

# ANTI-JOURNALIZATION HARD GATE (VIOLATED 2026-06-28 AND 2026-06-29)
After the heartbeat script completes and all three writes (evidence, ingestion, journal) are verified:

**DOUBLE-CHECK: Did YOU (the caller) already write a journal this run?**
Check: `ls "$JOURNAL_DIR" | grep "mentor-light-" | wc -l`
If the count is ≥1 BEFORE you attempt any journal write, **STOP. DO NOT WRITE.**

The script ALWAYS writes its own journal. The canonical journal ALREADY EXISTS after step 2 completes.
Your job after verification is: correct active_skills_30d → sync commons → **DONE**.

Two failure modes (BOTH observed in production):
1. **Duplicate journal (2026-06-29):** Caller wrote `mentor-light-20260629T005540Z.json` AFTER the script's `mentor-light-20260629T005139Z.json` already existed. Caught and deleted, but only AFTER the violation. The checkpoint said "resist" but the agent rationalized it as "mandatory."
2. **Overwrite-then-destroy (2026-06-28):** Caller overwrote script's canonical journal via heredoc at the SAME filename.

**HARD RULE: After step 2 (script execution) completes, the caller must NEVER invoke any write to `$JOURNAL_DIR`. No json.dump(), no heredoc, no `cat >`, no `python3 -c "open(...)"`. If you find yourself constructing a journal filepath — STOP. The heartbeat is OVER. Additional context goes in the EVIDENCE RECORD (via correct_active_skills_30d.py), NEVER a journal file.**

**CRITICAL: Journal directory date must use UTC** — Use `date -u +%Y-%m-%d` for `JOURNAL_DIR`, NOT `date +%Y-%m-%d` (which uses local time). The `run_id` is UTC-based, so the directory must be too. A mismatch puts the journal in yesterday's directory and creates confusion during cross-reference.

- ~~**Script journal filename missing `mentor-light-` prefix**~~ **FIXED 2026-06-08**: Script line 264 changed to use `f"mentor-light-{run_id}.json"`. Filename now matches the `run_id` field. Confirmed working as of 2026-06-08T22:46Z. `run_id = now.strftime("%Y%m%dT%H%M%SZ")` (just the timestamp), then line 264 writes to `f"{run_id}.json"` producing e.g. `20260607T045155Z.json`. But the journal's `run_id` *field* (line 249) is `f"mentor-light-{run_id}"` = `mentor-light-20260607T045155Z`. The filename doesn't match the `run_id` inside the file. Fix: change line 264 to `f"mentor-light-{run_id}.json"` or compose `run_id` with the prefix from the start. See run 2026-06-07T04:51Z for confirmation.

- **Partial success is possible (confirmed 2026-06-06T21:34Z and 2026-06-07T03:38Z):** Evidence and ingestion writes can succeed while the journal write fails in the same run — or vice versa. The three writes are independent. The verify-and-backup workflow must check ALL THREE files (`evidence.jsonl`, `ingestion_log.jsonl`, and the journal directory) independently. Do NOT assume that because evidence grew, the journal was also written.

- **Verify current live state before acting on escalated issues.** Custodian journals flag `escalation_needed: true` but the underlying issue may have already been resolved (user re-authorized, plugin bug fixed, transient error self-resolved). Before executing any fix: (1) check the job's current `last_status` in jobs.json, (2) check the latest esc-run journal, (3) verify the error still appears in logs. Do not trust the escalation flag alone. Confirmed 2026-06-17: 3 out of 4 escalated issues were already resolved. Note: Custodian flags `escalation_needed: true` on virtually every scan as part of its tiered escalation model (surfaces tier-2 issues for planning regardless of whether user action is needed). Check mtime: if all escalation journals are >48h old and from `ocas-custodian/`, they are historical operational noise, not fresh alerts (140-journal false-alarm pattern, 2026-06-19). See gotcha #63.

**`grep` on large JSONL files reports "binary file matches"** — Use `grep -a` to force text mode on evidence.jsonl and ingestion_log.jsonl. See gotcha #77.

**MANDATORY verify-and-backup workflow after every light heartbeat (SINGLE terminal() call):**
```bash
# ALL steps MUST be in ONE terminal() call — shell variables don't persist across calls.
# See gotcha #49.
# CRITICAL: Use PROFILE paths for all evidence/ingestion checks (gotcha #62).
# The profile path is authoritative; commons is a lagging copy.

# 1. Record pre-run counts (PROFILE path, not commons)
EVIDENCE_BEFORE=$(wc -l < /root/.hermes/profiles/indigo/commons/data/mentor/evidence.jsonl)
INGESTION_BEFORE=$(wc -l < /root/.hermes/profiles/indigo/commons/data/mentor/ingestion_log.jsonl)
JOURNAL_DIR="/root/.hermes/profiles/indigo/commons/journals/ocas-mentor/$(date -u +%Y-%m-%d)"

# 2. Run the script
python3 scripts/cron-heartbeat-light.py < /tmp/mentor_files_3d.txt

# 3. Verify ALL THREE files independently (partial success is possible)
EVIDENCE_AFTER=$(wc -l < /root/.hermes/profiles/indigo/commons/data/mentor/evidence.jsonl)
INGESTION_AFTER=$(wc -l < /root/.hermes/profiles/indigo/commons/data/mentor/ingestion_log.jsonl)
RECENT_JOURNAL=$(find "$JOURNAL_DIR" -name "mentor-light-*.json" -mmin -5 2>/dev/null | head -1)

# 4. If evidence didn't grow, write backup via shell to PROFILE path
if [ "$EVIDENCE_AFTER" -eq "$EVIDENCE_BEFORE" ]; then
    printf '%s\\n' '{...evidence json...}' >> /root/.hermes/profiles/indigo/commons/data/mentor/evidence.jsonl
fi

# 5. If ingestion didn't grow, write backup ingestion records via shell to PROFILE path
if [ "$INGESTION_AFTER" -eq "$INGESTION_BEFORE" ]; then
    # Compute true new files and write ingestion records
    # See references/shell-write-pattern.md for the full pattern
fi

# 6. If no recent journal file exists, the script's journal write failed
if [ -z "$RECENT_JOURNAL" ]; then
    echo "WARNING: No recent journal in $JOURNAL_DIR — script's journal write silently failed."
    # Write backup journal via shell (see references/shell-write-pattern.md)
fi

# IMPORTANT: $JOURNAL_DIR must use UTC date: JOURNAL_DIR="/root/.hermes/profiles/indigo/commons/journals/ocas-mentor/$(date -u +%Y-%m-%d)"
# Using local date puts the journal in the wrong directory when server TZ != UTC.
# DO NOT write a separate caller journal — the script's journal is canonical (gotcha #73).
#
# ██ ANTI-JOURNALIZATION CHECKPOINT (VIOLATED 2026-06-28) ██
# After verification is complete, you will feel an urge to write a "proper" journal.
# RESIST. The script already wrote the canonical journal. TWO failure modes:
# 1. Writing a SECOND journal (different run_id) → duplicates that inflate ingestion.
# 2. Overwriting the SCRIPT'S journal with heredoc (same filename) → DESTROYS canonical record.
# CONFIRMED 2026-06-28: caller overwrote script's journal via heredoc — same filename.
# RULE: After verifying the journal exists on disk, DO NOT write ANY file to the
# journal directory. No heredoc, no json.dump(), no `cat >`. Period.
# The correct place for additional context is the evidence record, NOT a journal file.
```

**`correct_active_skills_30d.py` writes BOTH an evidence record AND its own journal.** The correction script produces a secondary journal file with a separate `run_id` (different timestamp than the main heartbeat journal). This is expected (not a duplicate) — the correction script's journal will appear in future scans as a self-contained entity. Do NOT remove or suppress it; it provides an audit trail for the active skill counting decision. Two journals per heartbeat (main + correction) is the expected pattern from v2.8.23+.

**Light heartbeat caller MUST correct `active_skills_30d` AND write a complete evidence record — EVERY TIME, regardless of script success.** The script receives only `-mtime -3` files via stdin, so its `active_skills_30d` (typically 12–13) is NEVER the true 30-day active skill count (typically 18–21). This is not a failure condition — it is the expected behavior. The caller must compute the true count separately via a dual-path 30-day `find` (see `references/dual-path-journal-discovery.md`) and write a corrected evidence record with the true value. The script's evidence record will ALWAYS undercount. The caller's correction evidence record is NOT a backup or duplicate — it is the PRIMARY evidence. Two evidence lines per heartbeat is the expected pattern. See gotcha #29 and #58. Confirmed 2026-06-19: script can succeed on all 3 writes (evidence, ingestion, journal) and STILL produce a wrong `active_skills_30d`. The correction is mandatory, not conditional.

**Correction script field naming (confirmed 2026-06-23):** `correct_active_skills_30d.py` writes the corrected evidence with fields `active_skills_30d_true` and `active_skills_30d_true_ocas` (NOT `active_skills_30d`). When verifying the correction was applied, check for these field names — searching for `active_skills_30d` in the last evidence record will return the script's undercount (wrong) value, not the corrected one. The correction record also includes `active_skills_30d_script` showing the script's original (wrong) count.

**CRITICAL: Caller backup writes MUST target the profile path, NOT commons** — All caller-written evidence and ingestion records MUST be written to the profile-scoped data directory (`/root/.hermes/profiles/indigo/commons/data/mentor/`), NOT directly to `/root/.hermes/commons/data/mentor/`. The profile path is the authoritative source; commons is a lagging copy that receives data only via the line-level set-difference sync. Writing directly to commons creates duplicate or offset evidence lines — the script's version (with wrong `active_skills_30d`) gets synced from profile, then the caller's corrected version gets written directly to commons, producing two lines for the same run. See `references/session-2026-06-16-light-7.md` and gotcha #62.

**Commons sync must use timestamp-based set-difference, NOT line-count comparison (confirmed 2026-06-28):** When multiple concurrent heartbeats fire, commons can be AHEAD of profile (commons accumulated writes from sibling runs). A naive `if [ profile_lines -gt commons_lines ]` check falsely concludes "up to date" and skips sync. Use timestamp-based set-difference instead.

**CRITICAL: Do NOT use inline pipe-to-python patterns for commons sync** — `tail -1 ... | python3 -c "..."` is blocked by `tirith:pipe_to_interpreter` in cron mode (confirmed 2026-07-01). Write a sync script to `/tmp/` via `write_file` first, then execute it. This avoids both the tirith block and the fragile triple-quote escaping that the old inline pattern required.

Write the sync script via `write_file`:
```python
#!/usr/bin/env python3
"""Timestamp-based set-difference sync: profile -> commons for evidence and ingestion."""
import json

PROFILE_EVIDENCE = "/root/.hermes/profiles/indigo/commons/data/mentor/evidence.jsonl"
COMMONS_EVIDENCE = "/root/.hermes/commons/data/mentor/evidence.jsonl"
PROFILE_INGESTION = "/root/.hermes/profiles/indigo/commons/data/mentor/ingestion_log.jsonl"
COMMONS_INGESTION = "/root/.hermes/commons/data/mentor/ingestion_log.jsonl"

# --- Evidence sync (field: timestamp) ---
last_commons_ts = ""
with open(COMMONS_EVIDENCE) as f:
    for line in f:
        if not line.strip(): continue
        try:
            d = json.loads(line)
            ts = d.get("timestamp", "")
            if ts:
                last_commons_ts = ts
        except: pass

evidence_synced = 0
with open(PROFILE_EVIDENCE) as f:
    for line in f:
        if not line.strip(): continue
        try:
            d = json.loads(line)
            if d.get("timestamp", "") > last_commons_ts:
                with open(COMMONS_EVIDENCE, "a") as out:
                    out.write(line.rstrip() + "\n")
                evidence_synced += 1
        except: pass

print(f"Evidence sync: {evidence_synced} lines (last_commons_ts={last_commons_ts[:25] if last_commons_ts else 'none'})")

# --- Ingestion sync (field: ingested_at) ---
last_commons_ing = ""
with open(COMMONS_INGESTION) as f:
    for line in f:
        if not line.strip(): continue
        try:
            d = json.loads(line)
            ts = d.get("ingested_at", "")
            if ts:
                last_commons_ing = ts
        except: pass

ingestion_synced = 0
with open(PROFILE_INGESTION) as f:
    for line in f:
        if not line.strip(): continue
        try:
            d = json.loads(line)
            if d.get("ingested_at", "") > last_commons_ing:
                with open(COMMONS_INGESTION, "a") as out:
                    out.write(line.rstrip() + "\n")
                ingestion_synced += 1
        except: pass

print(f"Ingestion sync: {ingestion_synced} lines (last_commons_ing={last_commons_ing[:25] if last_commons_ing else 'none'})")
```

Then invoke in your single-terminal verify-and-backup workflow:
```bash
python3 /tmp/mentor_sync_commons.py
```

This is idempotent regardless of whether commons is behind, ahead, or equal. **IMPORTANT:** `ingestion_log.jsonl` uses `ingested_at` as its timestamp field, NOT `timestamp` (implemented in the script above). Using the wrong field name causes massive duplication. See `references/session-20260628-ingestion-sync-field-trap.md` for the original discovery.

**Ingestion sync field name trap (confirmed 2026-06-28):** `ingestion_log.jsonl` uses `ingested_at` as its timestamp field, NOT `timestamp`. The documented sync pattern above uses `d.get('timestamp','')` which returns empty string for ingestion records. This causes ALL profile lines to appear "new" relative to commons, duplicating the entire file. **Fix:** When syncing ingestion_log.jsonl, use `d.get('ingested_at','')` instead. Always verify the timestamp field name with `head -1 <file> | python3 -c "import sys,json; print(list(json.loads(sys.stdin.read()).keys()))"` before writing sync logic for any new JSONL file. See `references/session-20260628-ingestion-sync-field-trap.md`.

**Commons ingestion_log structural bloat (confirmed 2026-06-28):** The commons `ingestion_log.jsonl` is typically 2x the profile count (e.g. 37,734 commons vs 19,454 profile) due to: (1) historical records from other agent profiles (corvus, lucid, elephas) that live in commons but were never synced to indigo's profile, (2) ~18,000 legacy records with empty `file` field from schema variants across profiles, (3) duplicate ingestion records from pre-timestamp-sync era. This is expected structural accumulation — commons is a superset accumulator for all profiles. Do NOT investigate or attempt dedup. The profile-scoped file is the authoritative source for indigo's own ingestion state. This run's sync adds only the correct new lines via timestamp-based set-difference.

**`cron-heartbeat-light.py` `JOURNALS_DIR` constant is legacy/unused for output (confirmed 2026-07-13):** The script hardcodes `JOURNALS_DIR = "/root/.hermes/commons/journals"` at module top (line 9), which looks like it would make the heartbeat read/write against the legacy root. It does NOT. The script reads its journal file list from **stdin** (the `find ... > /tmp/mentor_files_3d.txt && python3 cron-heartbeat-light.py < /tmp/mentor_files_3d.txt` pattern) and writes its own journal to `JOURNAL_DIR = os.path.join(AGENT_ROOT, "commons", "journals", "ocas-mentor")` where `AGENT_ROOT = "/root/.hermes/profiles/indigo"` — i.e. the **profile-scoped** tree. The legacy `/root/.hermes/commons/journals/ocas-mentor/` holds only 1 stale file (2026-07-12); the 138 active `mentor-light-*` journals all live under the profile path. Do NOT conclude the script leaks stray journals into the legacy tree, and do NOT "fix" the script by changing `JOURNALS_DIR` (it is only referenced in the docstring/usage example, not in execution). The dual-path `find` (both commons + profile) is what feeds stdin — see `references/dual-path-journal-discovery.md`.

**Recommended skill counting technique (confirmed 2026-06-14):** Use `grep -oP` to extract unique skill names from journal file paths — avoids all edge cases of `awk -F/` on absolute paths (see gotcha #44a):
```bash
# OCAS-only count (fastest, most reliable)
ACTIVE_OCAS_30D=$(find /root/.hermes/commons/journals/ /root/.hermes/profiles/indigo/commons/journals/ -name "*.json" -mtime -30 2>/dev/null | grep -oP 'ocas-[a-z]+' | sort -u | wc -l)

# All skills count (OCAS + non-OCAS)
ACTIVE_ALL_30D=$(find /root/.hermes/commons/journals/ /root/.hermes/profiles/indigo/commons/journals/ -name "*.json" -mtime -30 2>/dev/null | grep -oP 'commons/journals/([a-z][a-z0-9_-]+)' | sed 's|commons/journals/||' | sort -u | wc -l)
```

**`active_anomalies` counting fixed in v2.8.10** — The light heartbeat script now uses `a.get("timestamp") or a.get("detected_at")` to correctly read anomalies regardless of which date field they use. Prior to v2.8.10, `active_anomalies` always reported 0 due to the field mismatch (gotcha #36).

**Light heartbeat caller MUST cross-reference ingestion counts** — The script's `new_files_ingested` is an upper bound. Pipe truncation (gotcha #26) and path normalization mismatches (gotcha #24) mean the script can report N while the true new-file count differs. After every heartbeat, cross-reference: `find ... -mtime -3 | sort -u` minus paths in `ingestion_log.jsonl`. If counts differ, note the discrepancy in the evidence record. Re-ingestions are harmless (idempotent).

**`cron-heartbeat-light.py` does NOT accept CLI arguments for file list — stdin redirect is the ONLY input method** — Invoking the script with `--files-from file.txt` or any other CLI argument silently produces 0 files scanned. Write file list to `/tmp/mentor_files_3d.txt` first, then use stdin redirect: `find ... | sort -u > /tmp/mentor_files_3d.txt && python3 /root/.hermes/profiles/indigo/skills/ocas-mentor/scripts/cron-heartbeat-light.py < /tmp/mentor_files_3d.txt`. Do NOT use `cat file | python3 script.py` — the pipe is blocked by `tirith:pipe_to_interpreter` in cron mode (confirmed 2026-07-01). Always use stdin redirect inside cron. See `references/gotcha-60-light-stdin.md`.

**Script stdout filename ≠ actual file on disk** — The `cron-heartbeat-light.py` script calls `datetime.now()`/`strftime()` twice internally: once for the `run_id` field inside the JSON content, and once for the filename. If the clock rolls over between these two calls (e.g. second boundary crossing), the `run_id` and filename timestamps will differ by up to 60 seconds (confirmed: 100-second difference on dispatch #104). Script stdout prints the `run_id`-based filename, but the file on disk has the filename-timestamp. **Fix:** After completing the heartbeat, `ls` the actual journal directory to get the real filenames, then `grep` those real filenames against `journals_evaluated.jsonl` — never trust the script's stdout filename claim. If you already added the wrong filename via third-wave mitigation, the subsequent gap backfill will add the correct filename automatically. Do NOT attempt to remove the wrong-filename phantom entry — it is inert and harmless. Confirmed 2026-06-25 dispatch #104: stdout said `T145011Z`, actual file was `T145111Z`, gap backfill auto-corrected.

**Gap backfill auto-catches correct filename (confirmed 2026-06-25 dispatch #104):** When third-wave mitigation adds a wrong-filename entry (from script stdout), the subsequent Praxis gap backfill walk finds the actual file on disk via `os.walk()` and adds it with the correct filename. The result: both entries exist in the eval file — the wrong-filename phantom (harmless, never re-detected because the dispatcher never lists that filename) and the correct-filename backfill entry. This is expected and safe — do NOT attempt to remove the phantom entry. Confirmed: third-wave added `mentor-light-T145011Z` (stdout), gap backfill added `mentor-light-T145111Z` (actual file). Both present, system healthy.

**Evidence record uses FLAT schema — no `metrics` wrapper** — The `cron-heartbeat-light.py` script writes evidence as a flat JSON object with top-level keys (`timestamp`, `heartbeat_type`, `total_files_scanned`, `new_files_ingested`, `errors`, `active_skills_30d`, `evaluation_coverage`, etc.). There is NO nested `metrics` dict. When writing backup evidence or correcting fields, use the flat schema. Accessing `record['metrics']['active_skills_30d']` will raise `KeyError`. Correct path: `record['active_skills_30d']`. Fixed 2026-06-09.

**Deep heartbeat is self-journaling:** `scripts/cron-heartbeat-deep-dualpath.py` writes its own journal entry. The caller must NOT append a separate journal entry for the same `run_id` — this produces duplicates.

**Deep heartbeat dual-path wrapper (2026-06-13):** Use `scripts/cron-heartbeat-deep-dualpath.py` instead of the stock `cron-heartbeat-deep.py`. The stock script only scans commons journals (168 files) while the dual-path wrapper scans both commons + profile-scoped journals (6,781 files). See `references/deep-heartbeat-dual-path.md` for the full fix details, metrics comparison, and usage instructions.

**Deep heartbeat journal filename double-prefix bug:** `cron-heartbeat-deep-dualpath.py` composes the journal filename as `f"mentor-deep-{run_id}.json"` where `run_id = f"deep-{timestamp}"`. The result is `mentor-deep-deep-2026-06-23T194032Z.json` — a double-prefix. This is a cosmetic issue in the script's journal writer (the `run_id` field inside the file is correct: `deep-2026-06-23T194032Z`). Fix: change the filename composition to `f"{run_id}.json"` since `run_id` already contains the `deep-` prefix. Confirmed 2026-06-23.

**Deep heartbeat caller MUST verify and backup writes** — The script writes evidence, decisions, OKR state, and proposals file via Python `with open()`, which silently fails in cron mode (same pattern as gotcha #27). The caller must verify all writes and back up via shell if missing. Confirmed 2026-06-24: script's evidence write succeeded but decisions.jsonl and proposals file were NOT written. Confirmed 2026-06-29: script's ingestion write silently failed (delta=0 despite 665 new files reported). The ingestion backup is the most critical deep heartbeat backup — use the `/tmp/mentor_deep_backup.py` pattern below.

**Deep heartbeat evidence uses `skills_active_30d` (NOT `active_skills_30d`)** — The `cron-heartbeat-deep-dualpath.py` script writes its evidence record with the field `skills_active_30d`, NOT `active_skills_30d`. When `correct_active_skills_30d.py` runs after a deep heartbeat, it reports `script=None` because it looks for `active_skills_30d` and doesn't find it. This is expected — the deep heartbeat counts differently (full scan vs stdin-based). The correction script still correctly computes the true 30d count from disk. Do NOT treat the `None` as an error. Confirmed 2026-06-29.

**Deep heartbeat proposals directory must exist** — The script writes to `commons/data/mentor/proposals/proposals-{date}.json` but the directory may not exist on first run (or after cleanup). The caller must `mkdir -p` the proposals directory before running the script, or the proposals write will fail silently. Confirmed 2026-06-29: proposals dir did not exist.

**Deep heartbeat caller verify-and-backup workflow (SINGLE terminal() call):**
```bash
# ALL steps in ONE terminal() call — shell variables don't persist across calls.

# 1. Ensure proposals directory exists
mkdir -p /root/.hermes/profiles/indigo/commons/data/mentor/proposals

# 2. Record pre-run counts (PROFILE path)
EVIDENCE_BEFORE=$(wc -l < /root/.hermes/profiles/indigo/commons/data/mentor/evidence.jsonl)
INGESTION_BEFORE=$(wc -l < /root/.hermes/profiles/indigo/commons/data/mentor/ingestion_log.jsonl)
DECISIONS_BEFORE=$(wc -l < /root/.hermes/profiles/indigo/commons/data/mentor/decisions.jsonl)
JOURNAL_DIR="/root/.hermes/profiles/indigo/commons/journals/ocas-mentor/$(date -u +%Y-%m-%d)"

# 3. Build dual-path file list (all journals, not just 3-day)
find /root/.hermes/commons/journals/ -name "*.json" -not -path "*/.archive/*" -not -path "*/.quarantine/*" > /tmp/mentor_deep_shared.txt
find /root/.hermes/profiles/indigo/commons/journals/ -name "*.json" -not -path "*/.archive/*" -not -path "*/.quarantine/*" >> /tmp/mentor_deep_shared.txt
sort -u /tmp/mentor_deep_shared.txt > /tmp/mentor_deep_files.txt

# 4. Run the script (stdin redirect, NOT pipe)
python3 /root/.hermes/profiles/indigo/skills/ocas-mentor/scripts/cron-heartbeat-deep-dualpath.py < /tmp/mentor_deep_files.txt

# 5. Verify ALL write targets independently
EVIDENCE_AFTER=$(wc -l < /root/.hermes/profiles/indigo/commons/data/mentor/evidence.jsonl)
INGESTION_AFTER=$(wc -l < /root/.hermes/profiles/indigo/commons/data/mentor/ingestion_log.jsonl)
DECISIONS_AFTER=$(wc -l < /root/.hermes/profiles/indigo/commons/data/mentor/decisions.jsonl)
RECENT_JOURNAL=$(find "$JOURNAL_DIR" -name "mentor-deep-*.json" -mmin -5 2>/dev/null | head -1)
echo "Evidence delta: $((EVIDENCE_AFTER - EVIDENCE_BEFORE))"
echo "Ingestion delta: $((INGESTION_AFTER - INGESTION_BEFORE))"
echo "Decisions delta: $((DECISIONS_AFTER - DECISIONS_BEFORE))"
echo "Recent journal: $RECENT_JOURNAL"

# 6. If ingestion didn't grow, back up via Python script
if [ "$INGESTION_AFTER" -eq "$INGESTION_BEFORE" ]; then
    echo "WARNING: Ingestion write failed — running backup"
    # Write backup script to /tmp/ and execute
    python3 /tmp/mentor_deep_backup.py  # See template below
fi

# 7. If evidence didn't grow, write backup evidence
if [ "$EVIDENCE_AFTER" -eq "$EVIDENCE_BEFORE" ]; then
    echo "WARNING: Evidence write failed — writing backup"
    python3 -c "
import json
from datetime import datetime, timezone
record = {
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'heartbeat_type': 'deep',
    'run_id': 'deep-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
    'journals_scanned': 0,  # Unknown in backup mode
    'journals_ingested': 0,
    'skills_evaluated': 0,
    'skills_total': 42,
    'skills_with_journals': 42,
    'skills_active_30d': 22,  # Use last known or recompute
    'evaluation_coverage': 1.0,
    'active_coverage': 0.45,
    'anomalies_detected': 0,
    'parse_errors': 0,
    'proposals_generated': 0,
    'gap_detected': False,
    'partial_success_evidence_write_failed': True,
    'note': 'Backup evidence — script evidence write failed silently in cron.'
}
with open('/root/.hermes/profiles/indigo/commons/data/mentor/evidence.jsonl', 'a') as f:
    f.write(json.dumps(record) + '\n')
"
fi

# 8. If no recent journal, the script's journal write failed
if [ -z "$RECENT_JOURNAL" ]; then
    echo "WARNING: No recent deep journal — script's journal write failed."
    # Deep journals are large; do NOT attempt caller backup of deep journal.
    # Log the failure in evidence instead.
fi

# 9. Run active_skills_30d correction (mandatory)
/usr/bin/python3 /root/.hermes/profiles/indigo/skills/ocas-mentor/scripts/correct_active_skills_30d.py

# 10. Sync to commons (timestamp-based set-difference)
# See commons sync pattern in main Cron-Mode Constraints section

# ██ ANTI-JOURNALIZATION CHECKPOINT ██
# The deep heartbeat script writes its own journal. DO NOT write a caller journal.
# Check: ls "$JOURNAL_DIR" | grep "mentor-deep-" | wc -l — if ≥1, STOP.
```

**Deep heartbeat ingestion backup script template** (write to `/tmp/mentor_deep_backup.py` via `write_file`):
```python
#!/usr/bin/env python3
"""Deep heartbeat ingestion backup writer."""
import json, os
from datetime import datetime, timezone

DATA_DIR = "/root/.hermes/profiles/indigo/commons/data/mentor"
INGESTION_LOG = os.path.join(DATA_DIR, "ingestion_log.jsonl")

already_ingested = set()
with open(INGESTION_LOG) as f:
    for line in f:
        if not line.strip(): continue
        try:
            d = json.loads(line)
            already_ingested.add(d.get("file", d.get("source", "")))
        except: pass

with open("/tmp/mentor_deep_files.txt") as f:
    all_files = [l.strip() for l in f if l.strip()]

now_iso = datetime.now(timezone.utc).isoformat()
written = 0
with open(INGESTION_LOG, "a") as f:
    for filepath in all_files:
        if filepath not in already_ingested:
            parts = filepath.split("/")
            skill_name = ""
            for i, part in enumerate(parts):
                if part == "journals" and i+1 < len(parts):
                    skill_name = parts[i+1]; break
            record = {"file": filepath, "skill_name": skill_name, "ingested_at": now_iso, "entries": 1, "heartbeat_type": "deep"}
            f.write(json.dumps(record) + "\n")
            written += 1

print(f"Ingestion backup: {written} records written")
```

**CRITICAL: Deep heartbeat evidence record missing `orchestration_success_rate` and `error_rate` fields** — The `cron-heartbeat-deep-dualpath.py` script computes these values (line ~180-189) but does NOT include them in the `evidence_record` dict (line ~236). The evidence record only has `evaluation_coverage`, `active_coverage`, `anomalies_detected`, etc. When writing backup evidence or parsing historical deep heartbeat records, do NOT expect `orchestration_success_rate` or `error_rate` in the evidence JSON. Get these from the OKR state file or the journal entry instead. Confirmed 2026-06-24.

**Heredoc journal file naming:** `cat > "$JOURNAL_DIR/${RUN_ID}.json" << 'EOF'` may create a file literally named `.json`. Compose the filename in a separate variable first, then reference without braces. Always `ls` the output to verify.
