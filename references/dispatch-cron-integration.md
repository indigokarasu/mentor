# Dispatch / Cron Integration (extracted from SKILL.md)

Extracted from SKILL.md to keep the skill under the 5,000-token budget. Load this reference for the full dispatch/cron caller workflows, second-wave/third-wave mitigation, and recovery contract details.

## Dispatch / Cron Integration

## Workflow

When triggered by the dispatcher or a cron job, the workflow proceeds as follows:

**Single-skill dispatch (Mentor only):** Follow the standard light heartbeat workflow above.

**Multi-skill dispatch (Forge + Mentor + Praxis):** Read `references/multi-skill-dispatch-workflow.md` FIRST. The consolidated workflow covers:
1. Pipeline sequence (Forge → Mentor → Praxis → Taste) with timing dependencies
2. Captured timestamp pattern (preventing cross-pipeline state collision)
3. Mandatory corrections (active_skills_30d, third-wave mitigation, gap backfill)
4. Second-wave / fast-no-op detection (grep eval file before mtime discovery)
5. Taste boundary (Praxis does NOT process Taste signals)
6. Verification checklist (all pipelines clean before exit)

**Praxis ingest script directory filter (confirmed 2026-06-24 dispatch #55, #102):** The `praxis_ingest_run.py` script only processes journals from the `ocas-praxis/` directory (its own self-referential journals). It does NOT evaluate journals from `ocas-mentor/`, `ocas-dispatch/`, or `ocas-forge/`. When the dispatcher lists journals from these directories in `new_files`, the dispatch caller must manually:
1. Check `journals_evaluated.jsonl` for the journal filename
2. If not present, manually add with `action_taken: "third_wave_mitigation"` and a note explaining the directory filter
3. Update `ingest_state.json:last_ingest_run` past the journal's mtime
This is NOT third-wave mitigation for self-referential journals — it is a manual bridge for cross-skill journals that the ingest script's directory filter excludes. **Confirmed #102:** `dispatch-triage-20260625T141334Z.json` in `ocas-dispatch/` was NOT auto-ingested and required manual bridge during third-wave mitigation.

**Dispatcher `new_files` already evaluated pattern (confirmed 2026-06-25 dispatch #60, #78, #99, #100):** When multiple dispatch waves fire in rapid succession (same day), journals from prior waves are typically already in `journals_evaluated.jsonl` — ingested by sibling Praxis heartbeats between waves. Before running Praxis ingest, always grep `journals_evaluated.jsonl` for each dispatcher `new_file` filename. If all are present, the bridge step is a fast no-op and Praxis mtime-based discovery will find only genuinely new self-referential journals. Do NOT re-add or re-evaluate — this is expected and correct behavior.

**Taste token refresh race in multi-skill dispatch (confirmed 2026-06-25 dispatch #62):** When the dispatch includes Taste (`taste_new_data`), the OAuth library may refresh the token between the repair call and the scan call if they're in separate `terminal()` invocations. The repair writes a clean expiry, but seconds later the scan sees `+00:00` again. Fix: combine token repair + taste scan in a single `terminal()` call. See `ocas-taste/references/token-repair.md` § Failure Mode 3.

**Quick reference for multi-skill dispatch:** The consolidated workflow lives in `references/multi-skill-dispatch-workflow.md`. For recent confirmed-clean runs, see:
| `references/session-20260624-dispatch-45.md` | Dispatch #45 (2026-06-24): second-wave Praxis skip, third-wave mitigation applied, active_skills_30d 10→22 |
| `references/session-20260624-dispatch-46.md` | Dispatch #46 wave 2 (2026-06-24): clean sweep all pipelines, email dedup (evidence log check), active_skills_30d 10→22 correction #24 |
- `references/session-20260624-dispatch-44.md` — dispatcher new_files timestamp mismatch, large gap backfill

1. **Forge**: Check for unprocessed proposals/decisions → no-op journal if clean
2. **Mentor**: Build dual-path list → run script → verify 3 writes → correct active_skills_30d → sync to commons
3. **Praxis**: Capture timestamp → mtime-based discovery → run dispatch ingest template → third-wave mitigation → gap backfill
4. Each pipeline writes its own journal — no cross-pipeline dependencies

**`active_skills_30d` correction is MANDATORY on every dispatch run.** The script receives only `-mtime -3` files via stdin, so its `active_skills_30d` (typically 12–14) is NEVER the true 30-day active skill count (typically 18–22). The caller must always compute the dual-path 30-day count and write a corrected evidence record. Two evidence lines per heartbeat is the expected pattern — the script's version (undercount) and the caller's corrected version. Confirmed 42+ times (2026-06-19 through 2026-06-25). See gotcha #29 and #58.

**Evidence delta mismatch: script reports N new files but evidence grows by N-1 (confirmed 2026-06-23).** The `cron-heartbeat-light.py` script reports "New files ingested: N" but `wc -l` on evidence.jsonl shows delta of N-1. This is the expected pattern: the script writes one evidence line, then the caller's `correct_active_skills_30d.py` writes a second evidence line (the correction). The script's stdout counter includes both lines, but the evidence file only grew by 1 at the time of the `wc -l` check (the correction hasn't been written yet). After the correction script runs, the total delta is 2 (matching the script's count). Do NOT treat this as a write failure — the post-correction `wc -l` will show the correct delta.

**Multi-skill dispatch pattern:** When the dispatcher triggers multiple skills in one dispatch (e.g., Forge + Mentor + Praxis), each pipeline runs independently and writes its own journal. No cross-pipeline dependencies. See `references/multi-skill-dispatch-pattern.md` for the full Forge → Mentor → Praxis pipeline.

**Cron dispatch verification shortcut (confirmed 2026-06-25):** After a cron-triggered dispatch completes all pipelines, a single-line verification confirms state:
```bash
echo "Forge: $(ls .../ocas-forge/2026-06-25/ | tail -2)" && echo "Mentor: evidence=$(wc -l < .../mentor/evidence.jsonl) ingestion=$(wc -l < .../mentor/ingestion_log.jsonl)" && echo "Praxis: eval=$(wc -l < .../journals_evaluated.jsonl)"
```

**Steady-state fast-no-op pattern (confirmed 50+ times):** When the dispatcher lists `new_files` but all are already in `journals_evaluated.jsonl` (evaluated by a concurrent heartbeat between dispatch waves), the Praxis mtime-based discovery finds only genuinely new self-referential journals. If all dispatcher `new_files` are already evaluated AND mtime-discovery finds 0 new journals, the dispatch is a fast no-op for that pipeline. This is the EXPECTED default — not an error or stale state.

**CRITICAL: Dispatch-triggered heartbeats — caller MUST always correct `active_skills_30d`** — Despite earlier documentation suggesting v2.8.23+ self-corrects, the `cron-heartbeat-light.py` script (as of v2.8.23) does NOT self-correct. It counts only from stdin (3-day piped files), producing `active_skills_30d` of 9–14 instead of the true 18–22. The script's evidence record will NOT show `correction: true`. The caller must ALWAYS compute the dual-path 30-day count and write a corrected evidence record. Two evidence lines per heartbeat is the expected pattern — the script's version (undercount) and the caller's corrected version. Confirmed 42+ times (2026-06-19 through 2026-06-25). See gotcha #29 and #58.

**Praxis cold-start interaction (confirmed 2026-06-22):** When the dispatcher runs Mentor before Praxis, the Mentor heartbeat script updates `ingest_state.json:last_ingest_run` to the current timestamp. If Praxis's `ingest_state.json` didn't exist before this dispatch, the Praxis cold-start initialization (with current timestamp) means 0 journals appear "new" — which is correct behavior for a fresh start. However, the dispatcher's `details.new_files` journals should still be explicitly evaluated even when the mtime-based discovery finds 0 new files. Always check the dispatcher's `new_files` list against `journals_evaluated.jsonl` independently of the mtime-based scan.

**Praxis "already evaluated" second-wave detection (confirmed 2026-06-24 dispatch #40):** After a multi-skill dispatch, the dispatcher may re-detect the mentor-light journal from the same dispatch as "new." Before running Praxis mtime-based discovery, always grep `journals_evaluated.jsonl` for the journal filename. If found (regardless of `action_taken`), Praxis has already evaluated it — skip silently. This is the correct no-op (not a failure, not a stale state). Example pattern:
```bash
grep -q "mentor-light-20260624T044239Z" <hermes-home>/profiles/indigo/commons/data/ocas-praxis/journals_evaluated.jsonl
# If exit code 0: already evaluated, skip Praxis silently
```
This prevents duplicate re-ingestion and unnecessary gap backfill on second-wave dispatches.

**Dispatch-mode caller workflow (confirmed 2026-06-22):** When triggered by `dispatcher.py` (not a standalone cron), the dispatch caller must:
1. Build dual-path 3-day file list: `find <hermes-home>/commons/journals/ <hermes-home>/profiles/indigo/commons/journals/ -name "*.json" -mtime -3 | sort -u > /tmp/mentor_files_3d.txt`
2. Record pre-run evidence count: `wc -l < <hermes-home>/profiles/indigo/commons/data/mentor/evidence.jsonl`
3. Run: `python3 {skill_dir}/scripts/cron-heartbeat-light.py < /tmp/mentor_files_3d.txt`
4. Verify evidence grew (delta should be ≥1). If delta=0, write backup evidence via `terminal()` Python one-liner.
5. **Always** run `python3 {skill_dir}/scripts/correct_active_skills_30d.py` to compute true dual-path 30-day count and write corrected evidence record to profile path. **NEVER write ad-hoc correction scripts** — use the existing script (see gotcha #74).
6. Cross-reference ingestion counts against `find ... -mtime -3 | sort -u` minus `ingestion_log.jsonl`.
7. **HARD GATE — DO NOT write ANY journal file after the script completes.** The script's journal is canonical and ALREADY EXISTS after step 2. There are TWO failure modes, BOTH observed in production:
   - **Duplicate journal (2026-06-29):** Caller wrote a second journal with a different `run_id` after the script's canonical journal already existed. Inflated `new_files_ingested` on next scan. Caught and deleted post-hoc, but the violation still happened.
   - **Journal overwrite (2026-06-28):** Writing a heredoc or `json.dump()` file with the SAME filename as the script's journal DESTROYS the canonical record.
   
   **VERIFICATION BEFORE ANY JOURNAL WRITE ATTEMPT:** Run `ls "$JOURNAL_DIR" | grep "mentor-light-" | wc -l`. If result ≥ 1, the script already wrote its journal. DO NOT WRITE. The heartbeat is OVER.
   
   Additional context goes in the evidence record (via `correct_active_skills_30d.py`), NEVER a journal file.

Steps 5–7 are mandatory regardless of script success. The script's evidence record (step 3) is always wrong on `active_skills_30d`. Do not skip the correction because the script reported "success." Confirmed 42+ times (2026-06-19 through 2026-06-25).

**Dispatch-mode caller workflow (confirmed 2026-06-22):** When triggered by `dispatcher.py` (not a standalone cron), the dispatch caller must:
1. Build dual-path 3-day file list: `find <hermes-home>/commons/journals/ <hermes-home>/profiles/indigo/commons/journals/ -name "*.json" -mtime -3 | sort -u > /tmp/mentor_files_3d.txt`
2. Record pre-run evidence count: `wc -l < <hermes-home>/profiles/indigo/commons/data/mentor/evidence.jsonl`
3. Run: `python3 {skill_dir}/scripts/cron-heartbeat-light.py < /tmp/mentor_files_3d.txt`
4. Verify evidence grew (delta should be ≥1). If delta=0, write backup evidence via `terminal()` Python one-liner.
5. **Always** run `python3 {skill_dir}/scripts/correct_active_skills_30d.py` to compute true dual-path 30-day count and write corrected evidence record to profile path. **NEVER write ad-hoc correction scripts** — use the existing script (see gotcha #74).
6. Cross-reference ingestion counts against `find ... -mtime -3 | sort -u` minus `ingestion_log.jsonl`.
7. **HARD GATE — DO NOT write ANY journal file after the script completes.** The script's journal is canonical and ALREADY EXISTS after step 2. There are TWO failure modes, BOTH observed in production:
   - **Duplicate journal (2026-06-29):** Caller wrote a second journal with a different `run_id` after the script's canonical journal already existed. Inflated `new_files_ingested` on next scan. Caught and deleted post-hoc, but the violation still happened.
   - **Journal overwrite (2026-06-28):** Writing a heredoc or `json.dump()` file with the SAME filename as the script's journal DESTROYS the canonical record.
   
   **VERIFICATION BEFORE ANY JOURNAL WRITE ATTEMPT:** Run `ls "$JOURNAL_DIR" | grep "mentor-light-" | wc -l`. If result ≥ 1, the script already wrote its journal. DO NOT WRITE. The heartbeat is OVER.
   
   Additional context goes in the evidence record (via `correct_active_skills_30d.py`), NEVER a journal file.

Steps 5–7 are mandatory regardless of script success. The script's evidence record (step 3) is always wrong on `active_skills_30d`. Do not skip the correction because the script reported "success." Confirmed 42+ times (2026-06-19 through 2026-06-25).

**Security alert triage (confirmed 2026-06-25):** GitGuardian (and similar) alerts on internal repos (e.g., `indigokarasu/indigo`) detecting JWTs or high-entropy secrets are typically test credentials, not active production secrets. Classify as `intent: "security_alert"` → **no action** unless the alert explicitly identifies an active production key. Recurring alerts on the same commit are noise — no escalation needed.

**Dispatcher second-wave pattern (confirmed 2026-06-21):** After the dispatch runs all three pipelines, the dispatcher re-scans and detects the mentor-light journal written by the dispatch's own run as "new." This is expected — the journal is genuinely new since the last dispatcher scan. The Praxis ingest should include the mentor-light journal from the dispatch run in its eval list to prevent re-processing. If a second dispatch wave fires, the mentor-light journal will already be evaluated and Praxis will find 0 new journals.

**Third-wave mitigation: journals_evaluated.jsonl gaps (confirmed 2026-06-24 dispatch #49, UPDATED 2026-06-25 dispatch #101):** After a multi-skill dispatch runs Praxis ingest, some dispatch-output journals may NOT appear in `journals_evaluated.jsonl` even though they were processed. Specifically: (1) journals from a PRIOR dispatch wave that were written between the wave's scan and the Praxis run, (2) forge-scan journals written by the current wave. The Praxis ingest script does NOT always add all relevant journals. **However (confirmed 2026-06-25):** The Praxis ingest script's mtime-based discovery now picks up forge-scan and mentor-light journals written during the same dispatch run. After running Praxis, `grep` the eval file for the forge-scan filename before assuming manual third-wave mitigation is needed. If present, skip — the script already evaluated it. Only add manually if genuinely absent:
```python
# Add missing journals to eval file (only if grep confirms absence)
entry = {'journal_id': 'ocas-forge/2026-06-25/forge-scan-XXX.json', 'evaluated_at': now_iso, 'action_taken': 'third_wave_mitigation'}
with open('.../journals_evaluated.jsonl', 'a') as f:
    f.write(json.dumps(entry) + '\n')
```
This prevents the dispatcher from re-detecting these journals as "new" in wave N+1.

**Dispatcher new_files as authoritative source (confirmed 2026-06-22):** When the dispatcher provides a `new_files` list in the dispatch details, this is the authoritative set of journals to evaluate — more reliable than mtime-based discovery alone. Journals can fall through the cracks of mtime-based discovery when `last_ingest_run` is updated by a sibling pipeline (e.g., Mentor heartbeat) before Praxis runs. The Praxis ingest should always evaluate the dispatcher's `new_files` list as a fallback, regardless of what mtime-based discovery finds. See Praxis SKILL.md § Dispatch / Cron Integration step 3.

**Already-ingested journal detection (confirmed 2026-06-24):** When the dispatcher lists a journal in `new_files` but it's already in `ingestion_log.jsonl` or `journals_evaluated.jsonl`, the journal was processed by a concurrent/recent heartbeat. Two distinct sub-patterns exist:

1. **One-wave lag:** Journal mtime > `last_ingest_run`. The journal is genuinely new but wasn't found by the current wave's mtime scan because `last_ingest_run` hadn't been updated yet. Self-correcting: the next wave's mtime scan will find it. Do NOT mark as `second_wave_no_op` — the work is pending.

2. **Concurrent Praxis race:** Journal mtime < `last_ingest_run` (a sibling Praxis cron updated `last_ingest_run` AFTER evaluating the journal). The journal is already in `journals_evaluated.jsonl` with an `evaluated_at` timestamp AFTER the journal's mtime. NOT self-correcting — the mtime-based scan will never find it again. Skip Praxis ingest for this journal, log `action: "concurrent_evaluation_detected"` in evidence. See `ocas-dispatch` skill's  for the full timeline and evidence structure.

Check both sources before running Praxis ingest. If found, mark as `already_ingested` in evidence and skip silently. This is NOT a second-wave false positive — the journal was genuinely new but already processed by a sibling pipeline.

**CRITICAL: Mentor heartbeat updates Praxis ingest state** — The `cron-heartbeat-light.py` script updates `ingest_state.json:last_ingest_run` when it writes evidence. If Praxis dispatch runs immediately after in the same multi-skill dispatch, its mtime-based journal discovery may find 0 new journals because the state timestamp moved forward. The dispatcher must capture `last_ingest_run` BEFORE running Mentor and pass it to Praxis. See Praxis SKILL.md § Dispatch / Cron Integration step 3.

**Caveat — heartbeat does NOT reliably advance Praxis ingest state (verified 2026-07-11):** In a multi-skill dispatch, after running `cron-heartbeat-light.py` via `python3 script.py < filelist` (returncode 0, heartbeat journal written to disk), `ingest_state.json:last_ingest_run` at `<hermes-home>/profiles/indigo/commons/data/ocas-praxis/` was UNCHANGED — it still held the prior-wave value. The dispatch caller MUST explicitly advance `last_ingest_run` itself after the heartbeat (and sync `journals_evaluated_count` / `last_eval_file_line` to the actual eval-file `wc -l`). Do NOT assume the script moved the state forward. A stale `last_ingest_run` is usually harmless (grep-based per-file classification wins over mtime discovery), but it means the state no longer reflects this wave's work and any later step that trusts it will read the prior-wave timestamp.

The script's `active_skills_30d` is the stdin-based count (3-day window, single path) — NOT the true 30-day active skill count. The correction is MANDATORY every time, not just when the script's write fails.

See `references/schemas.md` for storage layout and data schemas.

See `references/default-config.md` for default config.json.

See `references/workflow_plans.md` for available workflow plan templates.

Action Journal — every orchestration run, heartbeat pass, variant evaluation, and proposal emission. Include `entities_observed`, `relationships_observed`, `preferences_observed` with `user_relevance` field.

On first invocation, run `mentor.init`:

1. Create data directories and subdirectories
2. Write default `config.json` if absent
3. Create empty JSONL files
4. Create journal directory
5. Copy bundled plans to `plans/` directory
6. Register cron jobs if not already present
7. Log initialization as DecisionRecord

See `references/okrs-mentor.md` for full OKR definitions and targets.

Key OKRs: `orchestration_success_rate` (≥0.95), `evaluation_coverage` (≥0.90), `promotion_accuracy` (≥0.80).

**`orchestration_success_rate` scoring:** Computed as `(success + unknown) / total` — journals without explicit outcome fields (tagged `unknown`) are counted as successes since they have no `error` key. This corrects the prior measurement artifact where `unknown` was excluded from the numerator. See gotcha #34.

Implements the recovery contract from `spec-ocas-recovery.md`.

- **Evidence**: Every run writes an evidence record, including no-op runs. `not_activity_reason` mandatory.
- **Gap detection**: If gap exceeds 15min (light) or 24h (deep), logs `gap_detected`.
- **Degraded mode**: When Fellow or Forge unavailable, logs `degraded: <dependency>`.
- **Log compaction**: 30 days (no-op) / 90 days (error/gap). Last 7 days retained.

See `scripts/update_skill.sh` (centralized fleet updater).

