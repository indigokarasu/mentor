# Multi-Skill Dispatch Workflow (Forge → Mentor → Praxis)

**Consolidated from 50+ dispatches (2026-06-21 through 2026-06-26, dispatch ~#24).**

This reference consolidates the end-to-end procedure when the dispatcher triggers Forge + Mentor + Praxis in a single wave. Each pipeline runs independently, but timing and state-management dependencies require specific sequencing.

## Dispatch Trigger

The dispatcher (`dispatcher.py`) outputs JSON with `"has_work": true` and a `dispatches` array. When `"skill": "multi"`, the prompt names the specific skills to load. Parse the prompt, load each named skill, run each pipeline in order.

**Typical dispatch output for journal detection:**
```json
{
  "has_work": true,
  "dispatches": [
    {
      "type": "new_journals",
      "skill": "multi",
      "prompt": "New journal entries detected. Process them through all three pipelines...",
      "details": {
        "new_files": ["ocas-mentor/2026-06-23/mentor-light-20260623T231116Z.json", "..."],
        "latest_mtime": 1782256460.7447822,
        "latest_ts": "2026-06-23T23:14:20.744782+00:00",
        "count": 2
      }
    },
    {
      "type": "taste_new_data",
      "skill": "ocas-taste",
      "prompt": "New raw consumption signals detected (email, calendar, Spotify). Load ocas-taste skill and run the analysis pipeline...",
      "details": {
        "changes": {"signals": 2},
        "counts": {"extractions": 1071, "items": 1313, "signals": 5127}
      }
    }
  ]
}
```

**IMPORTANT:** `taste_new_data` is a **separate dispatch item** with its own `type`, `skill`, and pipeline. It runs independently of the journal pipeline sequence (Forge→Mentor→Praxis). When both `new_journals` and `taste_new_data` appear in the same dispatch, journal pipelines run first, then Taste runs. Taste produces its own journal in `ocas-taste/YYYY-MM-DD/`.

**Canonical data paths (confirmed 2026-06-29):**
- Praxis data: `/root/.hermes/profiles/indigo/commons/data/ocas-praxis/` (NOT `oras-praxis` — single-char typo causes silent "No such file or directory")
- Mentor data: `/root/.hermes/profiles/indigo/commons/data/mentor/`
- Forge data: `/root/.hermes/profiles/indigo/commons/data/ocas-forge/`
- Journals: `/root/.hermes/profiles/indigo/commons/journals/`

**CRITICAL: Path typo `oras-praxis` vs `ocas-praxis` (confirmed 2026-06-29):** When constructing the Praxis data directory path, a single-character typo (`oras-praxis` instead of `ocas-praxis`) causes `cp` and `python3` to fail with "No such file or directory". **Fix:** The canonical path is `/root/.hermes/profiles/indigo/commons/data/ocas-praxis/` — always verify with `ls -d /root/.hermes/profiles/indigo/commons/data/oca*` before constructing script paths. The skill name is `ocas-` (with `s`), not `ora-`.

**Critical path note:** Dispatcher `new_files` paths look like `ocas-mentor/2026-06-23/file.json` but actual files live at `/root/.hermes/profiles/indigo/commons/journals/<path>`. Always check both locations.

## Pipeline Sequence

### Phase 1 — Forge (Journal Scan)

1. Check `/root/.hermes/profiles/indigo/commons/data/ocas-forge/` for unprocessed `vp_*.json` (VariantProposal) or `vd_*.json` (VariantDecision) files
2. Cross-reference against `intake/processed/` and `processed/` directories
3. If nothing unprocessed: write no-op journal and exit
4. Write journal to `/root/.hermes/profiles/indigo/commons/journals/ocas-forge/YYYY-MM-DD/forge-scan-YYYYMMDDTHHMMSSZ.json`

**Forge journal schema:**
```json
{
  "run_id": "forge-scan-YYYYMMDDTHHMMSSZ",
  "timestamp": "ISO UTC",
  "action": {"result": "no_op", "unprocessed_proposals": 0, "unprocessed_decisions": 0},
  "findings": {"unprocessed_proposals": 0, "unprocessed_decisions": 0}
}
```

### Phase 2 — Mentor (Light Heartbeat)

1. **Build dual-path file list:**
   ```bash
   find /root/.hermes/commons/journals/ /root/.hermes/profiles/indigo/commons/journals/ -name "*.json" -mtime -3 | sort -u > /tmp/mentor_files_3d.txt
   ```

2. **Record pre-run counts:**
   ```bash
   EVIDENCE_BEFORE=$(wc -l < /root/.hermes/profiles/indigo/commons/data/mentor/evidence.jsonl)
   INGESTION_BEFORE=$(wc -l < /root/.hermes/profiles/indigo/commons/data/mentor/ingestion_log.jsonl)
   ```

3. **Run script (stdin redirect — NOT pipe):**
   ```bash
   python3 {skill_dir}/scripts/cron-heartbeat-light.py < /tmp/mentor_files_3d.txt
   ```
   ⚠️ Use stdin redirect (`< file`), **NOT** `cat file | python3 script`. Cron mode blocks `cat … | python3` via the `tirith:pipe_to_interpreter` security scanner (confirmed 2026-07-08): the pipe makes the **ENTIRE** `terminal()` call hang at `approval_pending` with no user present to approve, so the run silently stalls and produces no journal. The script reads its file list ONLY from stdin — CLI args (`--files-from`, etc.) are ignored and silently yield 0 files scanned. See `references/cron-execution-patterns.md` and the SKILL.md Cron-Mode Constraints for the full pattern.

4. **Verify all 3 writes independently** (partial success is possible):
   - Evidence: `wc -l` should show +1
   - Ingestion: `wc -l` should show +N
   - Journal: check for `mentor-light-*.json` in today's journal directory

5. **MANDATORY: Correct `active_skills_30d`:**
   ```bash
   python3 {skill_dir}/scripts/correct_active_skills_30d.py
   ```
   The script's stdin-based count (typically 11-14) is NEVER the true 30-day count (typically 18-22). The correction writes a second evidence record to the profile-scoped path.

6. **Sync to commons:**
   - Evidence: line-level set-difference, append new lines to commons
   - Ingestion: line-level set-difference, append new lines to commons
   - OKR state, anomalies, decisions: `cp -f` from profile to commons

7. **DO NOT write a separate caller journal** — the script's journal is canonical (gotcha #73).

**CRITICAL: Mentor updates Praxis `ingest_state.json:last_ingest_run`** — The `cron-heartbeat-light.py` script writes evidence which advances `last_ingest_run`. When Praxis runs after Mentor in a dispatch, the state timestamp is already PAST the dispatcher's `latest_ts`. Use the state's `last_ingest_run` as the mtime floor for Praxis discovery — do NOT force `CAPTURED_TS` (which would move the window backward and re-find already-evaluated journals). See `references/session-20260625-dispatch-073.md` for the confirmed pattern.

**⚠️ Divergence observed (2026-07-10): The "Mentor advances `last_ingest_run` past `latest_ts`" coupling is NOT reliably true.** In the 2026-07-10 dispatch, `ingest_state.json:last_ingest_run` REMAINED at `2026-07-10T04:48:47` after a Mentor light heartbeat ran at `05:16:30` — Mentor did NOT advance the Praxis state on that run. Consequence: the state value (`04:48:47`) was actually BEFORE the dispatcher's `latest_ts` (`04:51:31`), the opposite of the documented assumption. The Praxis ingest still worked correctly ONLY because the ingest template reads `ingest_state.json` and uses its value as the mtime floor by default (no `CAPTURED_TS` override was set). **Rule:** Always RE-READ `ingest_state.json:last_ingest_run` AFTER Mentor (and after every pipeline) to obtain the true mtime floor. Never assume Mentor advanced it, and never assume it is past `latest_ts`. Use whatever value is actually present — the Phase 3 step 1 logic already does this correctly; the only failure mode is assuming the documented coupling held. If you ever DO set `CAPTURED_TS`, derive it from the state value you just read, not the dispatcher's `latest_ts`.

### Phase 2.5 — Taste (Consumption Signal Pipeline)

When the dispatcher includes a `"type": "taste_new_data"` dispatch alongside journals, run this pipeline AFTER Forge→Mentor→Praxis. It is independent and produces its own journal.

**Trigger:** `taste_new_data` in the dispatches array.

**Pipeline:**
1. **Token repair** — Run the combined repair script AND the scan in a SINGLE `terminal()` call (chained with `&&`). The OAuth library refreshes the token on every `google_auth.py` initialization — if you run repair and scan as separate `terminal()` calls, the refresh happens between them, re-adding the `+00:00` suffix. A single combined call is mandatory:
   ```bash
   python3 -c "<repair script>" && cd <data_dir> && /usr/bin/python3 <scan script>
   ```
   Two separate calls WILL fail. See `ocas-taste` skill's "Pre-scan Token Repair" section for the full repair script and both failure modes.

2. **Run incremental scan:**
   ```bash
   cd /root/.hermes/profiles/indigo/commons/data/ocas-taste && /usr/bin/python3 /root/.hermes/profiles/indigo/skills/ocas-taste/scripts/taste_scan.py scan-incremental 24
   ```

3. **Parse output** — Extract `signals_created`, `cancellations`, `extractions` from JSON output.

4. **Write Taste journal** to `/root/.hermes/profiles/indigo/commons/journals/ocas-taste/YYYY-MM-DD/taste-scan-YYYYMMDDTHHMMSSZ.json`:
   ```json
   {
     "timestamp": "ISO UTC",
     "command": "taste.scan",
     "run_id": "taste-scan-YYYYMMDDTHHMMSSZ",
     "action": "signals_extracted",
     "result": "success",
     "findings": {
       "signals_created": 2,
       "cancellations": 0,
       "services_scanned": ["doordash", "instacart", "good_eggs", "tock", "opentable", "yelp", "amazon", "hotels"],
       "extractions": [{"venue": "...", "service": "...", "total": "$...", "domain": "restaurant"}]
     }
   }
   ```

5. **Handle token repair failure** — If the scan returns 0 results, check token file sizes with `wc -c`. A 0-byte token causes silent fallback to the wrong account. Report auth failure in output.

**Note:** Taste does NOT update Praxis state or `journals_evaluated.jsonl`. It only writes its own journal and updates `signals.jsonl` + `items.jsonl`.

### Phase 3 — Praxis (Journal Ingest)

1. **Determine mtime floor** — Read `ingest_state.json:last_ingest_run`. If it is PAST the dispatcher's `latest_ts` (common when Mentor ran first), use the state timestamp. Do NOT use `CAPTURED_TS` to move the window backward.
   ```python
   # Use Python, NOT find -newermt (which interprets timestamps as local time)
   state_path = '/root/.hermes/profiles/indigo/commons/data/ocas-praxis/ingest_state.json'
   with open(state_path) as f:
       state = json.load(f)
   last_ingest = state.get('last_ingest_run', '2020-01-01T00:00:00+00:00')
   li_dt = datetime.fromisoformat(last_ingest)
   li_ts = li_dt.timestamp()
   ```

2. **Find new journals** using mtime comparison:
   ```python
   # Walk both journal directories, compare os.stat(fp).st_mtime >= li_ts
   ```

3. **Check dispatcher's `new_files` as fallback** — Even when mtime-based discovery finds 0, the dispatcher's list may contain journals that fell through the cracks. **Taste journals in `new_files`:** Taste dispatch journals contain consumption signals (DoorDash, Instacart, etc.) that are self-contained in the Taste pipeline. Praxis does NOT process Taste signals — Praxis handles behavioral refinement from mentor/custodian/finch journals only. When a Taste journal appears in `new_files`, mark it as `action_taken: "taste_signal_skip"` in the eval file.

4. **Run ingest** — Copy the dispatch ingest template:
   ```bash
   cp {skill_dir}/templates/dispatch_ingest_template.py {data_dir}/dispatch_ingest_YYYYMMDD.py
   # If last_ingest_run is already past dispatcher latest_ts, NO CAPTURED_TS needed
   python3 {data_dir}/dispatch_ingest_YYYYMMDD.py
   # If you MUST override (rare), use the state timestamp, NOT the dispatcher's older timestamp:
   # If you MUST override (rare), use the state timestamp, NOT the dispatcher's older timestamp:
   # CAPTURED_TS=2026-06-25T05:09:54.000000+00:00 python3 {data_dir}/dispatch_ingest_YYYYMMDD.py

   ⚠️ ORDERING TRAP (confirmed 2026-07-07 and 2026-07-15): the ingest template advances
   `ingest_state.json:last_ingest_run` to NOW on its own. Gap backfill thresholds its scan on
   `mtime > last_ingest_run`. If gap backfill (step 6) runs AFTER this step, `last_ingest_run` is
   already NOW, so it silently finds 0 journals. You MUST run gap_backfill.py BEFORE this step,
   while `last_ingest_run` still holds the prior run's timestamp. gap_backfill only mutates backfill
   counters (never `last_ingest_run`), so running it early is safe and is the ONLY way it catches
   post-ingest / date-filter-missed journals. Re-read `ingest_state.json` AFTER this step (and after
   every pipeline) before any state update so your changes compose on top of the template's write.

5. **Third-wave mitigation** (mandatory, even when ingest finds 0):
   - Add ALL dispatch-output journals to `journals_evaluated.jsonl` with `action_taken: dispatch_output_skip`
   - This prevents the dispatcher from re-detecting the same journals
   - Dual-file sync (confirmed 2026-06-25 dispatch #114): the Praxis ingest script only writes to the
     profile-scoped eval file. You MUST manually sync the commons copy or the dispatcher re-detects on
     the next wave:
     ```bash
     # Check what's in profile but not in commons
     commons_eval="/root/.hermes/commons/data/ocas-praxis/journals_evaluated.jsonl"
     profile_eval="/root/.hermes/profiles/indigo/commons/data/ocas-praxis/journals_evaluated.jsonl"
     # Extract journal_id fields from both, find missing in commons, append
     ```
     Failure to sync causes re-detection on subsequent waves — the dispatcher may read the commons path.
   - **Automated bridge pre-registration (observed 2026-07-15):** A separate automated component (`bridge_eval_both_stores`) may ALREADY have registered the dispatcher's `new_file` journals into BOTH eval stores before your dispatch runs, tagged `action_taken: "post-dispatch-cleanup"`. When you reach third-wave mitigation, `grep` the journal in both profile AND commons eval FIRST — if present, do NOT double-add it, and do NOT treat "already in eval" as a signal the journal is stale or mis-processed. This is the expected steady-state for second-wave re-detections. Confirmed across consecutive 2026-07-15 dispatches (12:00Z and 12:35Z): the dispatcher `new_file` (`mentor-light-*.json`) was already in both eval stores via the automated bridge, so the Praxis pipeline correctly took the fast no-op path.

6. **Gap journal backfill** (run BEFORE the ingest template — mandatory):
   - ⚠️ ORDERING TRAP: the ingest template (step 4) advances `last_ingest_run` to NOW on its own. Gap backfill thresholds on `mtime > last_ingest_run`. If you run it AFTER step 4, `last_ingest_run` is already NOW → gap backfill finds 0 journals silently (no error, no catch). Run gap_backfill.py BEFORE step 4, while `last_ingest_run` still holds the PRIOR run's timestamp. gap_backfill only mutates backfill counters, never `last_ingest_run`, so running it early is safe and is the only way it catches post-ingest / date-filter-missed journals. Re-read `ingest_state.json` AFTER the template (and after every pipeline) before any state update so your changes compose on top.
   - Walk all journal directories, find journals with mtime > `last_ingest_run` (the PRIOR run value, since the template has not run yet) NOT in `journals_evaluated.jsonl`
   - Add eval entries with `action_taken: gap_backfill_entry`
   - Typically 0-5 per dispatch; **14,772 backfilled on 2026-06-25 dispatch #59** (accumulated from prior waves' dispatch-output journals written before `last_ingest_run` was advanced)
   - **Growing gap backfill pattern (observed 2026-06-24 through 2026-06-25):** Each dispatch that advances `last_ingest_run` "catches" all prior waves' dispatch-output journals. Counts escalated: 14,386 → 14,396 → 14,438 → 14,446 → 14,772 → 14,941. This is expected recovery — the eval file is accumulating the backlog. It will self-resolve once all prior-wave journals are backfilled, dropping to single-digit counts.
   - **Archive directory discovery (confirmed 2026-06-25 dispatch #72):** The `.archive/2026-04/` directory contains thousands of historical files (14,000+) that have never been in the eval file. When gap backfill walks all journal directories, these archive files appear as unevaluated candidates because their mtime predates `last_ingest_run`. A single backfill of 14,941 entries is normal when the archive directory is discovered for the first time. This is a one-time catch-up event, not a recurring backlog. After archive files are backfilled, subsequent dispatches return to single-digit counts.
   - **Post-catch-up backlog clearance (confirmed 2026-06-25 dispatch #97):** After the eval file clears the accumulated archive + non-archive backlog (dispatches #72 and #88), a subsequent dispatch can still produce 15,000+ gap backfill entries. This happens because `last_ingest_run` was advanced past the dispatcher's `latest_ts` by the Mentor script, but the eval file's gap backfill walk catches all dispatch-output journals from PRIOR waves that were written between waves but never evaluated. This is NOT a new backlog — it's the final clearance of residual entries. After this, gap backfill drops to 0-5. Confirmed: dispatch #97 produced 15,190 gap backfill entries immediately after #88's 15,106-entry catch-up.
   - **Extended post-catch-up clearance (confirmed 2026-06-25 dispatches #96–#102):** The >15K gap backfill pattern can persist for multiple consecutive dispatches as the eval file clears layers of accumulated dispatch-output journals from prior waves. Sequence: #88: 15,106 → #96: 15,238 → #97: 15,190 → #102: 15,255. Each advance of `last_ingest_run` catches MORE prior-wave journals that were written between waves but not yet evaluated. This is expected recovery behavior — the eval file is clearing a multi-layer backlog. Do NOT truncate the eval file or attempt to "fix" the backfill. After all residual dispatch-output journals are caught up, gap backfill drops to 0-5.
   - Large gap backfill counts (>1000) indicate either (a) `last_ingest_run` was not advanced for multiple dispatch cycles, (b) a previously-unscanned directory (like `.archive/`) was discovered for the first time, or (c) post-catch-up backlog clearance of residual dispatch-output journals from prior waves. All three are expected recovery behavior, not an error.

7. **Write Praxis journal** and clean up stale ingest script.

## Fully Caught Up State (Steady-State)

After the eval file accumulates all historical journals (including archive directories), dispatch enters a steady-state where:

- **Gap backfill = 0** consistently (no unevaluated historical journals remain)
- **Dispatcher `new_files` already in eval file** — same-day concurrent heartbeats process journals before the dispatch runs
- **Minimal work per dispatch**: only mandatory corrections (Mentor `active_skills_30d`) and third-wave mitigation for dispatch-output journals

**Signature of steady-state:** Gap backfill = 0 AND all dispatcher `new_files` already evaluated. This is NOT a failure — it means the system is healthy and current. Do NOT run gap backfill a second time or re-add journals. Apply third-wave mitigation, write the Praxis dispatch journal, advance state, exit.

**Transition event:** A sudden large gap backfill (>1000) indicates discovery of a previously-unscanned directory (e.g., `.archive/2026-04/`). This is a one-time catch-up, not recurring. After catch-up, steady-state resumes at 0 backfill.

Confirmed 2026-06-25 (dispatches #67, #69, #71, #73, #75): 5 consecutive dispatches with 0 gap backfill after #72's archive discovery (14,941 entries). Then 3 consecutive >15K backfills (#88: 15,106, #96: 15,238, #97: 15,190) cleared the residual backlog, after which steady-state resumes at 0-5 gap backfill. Dispatch #106 confirmed back to 1-entry gap backfill — eval file now at 38,773 entries. Dispatch #108: 0 gap backfill, eval file 38,792 — fully caught up (archive backlog cleared). Dispatch #134: 0 gap backfill, eval file 38,953 — steady-state confirmed (confirmation #46+). Dispatch ~#22 (2026-06-26): 2 gap backfill, eval file 39,374 — steady-state confirmed (confirmation #47+). Commons eval drift (39,380 > 39,377) fixed via `cp` profile→commons. Dispatches ~#24–#25 (2026-06-26): 0-1 gap backfill, eval file 39,432–39,436 — steady-state confirmed (confirmation #50+). Dispatch #147 (2026-06-26T07:45Z): 0 gap backfill, eval file 39,567 — steady-state confirmed (confirmation #55+). Dispatch #158 (2026-06-26T09:45Z): 3 eval gaps backfilled (genuine dispatch, cron journals 09:40-09:43), eval file 10,336 (profile) / ~39,600 (commons) — steady-state confirmed (confirmation #56+). Forge clean for 56+ consecutive dispatches. Dispatch ~#2145 (2026-06-27T21:45Z): 0 gap backfill, eval file 40,782 — steady-state confirmed (confirmation #57+).

**Dispatcher `new_files` empty/missing pattern:** When the dispatcher's `new_files` list is empty or contains only already-evaluated journals, the dispatch's own concurrent heartbeats captured everything. This is the expected default in steady-state.

## Second-Wave Detection (Post-Dispatch)

After a multi-skill dispatch completes, the dispatcher may re-scan and detect journals produced by the dispatch's own run as "new" (e.g., the `mentor-light-20260624T064417Z.json` written by Mentor in Phase 2). This is the **second wave** — expected and harmless if already evaluated.

**Detection pattern:** Before running Praxis mtime-based discovery, check if the dispatcher's `new_files` entries are already in `journals_evaluated.jsonl`:

```bash
# Check if a dispatcher new_file is already evaluated
grep -q "mentor-light-20260624T064417Z" /root/.hermes/profiles/indigo/commons/data/ocas-praxis/journals_evaluated.jsonl
# Exit code 0: already evaluated, skip silently (correct no-op)
# Exit code 1: not yet evaluated, proceed with ingest
```

**Fast no-op path (confirmed 2026-06-25):** When ALL dispatcher `new_files` are already in the eval file (common for same-day multi-wave dispatches), Praxis has nothing to do. Update `last_ingest_run` to now, write a no-op dispatch journal, and exit. Do NOT run mtime-based discovery, do NOT run gap backfill, do NOT re-add to eval file. This is the expected default for second-wave dispatches where concurrent heartbeats already processed the journals.

**⚠️ Dispatch prompt overrides fast-no-op (confirmed 2026-06-27T16:30Z):** The fast-no-op shortcut only applies when the dispatch is a bare second-wave re-detection without explicit pipeline instructions. **When the dispatch prompt explicitly names pipelines** (e.g., "Load ocas-forge skill and run Forge journal scan. Load ocas-mentor skill and run Mentor light heartbeat. Load ocas-praxis skill and run Praxis journal ingest"), **run all named pipelines even if the journals appear routine.** The Praxis pipeline can surface new lessons even from "routine" mentor-light journals (e.g., `outcome: success, errors: 0` but lessons extracted for recurring error patterns). Skipping the pipeline would miss these signals. **Rule:** Explicit pipeline instructions in dispatch prompt = run the full pipeline. Bare journal listing without pipeline instructions = fast-no-op if already evaluated.

**Genuine dispatch with new_entries > 0 gaps (confirmed 2026-06-27T22:18Z):** When eval gaps are found and the gap journals show `new_entries > 0` (not 0 entries / pure no-op), this is a genuine dispatch requiring full pipeline execution even if the content looks routine. The `new_entries` count indicates the cron pipeline observed something — even if it's just 1-3 entries of routine skill activity. Do NOT apply the no-op shortcut when `new_entries > 0`. Run all 3 pipelines.

**Why this happens:** The dispatcher's scan interval may fire while the dispatch is still writing journals, or immediately after. The journals are genuinely new (mtime > last dispatcher scan), but they were already processed by the dispatch's own Praxis pipeline.

**Correct behavior:** When a second-wave journal is already in the eval file, Praxis should find 0 new journals via its mtime-based discovery (because `last_ingest_run` was advanced during the first wave). This is a clean no-op. Do NOT re-ingest, do NOT run gap backfill a second time. The third-wave mitigation in step 5 prevents this from recurring.

Confirmed 2026-06-24 dispatch #40: mentor-light journal from the dispatch run was detected as "new" by a subsequent dispatcher scan, but was already in `journals_evaluated.jsonl` from the dispatch's own Praxis run. Correct no-op.

## Phantom Files in Dispatcher `new_files`

The dispatcher's file scan may capture files that are deleted or never materialize on disk by the time the dispatch runs. These appear in `details.new_files` but `os.path.exists()` returns False. **This is expected and must be handled silently.**

**Pattern:** A journal listed in `new_files` with timestamp T1 may not exist because:
- It was a placeholder written and deleted between scan and dispatch (confirmed 2026-06-24: `forge-scan-20260624T000942Z.json` listed but never existed)
- A sibling pipeline (e.g., a prior Forge cron) wrote and then replaced it
- The file was written with a different timestamp than expected (content `run_id` ≠ filename timestamp due to `$(date)` evaluating at different times in the same shell)

**Fix for all pipelines:** Before processing any file from the dispatcher's `new_files` list, check `os.path.exists(full_path)`. If missing, skip silently — do not treat as an error. Actual files on disk from the same dispatch may exist under slightly different timestamps.

**Forge specifically:** When writing the Forge scan journal, use a pre-computed static timestamp for BOTH the filename and the content `run_id` field — never call `$(date)` inside the heredoc AND in the cat command separately:

```bash
# CORRECT: compose timestamp once, use for both filename and content
TS=$(date -u +%Y%m%dT%H%M%SZ)
cat > "$DIR/forge-scan-${TS}.json" << EOF
{"run_id": "forge-scan-${TS}", "timestamp": "...", ...}
EOF

# WRONG: $(date) called twice produces different results
cat > "$DIR/forge-scan-$(date -u +%Y%m%dT%H%M%SZ).json" << EOF
{"run_id": "forge-scan-$(date -u +%Y%m%dT%H%M%SZ)", ...}
EOF
```

Confirmed 2026-06-24 dispatch #31: dispatcher listed `forge-scan-20260624T000942Z.json` but actual file was `forge-scan-20260624T001245Z.json` (filename and content timestamps mismatched by 3 minutes).

## Cross-Pipeline Timing Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Mentor updates Praxis `last_ingest_run` | Praxis finds 0 new journals | Use state's `last_ingest_run` as mtime floor (NOT dispatcher's older `latest_ts`) |
| Mentor does NOT advance Praxis `last_ingest_run` (observed 2026-07-10) | State timestamp stays at its prior value (or even BEFORE dispatcher `latest_ts`); Praxis mtime floor is older than the documented "past latest_ts" assumption | Re-read `ingest_state.json` AFTER Mentor; use its actual value as the floor. The ingest template reads state by default, so no `CAPTURED_TS` override is needed. Do NOT assume Mentor advanced it. |
| Forge journal written AFTER Praxis ingest | Dispatcher re-detects as "new" (3rd wave) | Add to eval file + advance state |
| Gap journals invisible to eval dedup | Dispatcher re-detects already-evaluated journals | Post-ingest gap backfill |
| `find -newermt` uses local time | 0 results despite files existing | Use Python mtime comparison |
| Script `active_skills_30d` undercount | Evidence shows 11 instead of 22 | Always run `correct_active_skills_30d.py` |
| Phantom file in dispatcher `new_files` | File listed but not on disk | `os.path.exists()` check before processing — skip silently |
| **Python f-string `$VAR` in terminal()** | JSON file written with literal `{ts}` in filename instead of timestamp | Shell `$VAR` expansion inside Python f-strings in `terminal()` can fail silently. **Fix:** Always use `write_file` to write scripts to `/tmp/`, then invoke with `python3 /tmp/script.py`. Never compose JSON filenames via shell heredoc with embedded Python f-string interpolation. Confirmed 2026-06-25 dispatch #88. |
| **Python f-string `$` in `python3 -c "..."`** | `python3 -c "...f'file-{TS}.json'..."` produces `SyntaxError: invalid decimal literal` when TS is a timestamp string (e.g., `20260625T134811Z`) because Python interprets the braces as f-string expression but the shell already stripped `$TS` | Never embed shell variables inside Python f-strings in `-c` oneliners. Use `write_file` to `/tmp/` and invoke separately. Confirmed 2026-06-25 dispatch #99. |
| **Cross-step timestamp mismatch** | Third-wave mitigation eval entry uses a different `datetime.now()` call than the journal-writing step → eval says `praxis-dispatch-221915Z` but actual file is `praxis-dispatch-221825Z` | Compose ALL output journal filenames in step 0. Step 2 writes files using those names. Step 3 registers those SAME names. No step calls `datetime.now()` independently. Confirmed 2026-06-27T22:18Z. |
| Dispatcher `new_files` timestamp mismatch | Dispatcher lists `mentor-light-20260624T115206Z.json` but actual file is `mentor-light-20260624T115823Z.json` | The dispatcher's file scan captures files mid-write or before final timestamp is set. Always use mtime-based discovery as the ground truth, not the dispatcher's `new_files` list. The list is a hint, not authoritative. **Post-ingest verification**: after gap backfill, `ls` the journal directory and confirm the eval file contains the ACTUAL filenames — not the dispatcher's stated filenames. |
| Path typo: `oca-praxis` vs `ocas-praxis` | Single-char typo makes eval file appear empty (0 entries) | Always verify with `ls -d .../data/oca*` before constructing paths |
| `$(date)` called multiple times in shell | Filename ≠ content timestamp | Compose timestamp once, interpolate into both |
| **Script stdout filename ≠ actual file on disk** | Third-wave mitigation adds wrong filename to eval file (script stdout says `mentor-light-T002055Z.json` but file on disk is `mentor-light-T002558Z.json` due to `$(date)` rollover between two `date` calls in the script) | After third-wave mitigation, ALWAYS `ls` the actual journal directory and use the real filename — never trust script stdout's filename claim. Verify with `grep <actual_filename> journals_evaluated.jsonl` before declaring done. Confirmed 2026-06-25 dispatch #56. |
| Journals on disk but NOT in `journals_evaluated.jsonl` | Next dispatch wave re-detects as "new" but they were already ingested | **Praxis catch-up pattern** — check for journals newer than `last_ingest_run` not in eval file, run Praxis ingest (see below) |
| **Dispatcher `new_files` incomplete** | Dispatcher lists N journals but mtime scan finds N+1 (or vice versa) | Dispatcher captures files at detection time; concurrent heartbeats can write journals before/after the scan. Always use mtime-based discovery as ground truth. Confirmed 2026-06-25 dispatch #59: dispatcher listed 4, mtime found 5. |
| **Dispatcher `new_files` timestamp mismatch** | Dispatcher says `mentor-light-20260625T020800Z.json` but actual file is `mentor-light-20260625T020902Z.json`. `grep <dispatcher_filename>` against eval file returns NOT_FOUND even though the journal IS evaluated under the actual filename. | ALWAYS use mtime-based discovery as ground truth for Praxis ingest. After finding unevaluated journals via mtime, `grep <actual_filename>` to confirm status — never grep the dispatcher's stated filename directly. The dispatcher's `new_files` is a filename hint, not a journal_id authority. Confirmed 2026-06-25 dispatch #60: dispatcher listed `praxis-dispatch-20260625T015715Z.json` as NOT_EVALUATED by naive grep, but it was at line 37990 with `action_taken: self_referential_skip`. The `new_files` timestamp was correct for that file, but 4 other journals had timestamp discrepancies that would have caused false re-ingestion without mtime-based discovery. |
| **Multiple phantom files for same skill** | Dispatcher lists 2+ files from same skill (e.g., `mentor-light-T042401Z` + `mentor-light-T043516Z`) but only one exists on disk | The dispatcher's scan interval captures the file list at T0, but a concurrent heartbeat writes a new journal and the dispatcher's next scan sees both the old and new. The "phantom" file was never actually written with that exact timestamp — it was a mid-write race. Check ALL listed files with `os.path.exists()`. If only one exists from a multi-file list for the same skill, it's the phantom pattern — evaluate the one that exists and skip the rest silently. Confirmed 2026-06-25 dispatch #69. |
| **Commons sync returns 0 delta** | `wc -l` on commons evidence/ingestion shows no growth after dispatch sync | Concurrent heartbeats may have already synced the new lines before the dispatch runs. This is EXPECTED in steady-state with multiple concurrent cron triggers. Do NOT treat as sync failure — verify with `grep <new_run_id> /root/.hermes/commons/data/mentor/evidence.jsonl` to confirm the new line exists in commons. If present, sync is already done. Confirmed 2026-06-25 dispatch #99. |
| **Praxis dispatch journal NOT auto-evaluated** | After the dispatch ingest completes, the Praxis dispatch journal (`praxis-dispatch-TS.json`) is NOT in `journals_evaluated.jsonl`. The ingest script only evaluates source journals and never adds its own output. The next dispatcher wave will re-detect it as "new" and Praxis will silently skip it (already ingested) — but it inflates `new_files` counts and wastes cycles. | After writing the Praxis dispatch journal, ALWAYS manually add it to `journals_evaluated.jsonl` with `action_taken: "dispatch_output_skip"`. This is a separate step from third-wave mitigation (which handles Mentor/Forge journals). Confirmed 2026-06-25 dispatch #70. |
| **Concurrent Praxis heartbeats create same-day eval gaps** | Gap backfill reveals 15,000+ entries, but many are Praxis dispatch journals from TODAY that were processed by concurrent heartbeats but never added to the eval file. These are not historical backlog — they are same-day concurrent evaluation gaps. | This is expected recovery behavior. Concurrent Praxis heartbeats (from different cron triggers) may each write their own dispatch journal but not coordinate eval file writes. The next dispatch wave's gap backfill catches them. After all same-day journals are backfilled, the count drops to 0. Do NOT truncate the eval file — these entries are genuine. Confirmed 2026-06-25 dispatch #96: 15,238 gap backfill entries, 31 from today's Praxis dispatch journals alone. |
- **Concurrent dispatch wave session reference conflicts (confirmed 2026-06-25 dispatch #100)**. When two dispatch waves fire in rapid succession (same cron schedule or overlapping schedules), both may attempt to write the same session reference file (`references/session-YYYYMMDD-dispatch-NNN.md`). The `write_file` tool reports a "modified by sibling subagent" warning. This is harmless for session narratives (idempotent) but could cause data loss for evidence/state files. **Mitigation**: Session reference files are append-only — if you get this warning, accept the concurrent wave's write. For evidence/state files, use atomic patterns (write to temp, rename) or `echo >>` append. |
- **Archive directory discovery (confirmed 2026-06-25 dispatch #72):** Gap backfill suddenly produces 14,000+ entries — looks like a bug but is actually the `.archive/` directory being discovered for the first time. Archive files have mtime predating `last_ingest_run` and were never in the eval file. | This is a one-time catch-up event. After archive files are backfilled, subsequent dispatches return to single-digit counts. Do NOT truncate the eval file or attempt to "fix" the backfill — these files genuinely need entries. Confirmed 2026-06-25 dispatch #72: 14,941 entries from `.archive/2026-04/`.
- **Accumulated non-archive backlog (confirmed 2026-06-25 dispatch #88):** After the archive catch-up, subsequent waves can still produce 10,000+ gap backfill entries from non-archive directories (e.g., `ocas-lucid` dream journals). This happens when `last_ingest_run` was not advanced for multiple dispatch cycles (e.g., script write failures, concurrent heartbeats racing). | This is expected recovery behavior. The eval file grows in large batches until all historical journals are caught up. Do NOT truncate or attempt to "fix" — these entries are genuine. After full catch-up, steady-state returns to 0-5 gap backfill per dispatch. Confirmed 2026-06-25 dispatch #88: 15,106 entries from `ocas-lucid/` and other directories. |
| **Forcing CAPTURED_TS when `last_ingest_run` is already past dispatcher `latest_ts`** | Praxis mtime window moves BACKWARD → re-finds already-evaluated journals → duplicate eval entries or false "new" detections | Read `ingest_state.json:last_ingest_run` FIRST. If it's already past the dispatcher's `latest_ts`, use the state timestamp as the mtime floor (the template does this by default). Do NOT set `CAPTURED_TS` to the older dispatcher timestamp. Confirmed 2026-06-25 dispatch #73. |
| **Using dispatcher `latest_ts` as CAPTURED_TS when state `last_ingest_run` is BEFORE it** | Praxis mtime window moves TOO FAR FORWARD → misses genuinely new journals written between state and dispatcher scan → under-evaluates | Use the STATE's `last_ingest_run` as the mtime floor, NOT the dispatcher's `latest_ts`. The dispatcher's timestamp is an UPPER BOUND on what it saw, not a LOWER BOUND on what exists. Journals may have been written between the state's last run and the dispatcher's scan — those are the target. If ingest finds fewer journals than dispatcher `new_files` count AND dispatcher `latest_ts` > state `last_ingest_run`, re-run with state timestamp. Confirmed 2026-06-26 dispatch (05:58Z). |
| **Commons eval file accumulates duplicate entries** | Repeated `comm -13` appends cause commons eval file to drift relative to profile. Drift goes BOTH directions: (a) commons > profile when profile was ever behind (commons entries get re-appended as "missing"), (b) profile > commons when a dispatch only updates the profile copy. Examples: 38,955 vs 38,952 (#134), 39,380 vs 39,377 (#22, 2026-06-26). `comm -13` can only grow, never shrink. | After EVERY dispatch ingest that modifies the eval file: compare line counts. If commons > profile → `cp` profile to commons (profile is authoritative). If profile > commons → `comm -13` append the delta. Never rely solely on `comm -13` — always check direction first. Confirmed 2026-06-25 #134, 2026-06-26 #22. |
| **Taste token repair + scan in separate `terminal()` calls** | OAuth library refreshes token between calls, re-adding `+00:00` suffix. Scan fails silently (0 results) or falls back to wrong account. | ALWAYS chain Taste token repair + scan in a SINGLE `terminal()` call with `&&`. Two separate calls WILL fail. Confirmed 2026-06-25 dispatches #68, #71, #73, #74 — 4 consecutive dispatches requiring repair. |
| **`execute_code` blocked in cron mode** | `execute_code` tool returns "BLOCKED: execute_code runs arbitrary local Python... Cron jobs run without a user present" | When running as a cron job, NEVER use `execute_code`. Use `terminal()` with `python3 -c "..."` or `python3 /tmp/script.py` for all Python operations. This applies to all dispatch pipelines (Forge, Mentor, Praxis, Taste). Confirmed 2026-06-25 dispatch #117. |
| **Cross-terminal-call timestamp drift (cron, no shared shell state)** | Each `terminal()` call is a fresh shell with no shared variables. A `TS=$(date ...)` composed in call N is invisible in call N+1, so journal filenames written across calls diverge from the eval-registration `journal_id` timestamps → phantom or false-gap re-detection on the next dispatch. | Externalize the composed timestamp ONCE to flat files at dispatch start (`echo "$TS" > /tmp/dispatch_ts.txt`, `echo "$NOW" > /tmp/dispatch_now.txt`), then read them in EVERY subsequent call (`TS=$(cat /tmp/dispatch_ts.txt)`). Reuse the SAME TS for the forge-scan, praxis-dispatch, and dispatch-wave journal filenames AND their eval-registration `journal_id` values so filenames and eval entries match exactly. This is the multi-call equivalent of the "compose ALL timestamps once" rule — required because you cannot run Forge/Mentor/Praxis in a single call. Validated 2026-07-10T06:10Z dispatch: all 4 output journals matched their eval entries (count=1 each, 0 phantom). |
| **Ingestion commons > Profile line count (benign)** | `wc -l` shows commons ingestion (45,098) >> profile ingestion (29,751). Initial panic: "sync failed, commons missing 15K entries." | Commons ingestion accumulates entries from concurrent heartbeats across multiple days. Profile only contains entries written by profile-scoped dispatches. Verify with `set` comparison (extract all `file` fields, check profile ⊆ commons) — if all profile entries exist in commons, sync is complete despite the line count difference. Do NOT attempt to "append the delta" — profile entries are a proper subset. Confirmed 2026-06-26 dispatch ~#24. |

## Praxis Catch-Up Pattern (Confirmed 2026-06-24)

**Problem:** After a multi-skill dispatch wave, some journals exist on disk and are in `ingestion_log.json` but are NOT in `journals_evaluated.jsonl`. This happens when a prior wave's Mentor heartbeat advanced `last_ingest_run` past the journal's mtime, but the journal was never added to the eval file.

**Detection (run after all pipelines complete):**
```python
from datetime import datetime, timezone
import json, os

state_path = '/root/.hermes/profiles/indigo/commons/data/ocas-praxis/ingest_state.json'
eval_path = '/root/.hermes/profiles/indigo/commons/data/ocas-praxis/journals_evaluated.jsonl'

with open(state_path) as f:
    state = json.load(f)
last_ingest = state['last_ingest_run']
li_dt = datetime.fromisoformat(last_ingest)
li_ts = li_dt.timestamp()

# Load evaluated journal IDs
with open(eval_path) as f:
    evaluated = f.read()

# Find unevaluated journals newer than last_ingest_run
jdirs = [
    '/root/.hermes/profiles/indigo/commons/journals/',
    '/root/.hermes/commons/journals/'
]
unevaluated = []
for jdir in jdirs:
    for root, dirs, files in os.walk(jdir):
        for fname in files:
            if not fname.endswith('.json'):
                continue
            fpath = os.path.join(root, fname)
            if os.path.getmtime(fpath) >= li_ts:
                rel = fpath.replace(jdir, '')
                if rel not in evaluated:
                    unevaluated.append((fpath, rel))
```

**Handling:** If `unevaluated` is non-empty:
1. Read each journal, check for signals
2. Write Praxis journal with events
3. Add entries to `journals_evaluated.jsonl`
4. Update `ingest_state.json:last_ingest_run` to now
5. Write Praxis evidence entry
6. This is NOT a second-wave false positive — work is genuinely done

**Distinction from one-wave lag:**
- One-wave lag: journal is newer than `last_ingest_run` → next wave's mtime scan finds it (self-correcting)
- Catch-up: journal is OLDER than `last_ingest_run` but not in eval file → mtime scan will never find it (NOT self-correcting)

**Full second-wave with catch-up:** Sometimes the dispatcher fires a second wave where all email threads are re-detections (skip silently) but there are genuinely unevaluated journals from the prior wave (process them). Handle each pipeline independently: email = no-op, journals = catch-up ingest.

## Email Triage Path (Within Multi-Skill Dispatch)

When the dispatcher includes a `"type": "new_emails"` dispatch alongside journals, handle email triage AFTER the journal pipelines (Forge → Mentor → Praxis) complete.

### Email Triage Workflow

1. **Read dispatch details** — Each account (jared, indigo) has `actionable`, `high_priority`, and `new_threads` fields.
2. **Read email state** — Check `last_email_check.json` for each account's `last_check` timestamp and `last_thread_id`.
3. **Evaluate each thread:**
   - `no-reply@` senders + order confirmations → **no action** (transactional)
   - `intent: "informational"` → **no action** (newsletters, notifications, marketing)
   - `intent: "dev_notification"` → **no action** (product updates, API notices)
   - `intent: "pr_review"` on Indigo's account → **no action** (code fix tasks are Koda's domain, not dispatch communication — confirmed 2026-06-25 dispatch #69)
   - `intent: "response_needed"` from market research/survey follow-ups → **no action** (low-priority survey requests, even if `response_needed` — confirmed 2026-06-25 dispatch #96: Dialectica survey follow-up correctly classified as no_action)
   - `intent: "security_alert"` (GitGuardian, secret detection) on internal repos → **no action unless active production secrets** (test credentials/JWTs in test repos are noise — confirmed 2026-06-25 dispatch #99)
   - `intent: "personal"` where snippet shows our reply → **no action** (already handled)
   - `intent: "personal"` from real human, no reply visible → **read full thread** to check for existing reply before escalating
   - `intent: "action_required"` from real human → **read full thread** — if Jared's question was already answered by the sender, no reply needed (confirmed 2026-06-25 dispatch #108: Emily Zhang's "shipped via DHL" response to Jared's "has it shipped yet?" was correctly classified as no_action despite `intent: action_required`). Only escalate if Jared's question remains unanswered.
4. **Read thread content for "personal" emails before acting** — The dispatch's snippet only shows the incoming message. Jared may have already replied. Confirmed 2026-06-25 dispatch #58: 475HOA fire alarm was flagged `intent: personal, priority: 55` but Jared had already replied "Thanks for the update Pedro!" — thread was complete, no escalation needed.
4. **Update state** — Write back to `last_email_check.json` with updated timestamps, `action_taken: "no_action"`, and zeroed counters.
5. **Do NOT escalate to Jared** unless a thread genuinely requires his personal input (commitment decisions, time-sensitive human correspondence). Transactional receipts, newsletters, and self-sent briefings never need escalation.

**Key rule:** Jared does NOT want email briefings. Handle autonomously. Only escalate if personal input is required.

**Mixed dispatch pattern:** When both `new_journals` and `new_emails` appear in the same dispatch, journals always run first (the 3-pipeline sequence). Email triage runs last and is independent — it does not produce journals or update Praxis state.

## Verification Checklist (End of Dispatch)

- [ ] Forge: journal written (no-op or processed)
- [ ] Mentor: evidence grew by ≥1, ingestion grew by ≥N, journal exists
- [ ] Mentor: `active_skills_30d` corrected (two evidence lines)
- [ ] Mentor: commons synced (evidence, ingestion, OKR, anomalies, decisions)
- [ ] Praxis: eval entries added for all new journals
- [ ] Praxis: Praxis dispatch journal added to eval file (script does NOT auto-add it)
- [ ] Praxis: third-wave mitigation applied
- [ ] Praxis: gap backfill run
- [ ] Praxis: stale ingest script cleaned up
- [ ] Taste: signals extracted, journal written (if `taste_new_data` dispatch present)
- [ ] Taste: token was repaired before scan (if scan ran)
- [ ] Taste: journal filename matches actual file on disk (verify via `ls`, not script stdout)
- [ ] All dispatch-output journals in eval file (with CORRECT filenames — verify via `ls` the journal directory, never trust script stdout)
- [ ] Dispatcher `new_files` cross-checked against mtime scan (list is a hint, not authoritative — missing journals found via mtime are NOT errors)
- [ ] After Praxis ingest: actual journal filenames `grep`'d against eval file (not dispatcher's stated filenames — they may differ due to `$(date)` rollover)

## Anti-Journalization Checkpoint

After completing all pipelines, you will feel an urge to write "proper" journals for each pipeline. **RESIST for Mentor** — the script's journal is canonical. Additional context goes in the evidence record, not a separate journal file. Forge and Praxis write their own journals via their respective commands.

## Session Log

| Dispatch | Date | Files | Mentor Correction | Praxis Events | Notes |
|----------|------|-------|-------------------|---------------|-------|
| #28 | 2026-06-23 | 2 | 11→22 | 0 | Anti-journalization checkpoint fired |
| #29 | 2026-06-23 | 2 | 11→22 | 0 | Cron-ingest journal from dispatch detected |
| #30 | 2026-06-23 | 2 | 11→22 | 0 | 4 mtime-discovered + 2 dispatcher, 5 gap backfill |
| #31 | 2026-06-24 | 2 | 11→22 | 0 | Phantom file pattern (forge-scan listed but never existed), third-wave mitigation |
| #34 | 2026-06-24 | 2 | 11→22 | 0 | Forge clean, 8 gap backfill, all pipelines clean |
| #38 | 2026-06-24 | 1 | 11→22 | 0 | All 3 pipelines clean, 14386 gap backfill, no errors |
| #39 | 2026-06-24 | 3 | 11→22 | 0 | All 3 pipelines clean, 14396 gap backfill, no errors |
| #41 | 2026-06-24 | 3 | 11→22 | 0 | All 3 pipelines clean, 3 gap backfill, no errors |
| #43 | 2026-06-24 | 3 | 11→22 | 0 | All 3 pipelines clean, 14438 gap backfill, third-wave mitigated |
| #44 | 2026-06-24 | 1 | 10→22 | 4 | All 3 pipelines clean, 14446 gap backfill, third-wave mitigated (7 journals) |
| #48 | 2026-06-24 | 2 | n/a (already corrected) | 2 | **Praxis catch-up**: 3 journals on disk but not in eval file (mentor-light + praxis-ingest + dispatch-no-op). Email: second-wave re-detection. |
| #49 | 2026-06-24 | 3 | n/a | 0 | Email: all action:none (fresh scan, 7 threads). Journals: all already ingested by concurrent heartbeat (one-wave lag). Taste: 1 signal (Lavash/DoorDash). Clean sweep + already-ingested pattern. |
| #485 | 2026-06-24 | 3 | 9→22 | 0 | Mixed outcome. Email: all informational/self-sent, 0 actionable (second-wave of #483 30s prior). Mentor: 1171 files, 2 ingested, correction 9→22. Praxis: 10 journals processed (3 dispatch + 7 from concurrent pipelines), all routine/healthy, 0 events. Third-wave mitigation applied. |
| #486 | 2026-06-24 | 1 | 9→22 | 0 | Token repair required (both accounts, timezone suffix). Forge: 0 unprocessed. Mentor: 1153 files, 4 ingested, correction 9→22. Praxis: 1 journal evaluated. Taste: 1 signal (Lavash/DoorDash). Email: all informational, 0 high-priority. All pipelines clean. |
| #56 | 2026-06-25 | 3 | 9→22 | 0 | All 3 pipelines clean. 33 gap backfill. Third-wave mitigation applied. **Filename mismatch pitfall**: script stdout reported `mentor-light-20260625T002055Z.json` but actual file was `mentor-light-20260625T002558Z.json` (post-write rename/`$(date)` rollover). Eval file got wrong filename — had to fix manually after verification caught it. |
| #57 | 2026-06-25 | 2 | 9→22 | 0 | Mixed dispatch (journals + email). Forge: 0 unprocessed. Mentor: 992 files, 2 ingested, correction 9→22. Praxis: 4 journals ingested, 0 events, 4 gap backfill. Email: jared 1 thread (DoorDash confirmation, no action), indigo 7 threads (all informational/already replied, no action). All pipelines clean. |
| #58 | 2026-06-25 | 1 | 9→22 | 0 | Mixed dispatch (journals + email). Forge: 0 unprocessed. Mentor: 998 files, 2 ingested, correction 9→22. Praxis: 6 journals evaluated, 1 gap backfill, 0 events. Email: jared 4 threads (all no-action — 475HOA fire alarm already replied by Jared), indigo 7 threads (all informational/self-sent). **Key learning:** Always read thread content before escalating "personal" intent — Jared had already replied "Thanks for the update Pedro!" to 475HOA.** |
| #59 | 2026-06-25 | 3 | 9→22 | 0 | Routine multi-skill dispatch. Forge: 0 unprocessed. Mentor: 1006 files scanned, 3 ingested, correction 9→22. Praxis: 5 journals evaluated (4 dispatcher + 1 concurrent heartbeat), 14,772 gap backfill, 0 events. **Dispatcher `new_files` is a hint, not authoritative** — mentor-light-T015059Z was already evaluated by concurrent heartbeat but absent from dispatcher list; mtime scan found it as the 5th unevaluated journal. Gap backfill size confirms accumulated dispatch-output journals from prior waves. |
| #60 | 2026-06-25 | 5 | 9→22 | 0 | Multi-skill + Taste dispatch. Forge: 0 unprocessed. Mentor: 1010 files, 2 ingested, correction 9→22. Taste: 2 signals (Next Level VG + Lavash, both DoorDash). Token repair required (both accounts, timezone suffix). Praxis: 5 unevaluated journals found via mtime (all dispatch-output from this wave), 2 gap backfill, 0 events. **Key pitfall**: naive `grep <dispatcher_filename>` returned false negative for `praxis-dispatch-20260625T015715Z.json` (was at eval line 37990), and mentor-light had `$(date)` rollover (dispatcher said T020800Z, actual T020902Z). Mtime-based discovery + grep on actual filenames is mandatory. |
| #61 | 2026-06-25 | 2 | 9→22 | 0 | Routine multi-skill dispatch. Forge: 0 unprocessed. Mentor: 1016 files, 3 ingested, correction 9→22. Praxis: 3 journals ingested (all dispatch-output), 0 gap backfill (eval file fully caught up after #59's 14,772-entry catch-up), 0 events. **Dispatcher `new_files` already evaluated** — both listed files were in eval file from concurrent heartbeat. Mtime-based discovery found the dispatch's own output journals instead. Confirmation #29+ of the already-evaluated pattern. |
| #64 | 2026-06-25 | 2 | 9→22 | 0 | Routine multi-skill dispatch. Commons > Profile sync verification (8891 vs 4878 = expected). |
| #65 | 2026-06-25 | 3 | 9→22 | 0 | Multi-skill + Taste + Email. Token repair race condition. Praxis directory filter excludes cross-skill journals (6 manual eval bridge). "Personal" intent ≠ escalation (read full thread). |
| #68 | 2026-06-25 | 3 | 9→22 | 0 | Multi-skill + Taste dispatch. Forge: 0 unprocessed. Mentor: 1055 files, 2 ingested, correction 9→22. Praxis: 4 journals evaluated (mtime), 2 gap backfill, 0 events. Taste: 2 signals (Next Level VG + Lavash). Token repair mandatory (timezone suffix). |
| #67 | 2026-06-25 | 2 | 9→22 | 0 | Mixed: email (2 no-action) + multi-skill journals (6 evaluated, 0 events). Eval file fully caught up (0 gap backfill). |
| #69 | 2026-06-25 | 3 | 9→22 | 0 | Routine multi-skill. All 3 pipelines clean. Phantom file pattern (dispatcher listed `mentor-light-T042401Z` and `T043516Z` but only former exists). 1 gap backfill (concurrent Praxis cron). Eval file at 38,075 entries — fully caught up. **PR review classification fix**: GitHub PR review emails on Indigo's account classified as `action:none` (Koda's domain, not dispatch communication). |
| #70 | 2026-06-25 | 1 | 9→22 | 0 | Routine multi-skill. Dispatcher listed `mentor-light-T043956Z` (already evaluated by concurrent heartbeat) but actual file was `T044606Z` (required Praxis ingest). 5 mtime-discovered journals, 1 gap backfill. **Praxis dispatch journal must be manually added to eval file** — the ingest script does not auto-add its own output journal. |
| #71 | 2026-06-25 | 4 | 9→22 | 0 | Multi-skill + Taste. Token repair required (both accounts, timezone suffix). Taste: 2 DoorDash signals (Next Level VG + Lavash). Praxis eval file fully caught up (0 gap backfill). All 4 pipelines clean. |
| #72 | 2026-06-25 | 5 | 9→22 | 0 | Multi-skill dispatch. Forge: 0 unprocessed. Mentor: 1133 files, 2 ingested, correction 9→22. Praxis: 4 journals evaluated, 0 events, **14,941 gap backfill** (archive directory `.archive/2026-04/` discovered for first time — 14,000+ historical files). All pipelines clean. |
| #73 | 2026-06-25 | 5 | 9→22 | 0 | Multi-skill + Taste. `last_ingest_run` already advanced past dispatcher `latest_ts` by Mentor script — use state timestamp as mtime floor, NOT CAPTURED_TS. 3 Praxis journals evaluated, 1 gap backfill. Taste: 2 DoorDash signals. All 4 pipelines clean. |
| #74 | 2026-06-25 | 4 | 9→22 | 0 | Multi-skill + Taste. All 4 dispatcher `new_files` already in eval file (second-wave pattern). Fast no-op for Praxis. Mentor: 1145 files, 3 ingested, correction 9→22. Taste: 2 DoorDash signals (Next Level VG + Lavash). Third-wave mitigation applied for forge-scan. |
| #76 | 2026-06-25 | 5 | 9→22 | 0 | Multi-skill clean sweep. Eval file fully caught up (0 gap backfill, 38,127 entries). All dispatcher `new_files` already evaluated by concurrent heartbeats. Mtime found 5 new journals from this dispatch's own run. Steady-state confirmed. |
| #77 | 2026-06-25 | 4 | 9→22 | 0 | Multi-skill + Taste dispatch. Forge: 0 unprocessed. Mentor: 1153 files, 1 ingested, correction 9→22. Praxis: 2 new journals, 0 events, third-wave mitigation for mentor-light. Taste: 2 signals (Next Level VG + Lavash, both DoorDash). Token repair mandatory (timezone suffix). All 4 pipelines clean. |
| #79 | 2026-06-25 | 6 | 1→22 | 4 | Multi-skill clean sweep (steady-state). Forge: 0 unprocessed. Mentor: 974 files, 1 ingested, correction 1→22. Praxis: 6 journals (1 new mtime + 5 concurrent), 4 events (all no_signal), 0 gap backfill. All dispatcher `new_files` already evaluated by concurrent heartbeats. |
| #81 | 2026-06-25 | 3 | 9→22 | 0 | Multi-skill steady-state. Phantom file pattern: 2 dispatcher-listed mentor-light files never materialized. Forge: 0 unprocessed. Mentor: 1173 files, 3 ingested, correction 9→22 (confirmation #34+). Praxis: 5 journals evaluated, 0 events, 0 gap backfill (eval file 38,151). |
| #83 | 2026-06-25 | 7 | 9→22 | 2 | Multi-skill clean sweep. Email: third-wave skip (all is_new=false, second_wave_no_op within 2h). Forge: 0 unprocessed. Mentor: 1163 files, 1 ingested, correction 9→22. Praxis: 2 journals ingested (2 no_signal events), 5 third-wave bridges (incl. praxis-dispatch-*.json in ocas-praxis/ dir NOT auto-ingested). **Key learning:** `praxis-dispatch-*.json` lives in `ocas-praxis/` but is NOT auto-ingested by Praxis script — filename filter only picks up `cron-ingest-*.json`. Manual eval file bridge required. |
| #82 | 2026-06-25 | 2 | 9→22 | 0 | Mixed (journals + email). Steady-state. Forge: 0 unprocessed. Mentor: 1165 files, 4 ingested, correction 9→22 (confirmation #35+). Praxis: 2 mtime-found (mentor-light already evaluated + praxis-cron), 0 events, 0 gap backfill (eval 38,557). Email: 9 threads, 0 escalations. GitGuardian internal alerts = no action (test JWTs). |
| #88 | 2026-06-25 | 2 | 9→22 | 0 | Multi-skill + email. **Forge filename bug:** Python `$TS` in terminal() heredoc produced literal `{ts}` in filename. Fixed by rename. Mentor: 1214 files, 59 ingested, correction 9→22 (#36+). Praxis: 5 journals, 0 events, 15,106 gap backfill (accumulated non-archive backlog). Email: 0 escalations. ARGGER resolved after 47 days. |
| #95 | 2026-06-25 | 4 | 9→22 | 0 | Multi-skill + email. Steady-state. Forge: 0 unprocessed. Mentor: 1206 files, 2 ingested, correction 9→22 (confirmation #35+). Praxis: 0 new journals, 0 gap backfill. All dispatcher `new_files` already evaluated. Email: 10 threads, 0 escalations. PR #12 approved. PR #13 one blocker remaining (double HTML escaping). |
| #96 | 2026-06-25 | 2 | 9→22 | 0 | Multi-skill + email. Forge: 0 unprocessed. Mentor: 1207 files, 2 ingested, correction 9→22 (confirmation #37+). Praxis: 5 journals evaluated (mtime), 0 events, **15,238 gap backfill** (accumulated same-day concurrent heartbeat eval gaps, including 31 Praxis dispatch journals from today). Email: jared 7 threads (all no-action), indigo 3 threads (all no-action). **Survey follow-up (Dialectica) classified as no_action despite `intent: response_needed`.** |
| #97 | 2026-06-25 | 1 | 9→22 | 0 | Multi-skill + email. Forge: 0 unprocessed. Mentor: 1209 files, 3 ingested, correction 9→22 (confirmation #38+). Praxis: 2 journals evaluated, 0 events, **15,190 gap backfill** (post-catch-up backlog clearance — residual dispatch-output journals from prior waves). Email: 10 threads, 0 escalations. **Gap backfill pattern:** 3rd consecutive >15K backfill = backlog clearance after archive (#72) + non-archive (#88) catch-ups. |
| #98 | 2026-06-25 | 3 | 9→22 | 1 | Multi-skill + email. Forge: 0 unprocessed. Mentor: 1208 files, 3 ingested, correction 9→22 (confirmation #39+). Praxis: 2 journals, 1 event, third-wave mitigation for forge-scan + concurrent journals. Email: jared 0 actionable (all from_me=True), indigo 0 actionable (PR #12 approved, PR #13 fix pushed). **GitHub API pitfall:** review ID from `pulls/reviews` ≠ comment ID for `pulls/comments/{id}/replies` (404). **Triage auth issue:** `triage.py --account indigo` uses Jared's auth. |
| #99 | 2026-06-25 | 3 | 9→22 | 2 | Multi-skill + email. Forge: 0 unprocessed. Mentor: 1204 files, 1 ingested, correction 9→22 (confirmation #35+). Praxis: 3 journals evaluated, 2 events (no_signal), third-wave mitigation for dispatch-output journals. Email: jared 11 actionable (0 escalations — ARGGER shipment resolved, all informational), indigo 5 actionable (0 escalations — PR #12 approved, GitGuardian internal secrets = no action). **GitGuardian pattern:** Internal secret alerts on `indigokarasu/indigo` repo (JWT + high entropy) are test credentials, not active production secrets. No escalation needed unless they are active production keys. **Commons sync "already in sync":** Concurrent heartbeats may sync evidence/ingestion before the dispatch runs, producing 0 delta on dispatch sync. This is expected — do NOT treat as sync failure. |
| #100 | 2026-06-25 | 2 | 9→22 | 0 | Multi-skill + email. Forge: 0 unprocessed. Mentor: 1203 files, 1 ingested, correction 9→22 (confirmation #41+). Praxis: fast no-op (all dispatcher `new_files` already evaluated, 0 mtime-discovered). Email: jared 11 actionable (0 escalations — ARGGER panel shipped/DHL, GLG already declined, Bywater COC obligation fulfilled), indigo 5 actionable (0 escalations — PR reviews are Koda's domain). **Concurrent dispatch wave file conflict:** `write_file` reported sibling subagent modified the session reference file — harmless for idempotent session narratives. |
| #102 | 2026-06-25 | 4 | 9→22 | 0 | Multi-skill + email. Forge: 0 unprocessed. Mentor: 1214 files, 2 ingested, correction 9→22 (confirmation #42+). Praxis: 4 journals evaluated, 0 events, **15,255 gap backfill** (4th consecutive >15K — extended post-catch-up clearance). Email: jared 16 actionable (0 escalations — ARGGER shipment confirmed, all informational), indigo 5 actionable (0 escalations — PR reviews Koda's domain, GitGuardian test noise). |
| #106 | 2026-06-25 | 4 | 9→22 | 0 | Multi-skill + email. Forge: 0 unprocessed. Mentor: 1216 files, 2 ingested, correction 9→22 (confirmation #43+). Praxis: 5 journals evaluated (mtime), 0 events, 1 gap backfill (eval file 38,773 — nearly caught up after archive discovery). Email: jared 10 threads (0 escalations — ARGGER shipment resolved/DHL, all no-action), indigo 5 threads (0 escalations — PR reviews Koda's domain, GitGuardian test noise). All second-wave email (is_new=false except OpenTable). |
| #108 | 2026-06-25 | 3 | 9→22 | 0 | Multi-skill + email. Forge: 0 unprocessed. Mentor: 1218 files, 2 ingested, correction 9→22 (confirmation #44+). Praxis: 9 journals evaluated (mtime), 0 events, **0 gap backfill** (eval file 38,792 — fully caught up). Email: jared 17 actionable/4 high-priority (0 escalations — ARGGER shipped/DHL confirmed, thread complete), indigo 4 actionable/2 high-priority (0 escalations — PR reviews Koda's domain). **Intent classification:** `action_required` label ≠ escalation when thread question is already answered by sender. |
| #114 | 2026-06-25 | 4 | 9→22 | 3 | Multi-skill + email. Forge: 0 unprocessed. Mentor: 1265 files, 1 ingested, correction 9→22. Praxis: 3 journals ingested (routine mentor-light), 0 lessons, 9/12 shifts. Email: jared 7 (3 new informational threads, 0 escalations), indigo 4 (0 escalations). **Dual-file eval sync:** Praxis script only updated profile eval; commons eval required manual sync. **Per-thread is_new shortcut:** dispatch had mixed is_new=true (3 threads) and is_new=false (8 threads) — shortcut only applies per-thread, not per-dispatch. |
| #117 | 2026-06-25 | 1 | 9→22 | 0 | Multi-skill + email. Forge: 0 unprocessed. Mentor: 1284 files, 1 ingested, correction 9→22. Praxis: 7 journals evaluated (mtime), 0 events, 2 gap backfill. Email: jared 4 (0 escalations — survey follow-ups, GLG declined, Amazon shipment), indigo 4 (0 escalations — PR reviews Koda's domain, Wikipedia code, Newspapers.com marketing). **Cron-mode tool restriction:** `execute_code` is blocked in cron jobs — use `terminal()` for all Python operations. |
| #128 | 2026-06-25 | 5 | 9→22 | 0 | Multi-skill + Taste + email. Steady-state. Forge: 0 unprocessed. Mentor: 1458 files, 118 ingested, correction 9→22. Praxis: all dispatcher `new_files` already evaluated, 0 gap backfill (eval file 38,913). Taste: 1 signal (Next Level VG / DoorDash). Token repair mandatory (both accounts, timezone suffix). Email: jared 6 (0 escalations), indigo 3 (0 escalations — PR reviews Koda's domain, GitGuardian test noise). **Confirmation #45+ of steady-state pattern.** |
| #134 | 2026-06-25 | 6 | 9→22 | 0 | Multi-skill + email. Steady-state. Forge: 0 unprocessed. Mentor: 1508 files, 2 ingested, correction 9→22. Praxis: 6 journals evaluated (mtime), 0 events, **0 gap backfill** (eval file 38,953). Email: jared 2 (0 escalations — both already handled), indigo 2 (0 escalations — PR reviews Koda's domain). All second-wave email (is_new=false). **Commons eval sync drift:** commons had 38,955 entries vs profile's 38,952 — `comm -13` had accumulated duplicates over prior dispatches. Fixed by `cp` profile→commons. **Confirmation #46+ of steady-state pattern.** |
| #95 | 2026-06-26T01:05Z | 3 | 9→22 | 0 | Multi-skill + email. All 3 dispatcher-listed journals already evaluated. 1 genuinely new mentor journal detected via directory scan (`mentor-light-20260626T011109Z.json`, concurrent pipeline write). Mentor heartbeat: 1 new file ingested, correction 9→22. Cross-skill mitigation: 2 ocas-mentor journals added to eval file. Email: third-wave skip (all is_new=false). **All-evaluated plus one new pattern** — dispatch new_files can be all done while concurrent pipeline writes real work alongside them. |
| ~#22 | 2026-06-26T02:45Z | 2 | 9→22 | 0 | Multi-skill steady-state. Forge: 0 unprocessed (confirmation #50+). Mentor: 1673 files, 3 ingested, correction 9→22. Praxis: 5 mtime-discovered journals (0 events), 2 gap backfill. **Commons eval drift (other direction):** commons=39,380 > profile=39,377 — `cp` profile→commons fixed it. Eval file: 39,374 entries. Confirmation #47+ of steady-state pattern. |
| 2026-06-29T11:38Z | 2026-06-29T11:38Z | 3 | 8→22 | 0 | Genuine full pipeline. 2 genuine eval gaps (dispatch-wave + praxis-cron) + 1 already-evaluated mentor-light. Path typo `oras-praxis`→`ocas-praxis`. Pipe-to-python bash quoting failure. Cross-terminal timestamp divergence. Praxis: 4 journals, 0 events, 6 eval entries. Eval file: 48,469. Steady-state #60+. |
| 2026-06-29T12:08Z | 2026-06-29T12:08Z | 5 | 8→22 | 0 | Second-wave re-detection with explicit pipeline instructions. All 5 new_files already in praxis eval. Mtime-discovery found 4 gaps (concurrent cron + dispatch output). Praxis: 3 journals, 0 events, 3 third-wave. Gap backfill: 0. Eval file: 48,485. Steady-state #62+. |
| 28 | 2026-06-26T03:37Z | 2 | n/a (cron mode) | 0 | Multi-skill + email. Forge: 0 unprocessed (confirmation #51+). Mentor: 6 new journals ingested (cron mode, manual scan). Praxis: 6 journals evaluated (0 events), proactive third-wave mitigation applied. Email: 6 threads (0 actionable, 0 escalations). DoorDash false positive confirmed via Gmail API fetch. Eval file: 39,408 entries. Confirmation #48+ of steady-state pattern. |
| ~#24 | 2026-06-26T04:12Z | 5 | 9→22 | 0 | Multi-skill + email. Forge: 0 unprocessed (confirmation #52+). Mentor: 1721 files, 2 ingested, correction 9→22. Praxis: 6 journals evaluated (mtime), 0 events, 1 gap backfill, 2 third-wave mitigation. Email: jared 2 (0 escalations — already replied + GLG auto-response), indigo 1 (0 escalations — Wikipedia AFC acceptance). Eval file: 39,432 entries. Confirmation #49+ of steady-state pattern. |
| ~#25 | 2026-06-26T04:15Z | 3 | 9→22 | 0 | Multi-skill + email. Forge: 0 unprocessed (confirmation #53+). Mentor: 1726 files, 2 ingested, correction 9→22. Praxis: 3 journals evaluated (mtime), 0 events, **0 gap backfill**. Email: jared 2 (0 escalations — already replied + GLG auto-response), indigo 1 (0 escalations — Wikipedia AFC acceptance informational). Eval file: 39,436 entries. Confirmation #50+ of steady-state pattern. |
| ~#26 | 2026-06-26T05:58Z | 5 | 9→22 | 0 | Multi-skill + email. Forge: 0 unprocessed (confirmation #54+). Mentor: 1770 files, 3 ingested, correction 9→22. Praxis: 5 journals evaluated (mtime), 0 events, 11 gap backfill. **CAPTURED_TS pitfall**: using dispatcher `latest_ts` (05:52) as floor missed 4 of 5 journals; re-ran with state `last_ingest_run` (05:49) to find all. Email: 3 threads (all second-wave, 0 escalations). Eval file: 39,482 entries. |
| #147 | 2026-06-26T07:45Z | 4 | n/a (cron mode) | 0 | Multi-skill second-wave. All 4 dispatcher new_files already in eval file (prior wave's output). Fast no-op for all 3 pipelines. Third-wave mitigation applied (3 journals). Eval file: 39,567 entries. Confirmation #55+ of steady-state pattern. |
| #158 | 2026-06-26T09:45Z | 3 | n/a (cron mode) | 0 | Genuine dispatch. 3 cron-written journals (09:40-09:43) not in eval → full pipeline execution. All 3 pipelines clean. 3 eval gaps backfilled + 3 third-wave mitigation entries. Eval file: 10,336 entries (profile). Confirmation #56+ of steady-state pattern. |
| ~#37 | 2026-06-27T16:30Z | 1 | 1→22 | 2 | **Genuinely-new-but-routine journal** with explicit pipeline instructions. Dispatch prompt named all 3 pipelines → full execution despite routine journal. Mentor: 1397 files, 1 ingested, correction 1→22. Praxis: 2 journals, 2 lessons (calendar_conflict n=9, coverage_gap n=10). **Key learning:** Explicit dispatch prompt overrides fast-no-op shortcut — running pipeline surfaced lessons from routine journal. |
| ~#2145 | 2026-06-27T21:45Z | 2 | 7→22 | 0 | Full pipeline execution, 0 gaps. Forge: 0 unprocessed. Mentor: 2173 files, 2 ingested, correction 7→22. Praxis: 7 journals evaluated, 0 events. **Key finding:** Praxis ingest script auto-registers dispatch-wave journals from prior waves (action_taken: no_signal_noise). Pipeline guide's "NEVER register dispatch-wave" rule applies to MANUAL registration, not ingest script auto-evaluation. Counter drift: journals_evaluated_count needs final `wc -l` sync. Eval file: 40,782 entries, steady-state confirmed. |
| ~#2218 | 2026-06-27T22:18Z | 2 | 7→22 | 0 | Genuine full pipeline. 2 eval gaps (mentor-light-220725Z before-ingest + mentor-light-221059Z post-ingest), both new_entries > 0. Cross-step timestamp mismatch: praxis-dispatch journal written at 22:18:25 but eval entry composed at 22:19:15 → caught by verification. Eval file: 40,812 entries. |
| 2026-07-10T04:55Z | 2026-07-10T04:55Z | 4 | 5→25 | 0 | Second-wave re-detection with explicit pipeline instructions (dispatcher `new_files` were prior-wave output journals: dispatch-wave, forge-scan, praxis-dispatch, mentor-light). Forge: 0 unprocessed → no_op. Mentor: 493 files scanned, 4 ingested, 0 events, correction 5→25 (OCAS 18). Praxis: 3 journals ingested (all no_signal), 0 events, **0 gap backfill** — dry-run walk found 0 unevaluated journals (eval fully caught up). Email: 1 informational thread (Roller shade) → action:none. **Key finding: Mentor did NOT advance praxis `ingest_state.json:last_ingest_run`** (remained `04:48:47` after a `05:16` heartbeat) — divergence from the documented "Mentor advances it past `latest_ts`" coupling. Re-read state after Mentor and use its actual value as the mtime floor; the ingest template already does this by default. Steady-state confirmed, eval 49,694. |
| 2026-07-10T06:10Z | 2026-07-10T06:10Z | 4 | 5→25 | 0 | Explicit-pipeline-instruction dispatch. `new_files` was a prior-wave dispatch-wave artifact (06:05:04 < detected_at 06:10:46) → skipped eval per prior-wave rule, but ran all 3 pipelines per explicit override. Forge: 0 unprocessed (all 11 `vp_*.json` already in `processed/`). Mentor: 12 ingested, 0 errors, correction 5→25 (OCAS 18). Praxis: 6 no-signal journals (concurrent cron 05:34–06:14), gap backfill 2, 0 events. **Re-confirmed**: Mentor did NOT advance `ingest_state.json:last_ingest_run` (stayed `05:34:33` after 06:14 heartbeat) — 2nd same-day confirmation of the divergence from the documented "Mentor advances it past `latest_ts`" coupling. Email: 1 thread (Roller shade) second-wave `is_new=false` → `action:none`. Eval file 49,706. Steady-state confirmed. Timestamps externalized to `/tmp/dispatch_ts.txt` across terminal calls → all 4 output journals matched eval (count=1 each, 0 phantom). |
| 2026-07-15T12:00Z | 2026-07-15T12:00Z | 2 | 14→23 | 0 | Multi-skill + email steady-state. Forge: 0 unprocessed (all `vp_*.json` in `processed/`). Mentor: 2016 files scanned, 12 ingested, 0 errors, correction 14→23 (OCAS 16). Praxis: dispatcher `new_file` (`mentor-light-20260715T114544Z.json`) already bridged at 11:46Z via automated `bridge_eval_both_stores` (`action_taken: post-dispatch-cleanup`) → fast no-op; gap backfill 2 (forge-scan + mentor-light, both no_signal), 0 template ingest, 14 Bug-2 noise lessons cleared (`--new-genuine-events 0`). **Re-confirmed**: Mentor did NOT advance `ingest_state.json:last_ingest_run` (stayed `11:36:15` after 12:01 heartbeat) — 3rd+ confirmation of the divergence. Email: jared 7 threads all `action:none` (self-reply to Kyra, GitHub/hermes-agent #55445 dev-notification, 5 expert-network solicitations, completed Apr shade thread); 0 drafts/sends/escalations. Eval file 292,293. Steady-state confirmed. |
| 2026-07-15T12:35Z | 2026-07-15T12:35Z | 2 | 14→23 | 0 | Multi-skill + email steady-state. Forge: 0 unprocessed (all 11 `vp_*.json` in `proposals/` also present in `processed/`). Mentor: 2054 files scanned, 20 ingested, 0 errors, correction 14→23 (OCAS 16). Praxis: dispatcher `new_file` (`mentor-light-20260715T123111Z.json`) already bridged in both eval stores via automated `bridge_eval_both_stores` (`action_taken: post-dispatch-cleanup`) → fast no-op; gap backfill 4 (3 mentor-light heartbeats from concurrent cron + forge-scan, all no_signal), 0 template ingest, 14 Bug-2 noise lessons cleared (`--new-genuine-events 0`). **Re-confirmed**: Mentor did NOT advance `ingest_state.json:last_ingest_run` (stayed `12:40:20` after 12:46 heartbeat) — 4th+ confirmation of the divergence. Email: jared 7 threads pure second-wave re-detection (all `is_new=false`, all `action:none`); 0 drafts/sends/escalations. Eval file 292,312. Steady-state confirmed. |
