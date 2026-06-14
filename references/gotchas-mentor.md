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

## Cron Mode — Python Writes

23. **Python `with open()` writes to evidence.jsonl and ingestion_log.jsonl are INTERMITTENT in cron mode — verify every run** — Across runs from 2026-06-12 through 2026-06-14, the `cron-heartbeat-light.py` script's Python `with open()` writes showed 0 delta on evidence and ingestion in most runs, with the journal write (different code path) sometimes succeeding. However, on 2026-06-14T12:15Z, all 3 writes (evidence +1, ingestion +4, journal) succeeded simultaneously — the first confirmed full-success run in the observed period. The pattern is shifting from "reliably fails" to "intermittent." **The verify-and-backup workflow remains mandatory regardless** — always `wc -l` all 3 files after the script exits and write backup via shell if delta is 0. The backup workflow is the ACTUAL persistence mechanism; treat script writes as best-effort. Script writes to `/tmp/` DO work (tmpfs is exempt), so the prepare-to-/tmp/ pattern (write via Python to /tmp/, validate with `wc -l`, then shell-append) is a reliable two-step alternative. See `references/shell-write-pattern.md` for the mandatory verify-and-backup workflow.

24. **Profile-scoped journal paths resolve to `..` skill name** — `cron-heartbeat-light.py` computes skill name via `os.path.relpath(fpath, JOURNALS_DIR)` where `JOURNALS_DIR = "/root/.hermes/commons/journals"`. Files under `/root/.hermes/profiles/indigo/commons/journals/` resolve to `..` as the skill name. This is cosmetic (the absolute path in the ingestion log is correct) but produces misleading `skill_name` values. Fix: detect profile-scoped paths and use a second `relpath` against the profile journals root, or extract skill name from the path parts after `/journals/`.

25. **Gap detection false negative chain** — When evidence writes silently fail across multiple consecutive heartbeats, the evidence log's last entry becomes stale. Each new run computes `gap_minutes` from that stale entry, which can be small (e.g., 0–5 min) even though the true gap since the last SUCCESSFUL write is much larger (e.g., 54+ min). The script reports `gap_detected: false` because it only reads the evidence log — it has no way to know intermediate runs existed. **Mitigation**: gap detection should also check the OKR state's `last_light_timestamp` as a secondary signal, or compare against expected cron interval. A gap >15 min when the cron runs every 5 min always means evidence writes are failing, not that the system is quiet.

25. **`active_skills_30d` in the script output reflects only the piped 3-day file set** — The script receives only `-mtime -3` files via stdin, so its `active_skills_30d` count (e.g., 15) is NOT the true 30-day active skill count (e.g., 35). The true count must be computed separately via a dual-path 30-day `find`. The evidence record's `active_skills_30d` field will undercount unless overridden by the caller.

26. **`MENTOR_ACTIVE_SKILLS_30D` env var is for the CALLER only — the script ignores it** — `cron-heartbeat-light.py` does NOT read or consume the `MENTOR_ACTIVE_SKILLS_30D` environment variable. Setting it via `cat file | MENTOR_ACTIVE_SKILLS_30D=35 python3 script.py` has zero effect on the script's behavior. The env var is only useful as a shell variable for the caller's own logic (e.g., writing corrected evidence). The script computes `active_skills_30d` solely from its stdin file list. Do not set this env var expecting the script to use it.

52. **`git stash` + `git pull` fails with untracked file conflicts** — When the working tree has both modified tracked files AND untracked files that would be overwritten by the incoming merge, `git stash` stashes the tracked changes but leaves untracked files in place. Then `git pull` aborts with "The following untracked working tree files would be overwritten by merge." The stash entry cannot be applied cleanly either. **Fix:** Don't use `git stash` for this case. Instead: `git checkout -- .` (discard tracked changes) + `git clean -fd` (remove untracked files) + `git pull origin main`. Then diff backups against the pulled state and re-apply local improvements. Confirmed 2026-06-13: stash-based approach failed, checkout+clean+pull succeeded.

## Scalability

17. **`os.walk` on journals directory is unreliable at scale** — With 5000+ journal files across 100+ skill dirs, `os.walk` can silently produce wrong counts or hit timeouts. Use `subprocess.run(["find", journals_dir, "-name", "*.json", "-mtime", "-30"])` for active-skill counting. It's faster and doesn't load every inode into Python memory.
18. **Active-skill counting must exclude `.archive`** — The `.archive/` directory under journals/ contains stale skill journals. Always filter `skill != ".archive"` when computing coverage denominators and active-skill sets.
19. **Anomaly dedup must not resolve same-run entries** — When deduplicating anomalies by `(type, skill)`, only resolve entries from *previous* runs. Entries written in the current heartbeat pass are new data, not duplicates. Check `timestamp` against the current run timestamp before resolving.

