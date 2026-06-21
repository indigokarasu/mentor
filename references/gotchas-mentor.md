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

23. **Python `with open()` writes to evidence.jsonl and ingestion_log.jsonl are INTERMITTENT in cron mode — verify every run** — The `cron-heartbeat-light.py` script's Python `with open()` writes can silently fail (0 delta) regardless of which files succeeded. The three writes (evidence, ingestion, journal) are independent and can succeed/fail in any combination. **The verify-and-backup workflow remains mandatory regardless of streak length** — always `wc -l` all 3 files after the script exits and write backup if delta is 0. See `references/shell-write-pattern.md`.

24. **Profile-scoped journal paths resolve to `..` skill name** — `cron-heartbeat-light.py` computes skill name via `os.path.relpath(fpath, JOURNALS_DIR)` where `JOURNALS_DIR = "/root/.hermes/commons/journals"`. Files under `/root/.hermes/profiles/indigo/commons/journals/` resolve to `..` as the skill name. Fix: extract skill name from path parts after `/journals/`: `parts = fpath.split('/'); skill = parts[parts.index('journals')+1] if 'journals' in parts else 'unknown'`.

25. **Gap detection false negative chain** — When evidence writes silently fail across multiple consecutive heartbeats, the evidence log's last entry becomes stale. The script reports `gap_detected: false` because it only reads the evidence log. **Mitigation**: if gap >15 min when cron runs every 5 min, evidence writes are failing, not the system is quiet.

25b. **`active_skills_30d` in the script output reflects only the piped 3-day file set** — The script receives only `-mtime -3` files via stdin, so its `active_skills_30d` count (e.g., 12–13) is NOT the true 30-day active skill count (e.g., 18–20). **This correction is MANDATORY every time — even when the script succeeds on all 3 writes.** Two evidence lines per heartbeat (script's undercount + caller's correction) is the expected pattern. Confirmed 7th time 2026-06-21.

26. **`MENTOR_ACTIVE_SKILLS_30D` env var is for the CALLER only — the script ignores it** — `cron-heartbeat-light.py` does NOT read this env var. The script computes `active_skills_30d` solely from its stdin file list.

52. **`git stash` + `git pull` fails with untracked file conflicts** — Fix: `git checkout -- .` + `git clean -fd` + `git pull origin main`. Then re-apply local improvements.

## Error Grep False Positives

63. **`grep -q '"error"'` on journal files produces false positives — finch/custodian journals mention "error" in content but are successful runs** — When scanning recent journals for urgent issues using `grep -q '"error"'`, journals from ocas-finch and ocas-custodian matched despite being successful runs. These journals contain the word "error" in their content (e.g., reporting on errors detected in other skills, or containing field names like `"error_count"`), but the journals themselves have `outcome: "success"`. **Fix:** Parse JSON and check `outcome` field rather than grepping raw content. See `references/gotcha-error-grep-false-positives.md` for the safe pattern.

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

60. **`cron-heartbeat-light.py` dedup checks `file_path` key but ingestion log uses `file` key — systemic undercount** — The script's `load_ingested_paths()` reads the ingestion log looking for a `file_path` field, but all ingestion records (written by both the script and caller backups) use the `file` field name (schema: `{"file": "...", "skill_name": "...", "ingested_at": "...", "entries": N}`). This means the script's dedup NEVER matches any existing ingestion records, and the script's `new_files_ingested` count is effectively "files scanned minus files the script's own dedup logic rejects for other reasons" rather than "truly new files." The caller's cross-reference (comparing `find` output against the `file` field in the ingestion log) gives the true new-file count. Confirmed 2026-06-15T20:15Z: script reported 6 new files, true new files (via `file` field cross-reference) = 10. The script's count is unreliable for any purpose other than a loose upper bound. **The caller must always cross-reference using the `file` field, not `file_path`.**

26b. **`cron-heartbeat-light.py` stdin pipe can silently drop files** — The pipe can truncate, causing under-count. Cross-reference `new_files_ingested` against `find ... -mtime -3 | sort -u` minus paths in `ingestion_log.jsonl`. If counts differ, use the manual count. Re-ingestions from path normalization mismatches are harmless (idempotent).

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

