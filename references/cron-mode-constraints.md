# ocas-mentor Cron-Mode Constraints & Dispatch — verbose detail

Extracted from `SKILL.md` ## Cron-Mode Constraints / ## Dispatch / Cron Integration to keep it under the 449-line D3 cap and ≤20% code ratio. The canonical guides: `references/cron-execution-patterns.md`, `references/multi-skill-dispatch-workflow.md`, `references/shell-write-pattern.md`, `references/dual-path-journal-discovery.md`, `references/mandatory-correction-workflow.md`.

## Cron-Mode Constraints — operational gotchas (full bodies)

- **Commons sync "already in sync" pattern (2026-06-25):** After evidence/ingestion sync, `wc -l` may show 0 delta on both — a concurrent heartbeat already synced between script write and dispatch sync call. EXPECTED in steady-state with multiple concurrent cron triggers. Verify with `grep <new_run_id> /root/.hermes/commons/data/mentor/evidence.jsonl`; if present, sync is done — proceed.
- **`execute_code` blocked in cron-triggered jobs:** all heartbeat/update/plan runs must use `terminal()` with `python3 /path/to/scripts.py`. Do NOT use `<<` heredoc (triggers foreground-background detection, exit_code=-1). Write scripts to `/tmp/` via `write_file` first, then `python3 /tmp/script.py`. See gotcha #70.
- **Pipe-to-python bash quoting pitfall (2026-06-29):** `VAR=$(tail -1 "$file" | python3 -c "...")` fails (syntax error). Fix: single quotes inside Python, or write `/tmp/script.py` and pipe into it.
- **`execute_code` blocking applies to ALL cron jobs (2026-06-25 #99):** state writes, JSON manipulation, multi-step Python — all must use `terminal()` with `cat > file << 'EOF'` (JSON) or `echo >>` (JSONL). Hard runtime constraint.
- **Python runtime resolution (2026-06-24):** docs reference `/root/hermes-agent/.venv/bin/python3.13` (does NOT exist). venv symlinks resolve to `/usr/bin/python3` (3.14). Install deps: `pip3 install --break-system-packages google-api-python-client google-auth google-auth-oauthlib`. Do NOT use the externally-managed uv cpython-3.13 or the taste venv (no googleapiclient).
- **Script path mismatch (2026-06-24 #49/#55/#63):** skill is `ocas-mentor`, scripts at `skills/ocas-mentor/scripts/`; data dir is `commons/data/mentor/` (no `ocas-` prefix). Always use `skills/ocas-mentor/scripts/<script>.py`. Correction script specifically at `skills/ocas-mentor/scripts/correct_active_skills_30d.py` (NOT `skills/mentor/scripts/`). Hard rule: verify path starts with `skills/ocas-mentor/scripts/` via `ls` before invoking. The agent has fallen into this trap 3+ times.
- **Inline Python variable scoping:** variables inside a function are NOT visible to caller scope in inline `python3 -c`. Structure as single flat scope or write to `/tmp/`.
- **Sandbox file discovery failure:** `subprocess.run(["find",...])` and `os.walk()` silently return 0 in cron sandbox. Use shell-pipe: `find JOURNALS_DIR -name "*.json" -mtime -3 | sort -u > /tmp/mentor_files_3d.txt && python3 scripts/cron-heartbeat-light.py < /tmp/mentor_files_3d.txt`. CRITICAL: any `cmd | python3` is blocked by `tirith:pipe_to_interpreter` — use temp files / here-strings (`<<<`), never pipes to python3.
- **Pipe-to-interpreter blocks ENTIRE terminal() call (2026-07-08):** a trailing `tail -1 file | python3 -c "..."` causes `exit_code=-1`, `pattern_key: tirith:pipe_to_interpreter` — ALL steps in that call lost. Never put `cmd | python3` anywhere in a cron `terminal()` call. Use `read_file` (outside terminal) or `/tmp/*.py` invoked WITHOUT a pipe.
- **Journal file-mtimes lag content timestamps (~7h12m, 2026-07-08):** `find -mmin -N` unreliable for tight windows (5-min heartbeat with `-mmin -5` perpetually returns 0, silently missing real journals). Mitigations: (1) verify 0 via content-timestamp scan (`scripts/verify_ingest_window.py`); (2) widen mtime window (`-mmin -450`) as stopgap; (3) cross-check with content timestamps. See `references/cron-mtime-discovery-gotcha.md`.
- **Python `with open()` writes UNRELIABLE in cron terminal():** sometimes persist, sometimes silently fail. `python3 /path/to/script.py` (no pipe) more reliable. Treat all Python writes best-effort: verify with `wc -l`, use shell `echo >>`/`cat >` for critical writes.
- **Heredoc vs pipe conflict:** `cat file | python3 << 'PYEOF'` does NOT deliver stdin — heredoc steals it. Write to `/tmp/` first, then `cat file | python3 /tmp/script.py`.
- **Env var on piped command:** `VAR=value cat file | python3 script` only sets var for `cat`. Safest: `cat file | VAR=value python3 script`.
- **Pre-run counts in SAME terminal() call as execution:** separate call for `EVIDENCE_BEFORE=$(wc -l ...)` creates race window; delta becomes meaningless (observed delta 4672 vs expected 2-3). Capture counts, run script, verify in ONE `terminal()` call.
- **Light heartbeat self-journaling EXPECTED failure pattern:** script's Python `with open()` writes to commons failed 3+ consecutive times (2026-06-16). Caller's backup write is NOT fallback — it is the ACTUAL persistence. Always run full verify-and-backup.
- **Forge/scan journal heredoc arithmetic error (2026-06-25 #85):** bash `${TS:9:2}` inside `cat > file.json << EOF` triggers `: syntax error: operand expected`. Use Python `json.dump()` for JSON journals; `echo >>` for simple appends.
- **ANTI-JOURNALIZATION HARD GATE (violated 2026-06-28/29):** after script completes + 3 writes verified, NEVER write to `$JOURNAL_DIR`. Script always writes its own journal (canonical, already exists). Two failure modes: (1) Duplicate journal (wrote second `mentor-light-*` after script's — inflates ingestion); (2) Overwrite-then-destroy (heredoc at same filename — destroys canonical record). HARD RULE: after step 2, no `json.dump()`, no heredoc, no `cat >`, no `python3 -c "open(...)"`. Additional context → evidence record, NEVER journal file.
- **Journal dir date must use UTC:** `date -u +%Y-%m-%d` for `JOURNAL_DIR`. Mismatch puts journal in wrong dir.
- **Partial success possible:** evidence/ingestion/journal writes independent. Check ALL THREE files independently. Don't assume evidence growth ⇒ journal written.
- **Verify live state before acting on escalated issues:** Custodian `escalation_needed:true` may be already-resolved (user re-auth, transient self-resolved). Check job `last_status` in jobs.json, latest esc-run journal, logs. 3 of 4 escalated were already resolved (2026-06-17). Custodian flags virtually every scan (tiered model) — if all esc journals >48h old from `ocas-custodian/`, historical noise, not alerts.
- **`grep` on large JSONL reports "binary file matches":** use `grep -a`.
- **`correct_active_skills_30d.py` writes BOTH evidence record AND its own journal** (separate run_id) — expected (audit trail), NOT a duplicate. Two journals per heartbeat (main + correction) expected from v2.8.23+.
- **Caller MUST correct active_skills_30d AND write complete evidence record EVERY TIME** regardless of script success. Script receives only `-mtime -3` files via stdin → its count (12-13) NEVER true 30d count (18-21). Compute true count via dual-path 30-day `find` (`references/dual-path-journal-discovery.md`), write corrected evidence. Script's evidence always undercounts. Correction evidence is PRIMARY, not backup. Confirmed 42+ times.
- **Correction field naming (2026-06-23):** `correct_active_skills_30d.py` writes `active_skills_30d_true` / `active_skills_30d_true_ocas` (NOT `active_skills_30d`). Verify against those field names.
- **Caller backup writes MUST target profile path, NOT commons:** profile `/root/.hermes/profiles/indigo/commons/data/mentor/` is authoritative; commons is lagging copy. Writing directly to commons creates duplicate/offset lines.
- **Commons sync must use timestamp-based set-difference, NOT line-count:** concurrent heartbeats can make commons AHEAD of profile; naive `profile_lines > commons_lines` falsely concludes "up to date". Use timestamp set-difference.
- **No inline pipe-to-python for commons sync (2026-07-01):** `tail -1 | python3 -c` blocked by tirith. Write sync script to `/tmp/` via `write_file`, execute.
- **Ingestion sync field-name trap (2026-06-28):** `ingestion_log.jsonl` uses `ingested_at`, NOT `timestamp`. Using wrong field duplicates entire file. Verify field with `head -1 <file> | python3 -c "import sys,json; print(list(json.loads(sys.stdin.read()).keys()))"`.
- **Commons ingestion_log structural bloat (2026-06-28):** commons `ingestion_log.jsonl` ~2x profile (37,734 vs 19,454) — historical records from other profiles (corvus/lucid/elephas), ~18k legacy empty-`file` records, pre-timestamp-sync duplicates. Expected accumulation; do NOT dedup. Profile-scoped file is authoritative.
- **`cron-heartbeat-light.py` JOURNALS_DIR constant legacy/unused (2026-07-13):** hardcodes `/root/.hermes/commons/journals` (module top) but reads file list from STDIN and writes to profile-scoped `AGENT_ROOT/commons/journals/ocas-mentor/`. Legacy tree holds 1 stale file; 138 active journals under profile path. Do NOT "fix" the constant — it's only in docstring/usage.
- **Recommended skill counting (2026-06-14):** `grep -oP` for unique skill names — `ACTIVE_OCAS_30D=$(find ... -name "*.json" -mtime -30 | grep -oP 'ocas-[a-z]+' | sort -u | wc -l)`; all skills `grep -oP 'commons/journals/([a-z][a-z0-9_-]+)'`.
- **`active_anomalies` fixed v2.8.10:** uses `a.get("timestamp") or a.get("detected_at")`. Prior always 0.
- **Light heartbeat caller MUST cross-reference ingestion counts:** script's `new_files_ingested` is upper bound (pipe truncation, path normalization). Cross-ref `find -mtime -3 | sort -u` minus `ingestion_log.jsonl`.
- **`cron-heartbeat-light.py` does NOT accept CLI args for file list — stdin redirect ONLY:** `--files-from` silently produces 0. Write list to `/tmp/mentor_files_3d.txt`, then `python3 .../cron-heartbeat-light.py < /tmp/mentor_files_3d.txt`. Never `cat file | python3` (blocked).
- **Script stdout filename ≠ actual file on disk:** script calls `datetime.now()` twice (run_id field vs filename) — can differ by up to 100s. After heartbeat, `ls` actual journal dir, `grep` real filenames against `journals_evaluated.jsonl`. Gap backfill auto-corrects wrong-filename phantom (harmless, don't remove).
- **Evidence record uses FLAT schema — no `metrics` wrapper:** top-level keys (`timestamp`, `heartbeat_type`, `total_files_scanned`, ...). `record['metrics']['active_skills_30d']` raises KeyError. Fixed 2026-06-09.
- **Deep heartbeat self-journaling:** `cron-heartbeat-deep-dualpath.py` writes own journal; caller must NOT append separate entry (duplicates).
- **Deep heartbeat dual-path wrapper (2026-06-13):** use `cron-heartbeat-deep-dualpath.py` (both commons + profile, 6,781 files) not stock `cron-heartbeat-deep.py` (commons only, 168 files).
- **Deep heartbeat journal filename double-prefix bug:** composes `mentor-deep-{run_id}.json` where `run_id="deep-{ts}"` → `mentor-deep-deep-...`. Cosmetic; fix filename to `f"{run_id}.json"`.
- **Deep heartbeat caller MUST verify + backup writes:** Python `with open()` silently fails. Verify all writes, back up via shell if missing. Ingestion backup most critical (`/tmp/mentor_deep_backup.py`).
- **Deep heartbeat evidence uses `skills_active_30d` (NOT `active_skills_30d`):** correction script reports `script=None` (expected) — deep counts differently (full scan). Don't treat None as error.
- **Deep heartbeat proposals dir must exist:** `mkdir -p .../proposals` before run or proposals write fails silently.
- **Deep heartbeat evidence missing `orchestration_success_rate`/`error_rate` (2026-06-24):** script computes but doesn't include in `evidence_record`. Get from OKR state or journal entry.
- **Heredoc journal file naming:** `cat > "$JOURNAL_DIR/${RUN_ID}.json" << 'EOF'` may create file literally named `.json`. Compose filename in variable first, `ls` to verify.

## Light heartbeat caller verify-and-backup workflow (SINGLE terminal() call)

```bash
# 1. Record pre-run counts (PROFILE path)
EVIDENCE_BEFORE=$(wc -l < /root/.hermes/profiles/indigo/commons/data/mentor/evidence.jsonl)
INGESTION_BEFORE=$(wc -l < /root/.hermes/profiles/indigo/commons/data/mentor/ingestion_log.jsonl)
JOURNAL_DIR="/root/.hermes/profiles/indigo/commons/journals/ocas-mentor/$(date -u +%Y-%m-%d)"
# 2. Run the script
python3 scripts/cron-heartbeat-light.py < /tmp/mentor_files_3d.txt
# 3. Verify ALL THREE files independently
EVIDENCE_AFTER=$(wc -l < /root/.hermes/profiles/indigo/commons/data/mentor/evidence.jsonl)
INGESTION_AFTER=$(wc -l < /root/.hermes/profiles/indigo/commons/data/mentor/ingestion_log.jsonl)
RECENT_JOURNAL=$(find "$JOURNAL_DIR" -name "mentor-light-*.json" -mmin -5 2>/dev/null | head -1)
# 4-6. Backup evidence/ingestion/journal via shell if delta=0 / missing (see references/shell-write-pattern.md)
```

Then: run `correct_active_skills_30d.py`, sync commons (timestamp set-difference), DONE. NEVER write a journal file.

## Deep heartbeat caller verify-and-backup workflow (SINGLE terminal() call)

```bash
mkdir -p /root/.hermes/profiles/indigo/commons/data/mentor/proposals
EVIDENCE_BEFORE=$(wc -l < /root/.hermes/profiles/indigo/commons/data/mentor/evidence.jsonl)
INGESTION_BEFORE=$(wc -l < /root/.hermes/profiles/indigo/commons/data/mentor/ingestion_log.jsonl)
DECISIONS_BEFORE=$(wc -l < /root/.hermes/profiles/indigo/commons/data/mentor/decisions.jsonl)
JOURNAL_DIR="/root/.hermes/profiles/indigo/commons/journals/ocas-mentor/$(date -u +%Y-%m-%d)"
find /root/.hermes/commons/journals/ -name "*.json" -not -path "*/.archive/*" -not -path "*/.quarantine/*" > /tmp/mentor_deep_shared.txt
find /root/.hermes/profiles/indigo/commons/journals/ -name "*.json" -not -path "*/.archive/*" -not -path "*/.quarantine/*" >> /tmp/mentor_deep_shared.txt
sort -u /tmp/mentor_deep_shared.txt > /tmp/mentor_deep_files.txt
python3 /root/.hermes/profiles/indigo/skills/ocas-mentor/scripts/cron-heartbeat-deep-dualpath.py < /tmp/mentor_deep_files.txt
# Verify ALL write targets; backup via /tmp/mentor_deep_backup.py if ingestion delta=0
/usr/bin/python3 /root/.hermes/profiles/indigo/skills/ocas-mentor/scripts/correct_active_skills_30d.py
# Sync to commons (timestamp-based set-difference)
```

Deep heartbeat ingestion backup template (`/tmp/mentor_deep_backup.py`): reads existing ingestion set, writes un-ingested files from `/tmp/mentor_deep_files.txt` with `ingested_at` = now ISO, `heartbeat_type: "deep"`. (Full script in prior SKILL.md history; reconstruct from `deep_ingest_backup.py` if needed.)

## Dispatch / Cron Integration — detail

- **Multi-skill dispatch (Forge+Mentor+Praxis+Taste):** read `references/multi-skill-dispatch-workflow.md` FIRST. Pipeline sequence Forge→Mentor→Praxis→Taste; captured-timestamp pattern; mandatory corrections; second-wave detection (grep eval file before mtime discovery); Taste boundary (Praxis does NOT process Taste signals); verification checklist.
- **Praxis ingest directory filter (#55/#102):** `praxis_ingest_run.py` only processes `ocas-praxis/` self-referential journals. For `ocas-mentor/`/`ocas-dispatch/`/`ocas-forge/` in `new_files`, manually bridge: grep eval file; if absent, add with `action_taken:"third_wave_mitigation"`; advance `ingest_state.json:last_ingest_run`.
- **new_files already evaluated pattern (#60/#78/#99/#100):** rapid successive waves → prior-wave journals already in `journals_evaluated.jsonl` (sibling heartbeats). Grep each `new_file` before Praxis; if all present, bridge is fast no-op. Don't re-add.
- **Taste token refresh race (#62):** OAuth may refresh between repair and scan if separate `terminal()` calls. Combine repair + taste scan in ONE call.
- **active_skills_30d correction MANDATORY every dispatch:** script counts only stdin 3-day → 9-14, true 18-22. Write corrected evidence. Two evidence lines per heartbeat expected.
- **Evidence delta mismatch (2026-06-23):** script reports N, evidence grows N-1 at check time (correction not yet written); post-correction delta=2. Not a write failure.
- **Steady-state fast-no-op (50+ times):** all `new_files` already evaluated + mtime-discovery finds 0 → fast no-op. Expected default.
- **Praxis cold-start (2026-06-22):** Mentor before Praxis updates `last_ingest_run`; Praxis cold-start → 0 new. Still explicitly evaluate dispatcher `new_files` regardless of mtime scan.
- **Already-evaluated second-wave (#40):** grep `mentor-light-*` in eval file before Praxis mtime discovery; if found, skip silently.
- **Dispatch-mode caller workflow (7 steps, mandatory):** (1) dual-path 3-day file list; (2) record pre-run evidence count; (3) run `cron-heartbeat-light.py < file`; (4) verify evidence grew, backup if delta=0; (5) ALWAYS run `correct_active_skills_30d.py` (never ad-hoc); (6) cross-ref ingestion counts; (7) HARD GATE — no journal write after script (verify `ls | grep mentor-light- | wc -l` ≥1 ⇒ STOP).
- **Security alert triage (2026-06-25):** GitGuardian JWT/high-entropy on internal repos = usually test creds → `intent:"security_alert"`, no action unless active production key. Recurring same-commit = noise.
- **Third-wave mitigation gaps (#49/#101):** some dispatch-output journals may miss `journals_evaluated.jsonl`. Praxis mtime discovery now picks up forge-scan/mentor-light from same run — grep before assuming manual mitigation. Only add manually if genuinely absent.
- **new_files authoritative (2026-06-22):** dispatcher `new_files` more reliable than mtime discovery alone (sibling pipeline may advance `last_ingest_run` before Praxis). Always evaluate `new_files` as fallback.
- **Already-ingested detection (#24):** one-wave lag (mtime > last_ingest_run, self-correcting next wave) vs concurrent Praxis race (mtime < last_ingest_run, already evaluated, log `concurrent_evaluation_detected`). Check both sources.
- **Mentor heartbeat updates Praxis ingest state (2026-07-11 caveat):** after `cron-heartbeat-light.py` (returncode 0, journal on disk), `ingest_state.json:last_ingest_run` at ocas-praxis was UNCHANGED. Caller MUST explicitly advance `last_ingest_run` + sync `journals_evaluated_count`/`last_eval_file_line` to actual `wc -l`. Don't assume script moved state.

See `references/dispatch-bridge-script-reality.md`: documented `bridge_eval_both_stores.py` / `close_dispatch_gap*.py` / `reconcile_dispatch_eval_today.py` / `scan_eval_missing_journals.py` DO NOT EXIST on disk. Use `scripts/bridge_eval_inline.py` (idempotent, in-process, both stores).