## Journal Date Directory Mismatch

56. **`date +%Y-%m-%d` in journal writer uses local time, not UTC — journal goes to wrong day's directory** — When writing the Mentor journal via shell, `JOURNAL_DIR="$(date +%Y-%m-%d)"` uses the system's local timezone. If the server is not set to UTC (e.g., UTC-7/8), the journal file lands in yesterday's directory. The `run_id` inside the file uses UTC time (via Python `datetime.now(timezone.utc)`), which means the filename's date and the directory's date disagree. **Fix:** Use `date -u +%Y-%m-%d` for the directory path to match UTC-based run_ids, or use Python for both: `python3 -c "from datetime import datetime, timezone; print(datetime.now(timezone.utc).strftime('%Y-%m-%d'))"`. Confirmed 2026-06-14: journal written to `2026-06-13/` (local) while run_id contained `20260613T215917Z` = 2026-06-14 UTC. Required manual `cp` to correct directory.

## Sync Loop — cp Echo Pipeline Failure

57. **`for f in ...; do cp $f /dest/$f && echo "Synced: $f"; done` fails in terminal()** — A `for` loop that combines `cp` with `&& echo "..."` inside `terminal()` can trigger the foreground-background detection (the `&&` compound exit-code logic confuses the shell parser). The entire block exits with "Foreground command uses '&' backgrounding" error (exit_code=-1). **Fix:** Separate sync and verification — no `&&` between cp and echo inside the loop:
    ```bash
    for f in evidence.jsonl ingestion_log.jsonl anomalies.jsonl okr_state.json decisions.jsonl; do
        cp <profile>/$f <commons>/$f 2>/dev/null
    done
    echo "Sync complete"
    ```
    Or use separate `terminal()` calls for sync and verification. Confirmed 2026-06-14: compound block with `&& echo` failed with exit_code=-1; same commands without `&&` succeeded.

## Cron Mode — Ingestion Count Accuracy

26. **`cron-heartbeat-light.py` stdin pipe can silently drop files** — The script reads file paths from stdin (piped from shell `find`), but the pipe can silently truncate or drop entries, causing the script to under-count new files (e.g., reported 3 but actual 8). After every heartbeat, cross-reference the script's `new_files_ingested` count against a manual check: `find ... -mtime -3 | sort -u` minus paths already in `ingestion_log.jsonl`. If counts differ, use the manual count and write corrected evidence via shell `printf >>`. See run 2026-06-06T174830Z for an example.