35a. **Self-referential journal accumulation accelerates over time** — Each heartbeat writes a journal file that becomes "new" for the next ~12 heartbeats (3-day window at 5-min intervals = 864 scans, but ingestion dedup catches it after first re-ingestion). However, backup journals, correction journals, and caller-written journals all add to the count. Confirmed 2026-06-14: 534 ocas-mentor journals in 3 days (out of 1,002 total files scanned). This inflates `total_files_3d` in evidence records but does not affect `new_files_ingested` (dedup catches re-ingestions). The ingestion log grows by ~1 entry per self-referential file on first encounter. No action needed unless ingestion_log exceeds ~10,000 lines (then run dedup per gotcha #42b). **Note:** The profile-scoped ingestion_log.jsonl (8,905 lines as of 2026-06-14T23Z) is the authoritative source — the commons copy (17,556 lines) is a lagging copy with historical accumulation from the pre-profile era. The commons log has ~7 extra duplicate lines but is functionally equivalent. Line-level set-difference sync (not `cp`) keeps them aligned after each heartbeat.

## Anomaly Counting

36. **Anomaly `timestamp` field mismatch — `active_anomalies` always reports 0** — ~~The light heartbeat script (`cron-heartbeat-light.py`, line ~218) reads anomalies using `a.get("timestamp")`, but anomalies created by the deep heartbeat and older detection logic use `detected_at` as their date field. Since `timestamp` is `None` on these entries, `parse_dt(None)` returns `None`, the `if a_ts` guard skips them, and `active_anomalies` is always 0 regardless of how many anomalies exist. This means the evidence record and heartbeat output always show 0 anomalies even when stale or active anomalies are present.~~ **FIXED 2026-06-08:** Line 218 changed from `a.get("timestamp")` to `a.get("timestamp") or a.get("detected_at")`. The script now correctly reads both field names.

37. **Stale anomalies never purged from `anomalies.jsonl`** — The light heartbeat counts anomalies within a 7-day window but never filters out entries with `stale: true`, and the timestamp mismatch (gotcha #36) means it doesn't see them anyway. Stale anomalies accumulate indefinitely with no cleanup. The deep heartbeat can mark anomalies stale after 5+ unchanged heartbeats, but no process archives or removes them. **Mitigation:** Either (a) add a periodic compaction step that moves `stale: true` entries older than 30 days to an archive file, or (b) filter `stale: true` out of the active count and add a separate `stale_anomalies` metric to evidence records.

37a. **Deep heartbeat proposals target auth/infrastructure errors, not just skill logic defects** — The deep heartbeat generates `skill_improvement` proposals when a skill has ≥3 errors (`len(errs) >= 3`). However, the error classifier does not distinguish between skill logic errors and environmental/auth failures (OAuth expiry, invalid_grant, missing credentials, network timeouts). Confirmed 2026-06-14: proposals were generated for `ocas-taste` (6 errors — all Spotify OAuth token expiry from May 2025) and `ocas-dispatch` (5 errors — all Google OAuth `invalid_grant`). These are credential/configuration issues, not skill design defects. Fellow experiments cannot fix them because the root cause is expired credentials, not incorrect code. **Mitigation:** Either (a) add a filter in the proposal generator to skip errors matching known auth patterns (`OAuth`, `invalid_grant`, `token`, `credential`, `401`, `403`), or (b) add an `error_category` field to proposals so Fellows can prioritize skill-logic errors over infra/auth ones, or (c) note this limitation in the heartbeat report and let the caller decide whether to forward proposals to Fellow.

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

## Future-Dated Journal Files

61. **Future-dated journal files inflate `find -mtime -3` counts — cross-reference delta, not absolute count** — When `ocas-forge` or other skills generate journal files with future dates (e.g., 2026-06-17 journals present on 2026-06-15), these files appear in the `-mtime -3` scan and show up as "new" in cross-referencing against the ingestion log. This can produce a large apparent new-file count (e.g., 562) even when the true delta from the last heartbeat is small. The cause is that these files were never in the ingestion log (they didn't exist during prior heartbeats), so they appear as permanently "new" until actually ingested. **This is a one-time catch-up event** per future-dated batch. The script's `new_files_ingested` (e.g., 3) is the reliable metric for *this heartbeat's* work; the cross-reference delta is a historical artifact. Don't flag anomalies based on a large cross-reference count after a catch-up event. Confirmed 2026-06-16: 562 "new" files were all future-dated ocas-forge journals + profile-scoped mentor journals that had never been ingested; script correctly ingested 3.

## Commons-Drift Reversal

66. **Commons evidence.jsonl can grow AHEAD of profile evidence.jsonl from prior direct-write patterns** — Gotcha #59 describes the expected pattern (profile leads commons). The reverse can also occur: commons evidence grows ahead of profile when prior sessions or tools write directly to `/root/.hermes/commons/data/mentor/evidence.jsonl` without going through the profile path. Confirmed 2026-06-17: commons evidence was 2,586 lines while profile evidence was 2,562 lines — commons ahead by 24 lines. This is NOT an error — the line-level set-difference sync handles this correctly by only appending profile-lines-not-in-commons, so extra commons lines are preserved (not overwritten). The sync is one-directional: profile → commons append-only, never truncating commons. Do NOT attempt to "fix" this by copying commons back to profile or by truncating commons. The two files are allowed to diverge; commons is a superset that absorbs profile lines over time.

67. **Commons ingestion_log.jsonl accumulates massive historical bloat — 2-4x+ profile line count is normal** — The commons ingestion log receives writes from multiple sources: the heartbeat script (when it targets commons directly), caller backups (when incorrectly written to commons per gotcha #62), and the line-level sync from profile. Over time, commons ingestion_log grows to 2-4x the profile count. Confirmed 2026-06-18: commons ingestion was 28,393 lines vs profile 11,692 lines (2.4x). Confirmed 2026-06-19: commons ingestion was 41,409 lines vs profile 12,278 lines (3.4x) — the ratio continues to grow over time as commons accumulates historical entries from pre-profile-era direct writes. This is a known cosmetic issue — the profile ingestion_log is the authoritative source and is the one read by the heartbeat's cross-reference dedup. The commons copy is a lagging superset. Do NOT attempt to deduplicate or truncate commons ingestion_log — it has no operational impact (the heartbeat reads from profile). The gap will continue to grow slowly over time and may exceed 4x over months.

62. **Caller backup writes MUST target profile path, NOT commons — writing to commons creates duplicate/offset evidence lines** — When the caller writes backup evidence or ingestion records, the target MUST be the profile-scoped path (`/root/.hermes/profiles/indigo/commons/data/mentor/`), NOT `/root/.hermes/commons/data/mentor/`. The profile is the authoritative source; commons receives data only via the line-level set-difference sync run after each heartbeat. If the caller writes directly to commons: (a) the sync copies the script's version from profile (with wrong `active_skills_30d`) to commons, (b) the caller's corrected version is also in commons, (c) two evidence lines exist for the same run — one wrong, one correct. This confuses gap detection and metrics. **The rule: write once, to profile. Let sync handle commons.** Confirmed 2026-06-16: backup evidence written to commons path created duplicate lines; required re-writing to profile + re-sync.

## Heredoc Content — Ampersand Triggers Background Detection

64. **`&` inside heredoc content triggers terminal background detection — exit_code=-1** — When writing JSON or other content via `cat > file << 'EOF'`, if the content contains `&` (e.g., in URLs, JSON strings with `&`, or markdown), the terminal tool's shell parser misinterprets it as a background operator. The entire block exits with `exit_code=-1` and error "Foreground command uses '&' backgrounding". **Fix:** Use Python heredocs (`python3 << 'PYEOF'`) to write JSON files instead of shell heredocs. For non-JSON content, escape `&` as `\&` or write via Python. Confirmed 2026-06-17: `cat > journal.json << 'EOF'` with JSON containing `&` in a URL string failed with exit_code=-1; same content written via `python3 << 'PYEOF'` with `json.dump()` succeeded.

64a. **Inline `python3 << 'PYEOF'` heredoc writes to profile paths can silently fail — use `/tmp/script.py` file for critical writes** — When the heartbeat correction workflow writes evidence via an inline `python3 << 'PYEOF'` heredoc targeting profile paths (e.g., `open(DATA_DIR + "/evidence.jsonl", "a")`), the write can silently fail (0 delta on `wc -l`). This is the same intermittent Python write failure pattern as gotcha #23, but it affects the caller's backup writes, not just the script's. **Fix:** For critical evidence/ingestion writes, write the Python code to a `/tmp/script.py` file first (`cat > /tmp/write_evidence.py << 'SCRIPTEOF'` ... `SCRIPTEOF`), then invoke it as `python3 /tmp/write_evidence.py`. The file-based invocation has higher persistence reliability than inline heredocs. Confirmed 2026-06-18: inline heredoc evidence write failed (0 delta), file-based invocation succeeded (delta +1). Always verify with `wc -l` regardless of method.

## Sed Template Substitution for JSON

68. **`sed -i "s|PLACEHOLDER|$VAR|g"` for journal writing silently produces `.json` when `$VAR` is empty** — When using sed to replace placeholders in a journal template, if `$VAR` is unset, empty, or uses inconsistent naming (e.g., `RUN_ID` vs `RUNID`), sed substitutes an empty string. A placeholder like `${RUN_ID}.json` becomes literally `.json`. **Fix:** Do NOT use sed for JSON file construction. Use Python heredocs (`python3 << 'PYEOF'`) with `json.dump()` and hardcoded paths/values computed inside Python. If you must use shell variable interpolation in filenames, compose the full path in a separate variable first and `ls` the result before writing. The sed approach is especially dangerous because it silently succeeds (exit code 0) while producing a corrupt filename. Confirmed 2026-06-19: `sed -i "s|RUN_ID_PLACEHOLDER|$RUN_ID|g"` with `$RUN_ID` unset produced `.json`; a second sed for timestamp also failed silently.

## Deep Heartbeat — Single-Path Scan Gap

32. **`cron-heartbeat-deep.py` only scans `JOURNALS_ROOT` (commons), misses profile-scoped journals** — FIXED 2026-06-13: Use `scripts/cron-heartbeat-deep-dualpath.py` which scans both paths. See `references/deep-heartbeat-dual-path.md`. Confirmed: stock script scanned 168 files, dual-path wrapper scanned 6,781 files (40x more). Also writes to profile-scoped data dir for light heartbeat consistency. `active_coverage` capped at 1.0 (raw stored separately as `active_coverage_raw`).
    ```python
    okr_str = ", ".join(f"{k}={v['status']}" for k, v in okr_scores.items())
    print(f"  OKRs:                 {okr_str}")
    ```
    Confirmed 2026-06-06T19:01Z — script crashed on first run, fixed in-place.
    **Re-fixed 2026-06-14:** The same f-string SyntaxError recurred on line 276 of `cron-heartbeat-deep-dualpath.py`. The inline f-string `f"...{', '.join(f'{k}=...')}"` was replaced with a two-step: `okr_str = ", ".join(...)` then `print(f"...{okr_str}")`. Fix persisted to script.

## OKR Measurement

34. **`orchestration_success_rate` OKR scoring deflates by counting `unknown` as non-success** — The OKR computes `success / (success + error + unknown)`, but `unknown` outcomes are journals that lack an explicit outcome field AND have no `error` key — they are effectively successful runs (per `normalize_outcome()` which defaults to `success` when no error is present). The OKR should either: (a) count `unknown` as success: `(success + unknown) / total`, or (b) use `success / (success + error)` as the denominator. **IMPORTANT (2026-06-17):** Script-generated evidence records (gotcha #58) have `outcome` field **entirely missing** — `r.get("outcome")` returns `None`, NOT the string `"unknown"`. The correct check is `r.get("outcome") in ("success", None) and "error" not in r`, NOT `r.get("outcome") in ("success", "unknown")`. Using the string `"unknown"` will miss `None` records and report falsely low success rates (e.g., 0.50 instead of 1.0). Confirmed 2026-06-17: 10 of 20 recent evidence records had `outcome=None` (script-written), 10 had `outcome="success"` (callercorrected). Correct rate: 1.0. Naive string check: 0.50.
    Current behavior: with 81% success and 19% unknown, the OKR reports FAIL at 0.81 even though error_rate is 0.0000. This is a measurement artifact, not a real failure. Confirmed 2026-06-06: orchestration_success_rate=FAIL (0.8122) while error_rate=PASS (0.0000).