27. **Script self-journaling via Python `with open()` is best-effort** — `cron-heartbeat-light.py` writes its own evidence record via Python `with open(evidence_log, 'a')`. This sometimes persists and sometimes silently fails (confirmed pattern across multiple runs: sometimes evidence grows, sometimes it doesn't). The caller must always verify evidence persistence via `wc -l` after the script exits, and write a backup evidence entry via shell `printf >>` if the count didn't change. Do NOT assume the script's own journaling succeeded. See gotcha #23 for the broader pattern and `references/shell-write-pattern.md` for the verify-and-backup workflow.

    **Partial success is possible (confirmed 2026-06-06T21:34Z):** Evidence and ingestion writes can succeed (evidence 177→178, ingestion 6419→6423) while the journal write fails in the *same run*. The three writes are independent — the verify-and-backup workflow must check all three files (`evidence.jsonl`, `ingestion_log.jsonl`, and the journal directory) independently. Do NOT assume that because evidence grew, the journal was also written.

28. **Script-reported `new_files_ingested` is an upper bound, not exact** — The script's dedup uses absolute path normalization that can differ from how paths were stored in the ingestion log by prior runs (especially profile-scoped paths with `..` skill names, see gotcha #24). A manual cross-reference (`find ... -mtime -3 | sort -u` minus paths already in `ingestion_log.jsonl`) gives the ground truth. If the script reports N but manual check shows M≠N, use M and note the discrepancy. Re-ingestions from path normalization mismatches are harmless (idempotent) — they re-parse already-known entries but don't corrupt state.

    **Zero truly new files (confirmed 2026-06-06T21:34Z):** When cross-reference shows 0 truly new files but the script reports N ingestions, all N are idempotent re-ingestions. This happens when the script's canonical path normalization differs from the ingestion log's stored paths. The script will still parse and re-record entries for already-known files — this is harmless but inflates the `new_files_ingested` count. The corrected evidence record should note this.

## Heredoc and File Naming

31. **Heredoc journal file naming — `${VAR}.json` in heredoc path can produce `.json` literal** — When writing journal files via `cat > "$DIR/${RUN_ID}.json" << 'EOF'`, the braces can be consumed by the shell's heredoc or variable expansion logic, producing a file literally named `.json`. **Fix: compose the filename in a separate variable FIRST, then reference it without braces:**
    ```bash
    JOURNAL_FILE="$JOURNAL_DIR/${RUN_ID}.json"  # compose first
    cat > "$JOURNAL_FILE" << 'EOF'               # then reference
    {"run_id": "$RUN_ID", ...}
    EOF
    ls -la "$JOURNAL_FILE"                        # verify immediately
    ```
    Always `ls` the output file after writing to confirm the name is correct. If you see `.json` as the filename, rename immediately: `mv "$JOURNAL_DIR/.json" "$JOURNAL_FILE"`. Confirmed 2026-06-06T18:57Z — the heredoc consumed the variable, producing `.json`.

## Self-Referential Journal Ingestion

35. **Heartbeat discovers its own prior journal files as "new"** — When `cron-heartbeat-light.py` writes its own journal to `commons/journals/ocas-mentor/YYYY-MM-DD/`, that file appears in the next run's `find -mtime -3` scan as a "new" file (since it was created after the last ingestion log entry). The script ingests it, parses it, and records it — producing a misleading `new_files_ingested` count (e.g., 2) when truly new skill journals = 0. **This is harmless** (idempotent re-ingestion) but the corrected evidence record should note it. The cross-reference step (`find ... -mtime -3` minus `ingestion_log.jsonl`) catches these: they show up as "new" to the script but are actually self-referential. Confirmed 2026-06-06T22:17Z: script reported 2 new files, both were ocas-mentor's own journals from prior runs today; true new skill journals = 0.

35a. **Self-referential journal accumulation accelerates over time** — Each heartbeat writes a journal file that becomes "new" for the next ~12 heartbeats (3-day window at 5-min intervals = 864 scans, but ingestion dedup catches it after first re-ingestion). However, backup journals, correction journals, and caller-written journals all add to the count. Confirmed 2026-06-14: 534 ocas-mentor journals in 3 days (out of 1,002 total files scanned). This inflates `total_files_3d` in evidence records but does not affect `new_files_ingested` (dedup catches re-ingestions). The ingestion log grows by ~1 entry per self-referential file on first encounter. No action needed unless ingestion_log exceeds ~10,000 lines (then run dedup per gotcha #42b).

## Anomaly Counting

36. **Anomaly `timestamp` field mismatch — `active_anomalies` always reports 0** — ~~The light heartbeat script (`cron-heartbeat-light.py`, line ~218) reads anomalies using `a.get("timestamp")`, but anomalies created by the deep heartbeat and older detection logic use `detected_at` as their date field. Since `timestamp` is `None` on these entries, `parse_dt(None)` returns `None`, the `if a_ts` guard skips them, and `active_anomalies` is always 0 regardless of how many anomalies exist. This means the evidence record and heartbeat output always show 0 anomalies even when stale or active anomalies are present.~~ **FIXED 2026-06-08:** Line 218 changed from `a.get("timestamp")` to `a.get("timestamp") or a.get("detected_at")`. The script now correctly reads both field names.

37. **Stale anomalies never purged from `anomalies.jsonl`** — The light heartbeat counts anomalies within a 7-day window but never filters out entries with `stale: true`, and the timestamp mismatch (gotcha #36) means it doesn't see them anyway. Stale anomalies accumulate indefinitely with no cleanup. The deep heartbeat can mark anomalies stale after 5+ unchanged heartbeats, but no process archives or removes them. **Mitigation:** Either (a) add a periodic compaction step that moves `stale: true` entries older than 30 days to an archive file, or (b) filter `stale: true` out of the active count and add a separate `stale_anomalies` metric to evidence records.

38. **Script journal filename missing `mentor-light-` prefix** — ~~`cron-heartbeat-light.py` line 264 writes to `f"{run_id}.json"` where `run_id = now.strftime("%Y%m%dT%H%M%SZ")`, producing e.g. `20260607T045155Z.json`. But the journal's `run_id` field (line 249) is `f"mentor-light-{run_id}"` = `mentor-light-20260607T045155Z`. The filename doesn't match the `run_id` inside the file, breaking tools or humans that expect consistency.~~ **FIXED 2026-06-08:** Line 264 changed from `f"{run_id}.json"` to `f"mentor-light-{run_id}.json"`. The filename now matches the `run_id` field inside the journal.

    **Compounding effect:** When the caller writes a corrected backup journal (e.g., `mentor-light-20260608T155703Z.json`) to the same directory, the next heartbeat's `find -mtime -3` discovers BOTH the script's malformed file and the caller's backup as "new" files. Both get ingested as ocas-mentor journals, inflating `new_files_ingested` and triggering the self-referential ingestion pattern (gotcha #35) twice per heartbeat cycle.

## JSON and Float Formatting in Shell

39. **Never use `bc -l` for float values inside JSON strings** — `bc -l` produces floats without leading zeros (e.g., `.0285` instead of `0.0285`), which is invalid JSON. When embedding computed floats in JSON via shell `printf`, always use Python for the float-to-string conversion:
    ```bash
    # BAD — produces invalid JSON:
    "evaluation_coverage": $(echo "scale=4; 1 / 35" | bc -l)
    # Result: "evaluation_coverage": .0285  ← missing leading zero → JSON parse error

    # GOOD — compute the float in Python, write full JSON via Python:
    python3 -c "
    import json, datetime
    record = {..., 'metrics': {'evaluation_coverage': round(1/35, 4), ...}}
    with open('/tmp/evidence_backup.json', 'w') as f:
        json.dump(record, f)
    "
    cat /tmp/evidence_backup.json >> evidence.jsonl
    ```
    Confirmed 2026-06-08: two separate heartbeats (lines 207 and 219) produced corrupt evidence.jsonl entries because `bc -l` output `.0285` was embedded directly in JSON. Both required manual repair. The same issue affects any shell-constructed JSON with computed numeric values.

40. **Evidence.jsonl corrupt-line repair during heartbeat** — When a heartbeat's own backup evidence write has produced a corrupt line (detected via `tail -1 | python3 -c "json.loads(...)"` failing), repair it within the same heartbeat before writing the new entry:
    ```bash
    # Check last line validity
    if ! tail -1 /root/.hermes/commons/data/mentor/evidence.jsonl | python3 -c "import sys,json; json.loads(sys.stdin.read())" 2>/dev/null; then
        # Remove corrupt tail — scan for last valid JSONL line (may be multiple corrupt lines)
        VALID_LINES=$(python3 -c "
import json
lines = open('/root/.hermes/commons/data/mentor/evidence.jsonl').readlines()
for i in range(len(lines)-1, -1, -1):
    try:
        json.loads(lines[i].strip())
        print(i+1)
        break
    except: continue
")
        head -n "$VALID_LINES" /root/.hermes/commons/data/mentor/evidence.jsonl > /tmp/evidence_repair.jsonl
        cp /tmp/evidence_repair.jsonl /root/.hermes/commons/data/mentor/evidence.jsonl
        echo "Repaired evidence.jsonl: kept $VALID_LINES lines"
    fi
    ```
    This prevents corrupt entries from persisting and confusing future heartbeats' gap detection and metrics. Scan the full file periodically: `python3 -c "import json; [json.loads(l) for l in open('evidence.jsonl')]"`. Confirmed 2026-06-08: lines 207 and 219 were both corrupt from different prior heartbeats and required inline repair.

## Deep Heartbeat — Single-Path Scan Gap

41. **Python heredoc to `/tmp/` then `cat >>` can corrupt JSONL with multi-line output** — When writing evidence backup via `python3 << 'PYEOF' > /tmp/evidence_backup.json` followed by `cat /tmp/evidence_backup.json >> evidence.jsonl`, the Python heredoc may produce multi-line output. This happens if `json.dump(record, f)` is called with an `indent` parameter, or if `print(json.dumps(record, indent=2))` is used. Multi-line output appended to a JSONL file corrupts it — every JSONL parser expects exactly one JSON object per line. **The file written to `/tmp/` must contain exactly ONE line.** Safe patterns:
    ```bash
    # SAFEST: Use printf with inline Python — guarantees single-line output
    printf '%s\n' "$(python3 -c "
    import json
    from datetime import datetime, timezone
    record = {
        'schema': 'mentor-evidence-v2',
        'run_id': 'mentor-light-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'heartbeat_type': 'light',
        'metrics': {'total_files_3d': 935, 'new_files_ingested': 3, 'active_skills_30d': 35,
                    'evaluation_coverage': round(2/35, 4), 'gap_detected': False, 'active_anomalies': 0},
        'outcome': 'success',
        'notes': 'Backup via shell.'
    }
    print(json.dumps(record))
    ")" >> /root/.hermes/commons/data/mentor/evidence.jsonl

    # ALSO SAFE: Write to /tmp/ with json.dumps (no indent), validate line count BEFORE appending
    python3 -c "
    import json
    record = {...}
    with open('/tmp/evidence_backup.json', 'w') as f:
        f.write(json.dumps(record) + '\n')
    "
    # Validate: file must be exactly 1 line
    if [ "$(wc -l < /tmp/evidence_backup.json)" -eq 1 ]; then
        cat /tmp/evidence_backup.json >> /root/.hermes/commons/data/mentor/evidence.jsonl
    else
        echo "ERROR: /tmp/evidence_backup.json has multiple lines — JSONL would be corrupted. Abort."
    fi
    ```
    **NEVER use `json.dump(record, f)` with `indent` when the output will be appended to a JSONL file.** Even `indent=2` produces multi-line output that breaks every downstream JSONL parser.
    Confirmed 2026-06-08: evidence.jsonl grew from 223 to 239 lines (+16) because a Python heredoc wrote multi-line JSON to `/tmp/` which was then `cat >>`'d into the JSONL. Required truncating 16 corrupt lines and rewriting the entry as single-line JSON.
    **Root cause:** The Python heredoc `python3 << 'PYEOF' > /tmp/evidence_backup.json` can produce multi-line output if the script uses `json.dump(record, indent=2)`, `print(json.dumps(record, indent=2))`, or multiple `print()` statements. Always validate with `wc -l` before appending to any JSONL file.

42. **Ingestion log uses TWO path formats — naive `comm` shows false "new" files** — The ingestion log stores paths in two formats: (a) relative `ocas-xxx/YYYY-MM-DD/file.json` (from early heartbeats) and (b) absolute `/root/.hermes/commons/journals/ocas-xxx/...` (from later heartbeats). Profile-scoped paths use `/root/.hermes/profiles/indigo/commons/journals/ocas-xxx/...`. A naive `comm -23 <(sort find_output) <(sort ingestion_log)` will show 800+ "new" files when only ~6 are truly new, because the relative paths from the ingestion log don't match the absolute paths from `find`. **Fix:** Extract and normalize all paths to absolute before comparison:
    ```bash
    python3 -c "
    import json
    paths = set()
    with open('/root/.hermes/commons/data/mentor/ingestion_log.jsonl') as f:
        for line in f:
            try:
                d = json.loads(line)
                src = d.get('source') or d.get('file', '')
                if src:
                    if not src.startswith('/'):
                        src = '/root/.hermes/commons/journals/' + src
                    paths.add(src)
            except: pass
    for p in sorted(paths):
        print(p)
    " > /tmp/ingested_paths.txt
    # Now comm works correctly:
    comm -23 <(sort /tmp/mentor_files_3d.txt) <(sort /tmp/ingested_paths.txt) > /tmp/new_files_3d.txt
    ```
    Confirmed 2026-06-08: 882 false "new" files reduced to 6 true new files after normalization.

42b. **Ingestion log accumulates massive duplicate entries — periodic dedup required** — Even after path normalization, the ingestion log accumulates duplicate entries over time. Path format mismatches (relative vs. absolute vs. profile-scoped) mean the same journal file gets ingested multiple times under different path representations. Confirmed 2026-06-08: ingestion_log.jsonl grew to 8,067 lines but only 1,751 were unique — 6,314duplicate entries (78% bloat). This inflates file counts, slows heartbeat processing, and wastes tokens. **Fix during heartbeat when delta seems excessive:** Parse the full file, deduplicate by the `file` field (keeping the last occurrence), and rewrite:
    ```bash
    python3 -c "
    import json
    seen = {}
    lines = []
    with open('/root/.hermes/commons/data/mentor/ingestion_log.jsonl') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                d = json.loads(line)
                fp = d.get('file', '')
                if fp: seen[fp] = line
            except: pass
    with open('/root/.hermes/commons/data/mentor/ingestion_log.jsonl', 'w') as f:
        for v in seen.values():
            f.write(v + '\n')
    print(f'Deduped: {len(seen)} unique entries')
    "
    ```
    This is a safe periodic maintenance operation — the ingestion log is a pure function of file paths, so deduping never loses information. Run it when `wc -l` exceeds 3,000 lines or when the heartbeat reports a suspiciously high `new_files_ingested` count. **After dedup, update the pre-run count baseline** so the next heartbeat's delta check works correctly.

43. **Caller backup journal must NOT double-prefix filename** — When writing a backup journal via shell, if the `RUN_ID` variable already contains the `mentor-light-` prefix (e.g., `RUN_ID="mentor-light-20260608T175904Z"`), the filename must be `"$RUN_ID.json"`, NOT `"mentor-light-${RUN_ID}.json"`. Double-prefixing produces `mentor-light-mentor-light-20260608T175904Z.json`. Confirmed 2026-06-08T17:59Z — required manual `mv` to rename.

44. **`active_skills_30d` from dual-path `find` counts ALL skill dirs, not just OCAS** — The dual-path 30-day `find` returns 289 unique directories, but many are non-OCAS skills (api-integration, csv-parsing, database-operations, etc.). The true OCAS skill count is ~25-30. The inflated number makes `evaluation_coverage` misleading (6/289 ≈ 0.02 instead of 6/30 ≈ 0.20). **Fix:** Filter to ocas-* prefixes when computing the denominator:
    ```bash
    ACTIVE_OCAS_30D=$(find /root/.hermes/commons/journals/ /root/.hermes/profiles/indigo/commons/journals/ -name "*.json" -mtime -30 2>/dev/null | grep -oP 'ocas-[a-z]+' | sort -u | wc -l)
    ```
    This gives the true OCAS active skill count for evaluation_coverage denominator.

44a. **`awk -F/` on absolute paths produces `//` double-slash prefixes — use `grep -oP` instead** — When counting unique skill directories from absolute paths using `awk -F/`, the leading `/` creates an empty first field, producing paths like `//root/.hermes/...` instead of `/root/.hermes/...`. This causes downstream path comparisons to fail because `//root/...` ≠ `/root/...`. Additionally, the awk approach requires complex logic to strip date subdirectories and deduplicate. **Confirmed reliable alternative:** Use `grep -oP` to extract the skill name directly from the path:
    ```bash
    # Extract unique OCAS skill names (confirmed reliable)
    cat /tmp/mentor_files_30d.txt | grep -oP 'ocas-[a-z]+' | sort -u | wc -l

    # Extract ALL unique skill names (OCAS + non-OCAS)
    cat /tmp/mentor_files_30d.txt | grep -oP 'commons/journals/([a-z][a-z0-9_-]+)' | sed 's|commons/journals/||' | sort -u
    ```
    The `grep -oP 'ocas-[a-z]+'` pattern is the fastest, most reliable way to count unique OCAS skills from journal file paths. It avoids all the edge cases of awk field splitting on absolute paths, date subdirectory stripping, and `.archive` filtering. Confirmed 2026-06-14: counted 20 OCAS skills (excluding custodian) and 21 total from 4003 journal files in under 1 second.

46. **`ocas_skills_30d` should be tracked as a separate metric in evidence records** — In addition to `active_skills_30d` (all skills) and `evaluation_coverage` (which uses the OCAS-only denominator), record `ocas_skills_30d` as a separate field in the evidence metrics. This makes the OCAS-specific activity visible at a glance without requiring the reader to derive it. Example: `"active_skills_30d": 35, "ocas_skills_30d": 21`. The dual-path 30-day find with `grep -oP 'ocas-[a-z]+'` gives the OCAS count; pipe it through `sort -u | wc -l`.

## Caller Workflow — Duplicate Journal Prevention

47. **`comm -23` requires sorted input — unsorted pipe produces false positives** — When cross-referencing `find` output against ingested paths using `comm -23`, both inputs must be sorted. Piping `find` directly to `comm` (or using `sort -u` that outputs in non-deterministic order) causes `comm` to report "input is not in sorted order" and produce wildly inflated false-positive counts (e.g., 38 instead of 3). **Fix:** Always sort both files before `comm`: `sort /tmp/mentor_files_3d.txt > /tmp/mentor_files_3d_sorted.txt` and `sort /tmp/ingested_paths.txt > /tmp/ingested_paths_sorted.txt`, then `comm -23 /tmp/mentor_files_3d_sorted.txt /tmp/ingested_paths_sorted.txt`. Confirmed 2026-06-08T21:58Z: unsorted comm reported 38 new files, properly sorted comm showed 3.

48. **Script-reported `new_files_ingested` consistently undercounts — always cross-reference** — The script's `new_files_ingested` is not just an upper bound (gotcha #28) — it can also UNDERCOUNT. Confirmed 2026-06-08T22:17Z: script reported 1 new file, cross-reference showed 5 truly new files. The script's internal dedup logic can miss files that the ingestion log has under different path representations. **Always cross-reference via `find` minus ingestion_log (with path normalization) regardless of what the script reports.** The cross-reference ground truth supersedes the script's count in all cases.

49. **Shell variables don't persist across `terminal()` calls** — Pre-run counts (`EVIDENCE_BEFORE`, `INGESTION_BEFORE`) set via `VAR=$(wc -l < file)` in one `terminal()` block are GONE in the next block. The verify-and-backup workflow MUST read pre-run counts AND run the script AND verify post-run counts all in the SAME `terminal()` call. Splitting into separate `terminal()` calls loses the baselines and makes delta verification impossible. The SKILL.md code example shows the blocks sequentially for readability, but in cron mode they MUST be one compound shell block (use `;` or `&&` between steps, or a single heredoc). Confirmed 2026-06-08T23:39Z: pre-run counts from first `terminal()` were empty strings in the fourth `terminal()` because each call is a fresh shell.

50. **`evidence.jsonl` uses FLAT schema — no `metrics` wrapper** — The `cron-heartbeat-light.py` script and all shell-backup evidence writes use a flat schema where `new_files_ingested`, `active_skills_30d`, `evaluation_coverage`, etc. are top-level keys. There is NO nested `metrics` dict. When reading evidence entries, use `d.get('new_files_ingested')` directly, NOT `d.get('metrics', {}).get('new_files_ingested')`. The flat schema has been confirmed consistently from v2.8.10 onward (2026-06-09). Mixed schema in the file is a confirmed pattern: some very old entries may use a nested `metrics` wrapper, but all entries written since 2026-06-09 are flat.

50a. **Light heartbeat evidence entries use `outcome_counts` (dict), NOT `outcome` (string)** — When validating evidence entries, checking for `outcome` field presence will falsely flag ~95% of light heartbeat entries as corrupt. Light heartbeat entries have `outcome_counts: {"success": N}` (a dict), while deep heartbeat entries may have `outcome: "success"` (a string). Both are valid. Do NOT use `if 'outcome' in d` as a validity check — use `if 'outcome' in d or 'outcome_counts' in d` instead. Confirmed 2026-06-14: 789/822 entries flagged as "missing outcome" were actually valid light heartbeat entries with `outcome_counts`.

45. **Caller MUST NOT write two journal files for the same run** — When the script self-journaling fails and the caller writes a backup journal, it is tempting to use both a heredoc write AND a Python write "to be safe." This produces two journal files with different `run_id` values (e.g., `mentor-light-20260608T183959Z.json` and `mentor-light-20260608T184059Z.json`) for the same heartbeat run. Both get discovered as "new" by the next heartbeat's `find -mtime -3`, ingested as separate ocas-mentor entries, and inflate the `new_files_ingested` count. **Rule: write the backup journal exactly ONCE, via ONE method.** If using heredoc, verify the file exists and is valid before considering "maybe I should also write via Python." If using Python-to-/tmp then `cat >>`, that's the single write. After writing, `ls` the journal directory to confirm exactly one new file. Confirmed 2026-06-08: two journals written for same run (heredoc + Python), required manual `rm` to deduplicate.

51. **Extended cron gaps amplify self-journaling failure rate** — After a prolonged gap (e.g., 46+ hours), multiple consecutive heartbeats all fail to self-journal via Python writes. Confirmed 2026-06-11: after a 46-hour gap (last heartbeat 2026-06-09T07:59Z), this heartbeat's script also showed 0 delta on evidence and ingestion. The dual failure pattern persisted across 5+ consecutive runs before this session. The caller's backup write pattern (python3 -c to /tmp/, validate wc -l, cat >> to JSONL) remains the only reliable persistence method after gaps. The gap itself is an operational concern (check gateway/cron status) but does not change the backup write workflow.

55a. **Python heredoc with shell variable interpolation fails for dynamic paths** — When writing journal files via `python3 << 'PYEOF'`, shell variables (`$JOURNAL_DIR`, `$RUN_ID`) set in the same `terminal()` block are NOT visible to the Python subprocess if the heredoc is single-quoted (`'PYEOF'`). The Python code sees empty strings for `os.environ.get("JOURNAL_DIR")` and `os.environ.get("RUN_ID")`. **Fix:** Hardcode paths inside the Python heredoc, or compose the full file path as a Python string from `os.path.join()` calls. Do NOT rely on shell variable expansion to pass paths into a single-quoted Python heredoc. Confirmed 2026-06-14: journal write failed with `FileNotFoundError: 'JOURNAL_PATH_PLACEHOLDER'` because shell vars didn't propagate; fix was to hardcode the path construction inside Python.

53. **Shell `${VAR}` inside heredocs can produce stray braces in paths** — When constructing file paths in heredocs using `${VAR}` syntax, a stray `}` can appear (e.g., `${DATA_DIR}}` producing `/path/to/file.jsonl}`). This silently breaks file operations. **Use `$VAR` without braces for path interpolation in heredocs**, or better yet, use Python heredocs (`python3 << 'PYEOF'`) with hardcoded paths for all backup writes. Never mix shell variable expansion with `>>` redirection to paths constructed from variables. Confirmed 2026-06-14: three separate terminal() calls failed with "No such file or directory" because `${DATA_DIR}}` expanded to `/root/.hermes/commons/data/mentor/}`.

54. **`os.environ.get()` in single-quoted Python heredocs returns 0/empty for unexported shell vars** — When the backup workflow writes evidence via `python3 << 'PYEOF'` and uses `os.environ.get("TOTAL_3D", 0)`, the value will be 0 if `TOTAL_3D` was set as a shell variable (not exported) in the same `terminal()` block. Single-quoted heredocs (`'PYEOF'`) prevent shell expansion AND the subprocess doesn't inherit non-exported shell vars. This produces evidence records with all-zero metrics (total_files_3d=0, new_files_ingested=0, active_skills_30d=0) that silently pass validation but are wrong. **Fix:** Either (a) `export` vars before the heredoc (but `export` in a compound `terminal()` block may not propagate to subshells either), or (b) compute values directly inside the Python heredoc using subprocess calls (e.g., `TOTAL_3D = int(subprocess.check_output(["wc", "-l", "/tmp/mentor_files_3d.txt"]).split()[0])`), or (c) write a standalone `/tmp/write_evidence.py` script file and invoke it — file-based scripts don't have the heredoc env var isolation problem. Confirmed 2026-06-14: evidence written with 0 values despite correct shell vars visible via `echo` in the same block. Fixed post-hoc by re-writing the evidence record.

55a. **Python heredoc with shell variable interpolation fails for dynamic paths** — When writing journal files via `python3 << 'PYEOF'`, shell variables (`$JOURNAL_DIR`, `$RUN_ID`) set in the same `terminal()` block are NOT visible to the Python subprocess if the heredoc is single-quoted (`'PYEOF'`). The Python code sees empty strings for `os.environ.get("JOURNAL_DIR")` and `os.environ.get("RUN_ID")`. **Fix:** Hardcode paths inside the Python heredoc, or compose the full file path as a Python string from `os.path.join()` calls. Do NOT rely on shell variable expansion to pass paths into a single-quoted Python heredoc. Confirmed 2026-06-14: journal write failed with `FileNotFoundError: 'JOURNAL_PATH_PLACEHOLDER'` because shell vars didn't propagate; fix was to hardcode the path construction inside Python.

## Script Evidence Record — Missing Fields

58. **`cron-heartbeat-light.py` evidence record written with null `run_id` and no `outcome` field** — When the script successfully writes to evidence.jsonl (confirmed by `wc -l` delta), the record may still have `run_id: null` and lack an `outcome` top-level key entirely. The script's evidence writer uses a local `run_id` variable that can be `None` if `datetime.now()` returns unexpectedly, and the `outcome` key is omitted when `errors == 0` (the `outcome_counts: {"success": N}` dict is present instead). The record is technically valid JSON and validates via `json.loads()`, but looks corrupt to human readers and to the `outcome` validation check (see gotcha #50a). **Mitigation:** The caller's corrected backup evidence record (with proper `run_id` and `outcome: "success"`) should always be written as a separate line. This is not a duplicate — it is a correction. Two evidence lines per heartbeat (script's incomplete one + caller's corrected one) is the expected pattern, not a bug. The corrected record should use the flat schema with all fields populated. Confirmed 2026-06-14: script wrote `{"schema": "mentor-evidence-v2", "run_id": null, "timestamp": "...", "heartbeat_type": "light", "new_files_ingested": 1, "active_skills_30d": 10, ...}` with no `outcome` and `evaluation_coverage: 0.1` (stale stdin-count denominator).

59. **Commons sync gap accumulates after every heartbeat — profile data leads commons** — After every heartbeat, the profile-scoped evidence.jsonl and ingestion_log.jsonl will be ahead of the commons copies by the number of new lines written this run (typically 1-2 each). The profile is the authoritative source; commons is a lagging copy. The line-level set-difference sync (not `cp -f`, which silently skips when profile is newer) must be run after every heartbeat. Confirmed 2026-06-14: 31 evidence + 33 ingestion lines behind after one heartbeat cycle. See gotcha #13 for the `cp -n` skip problem and the Python set-difference fix.

## Deep Heartbeat — Single-Path Scan Gap

32. **`cron-heartbeat-deep.py` only scans `JOURNALS_ROOT` (commons), misses profile-scoped journals** — FIXED 2026-06-13: Use `scripts/cron-heartbeat-deep-dualpath.py` which scans both paths. See `references/deep-heartbeat-dual-path.md`. Confirmed: stock script scanned 168 files, dual-path wrapper scanned 6,781 files (40x more). Also writes to profile-scoped data dir for light heartbeat consistency. `active_coverage` capped at 1.0 (raw stored separately as `active_coverage_raw`).
    ```python
    okr_str = ", ".join(f"{k}={v['status']}" for k, v in okr_scores.items())
    print(f"  OKRs:                 {okr_str}")
    ```
    Confirmed 2026-06-06T19:01Z — script crashed on first run, fixed in-place.

## OKR Measurement

34. **`orchestration_success_rate` OKR scoring deflates by counting `unknown` as non-success** — The OKR computes `success / (success + error + unknown)`, but `unknown` outcomes are journals that lack an explicit outcome field AND have no `error` key — they are effectively successful runs (per `normalize_outcome()` which defaults to `success` when no error is present). The OKR should either: (a) count `unknown` as success: `(success + unknown) / total`, or (b) use `success / (success + error)` as the denominator. Current behavior: with 81% success and 19% unknown, the OKR reports FAIL at 0.81 even though error_rate is 0.0000. This is a measurement artifact, not a real failure. Confirmed 2026-06-06: orchestration_success_rate=FAIL (0.8122) while error_rate=PASS (0.0000).
