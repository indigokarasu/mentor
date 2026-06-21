# Multi-Skill Dispatch Pattern

## Problem

When `dispatcher.py` detects new journal files, it dispatches a single work item that triggers multiple OCAS skill pipelines in sequence. The canonical dispatch is **Forge → Mentor → Praxis**, each running independently and writing its own journal.

## Trigger

`dispatcher.py` outputs `{"has_work": true, "dispatches": [...]}` with a dispatch item of type `new_journals`. The dispatch details include:
- `new_files`: list of newly detected journal file paths
- `latest_mtime`, `latest_ts`, `count`

## Pipeline Sequence

Each pipeline runs independently. No cross-pipeline dependencies block execution. Each writes its own journal at the end.

### 1. Forge Journal Scan

**Purpose:** Check for unprocessed VariantProposal (`vp_*.json`) and VariantDecision (`vd_*.json`) files.

**Steps:**
1. Cross-reference files in `{agent_root}/commons/data/ocas-forge/proposals/` against `{agent_root}/commons/data/ocas-forge/intake/processed/`
2. Also check data root level for any `vp_*.json` / `vd_*.json` not in processed
3. If unprocessed files found: process variants, apply fixes, or queue for Mentor evaluation
4. If clean: write no-op journal with `result: "no_op"`

**Output:** `forge-scan-{timestamp}.json` journal in `{agent_root}/commons/journals/ocas-forge/`

### 2. Mentor Light Heartbeat

**Purpose:** Scan all skill journals for new entries, ingest, compute metrics.

**Steps:**
1. Build dual-path 3-day file list:
   ```bash
   find /root/.hermes/commons/journals/ /root/.hermes/profiles/indigo/commons/journals/ \
       -name "*.json" -mtime -3 | sort -u > /tmp/mentor_files_3d.txt
   ```
2. Record pre-run `wc -l` on evidence.jsonl and ingestion_log.jsonl
3. Run: `cat /tmp/mentor_files_3d.txt | python3 {skill_dir}/scripts/cron-heartbeat-light.py`
4. Verify all three writes independently (evidence delta, ingestion delta, recent journal)
5. **Mandatory correction:** Compute true `active_skills_30d` via dual-path 30-day scan and write corrected evidence record (see `shell-write-pattern.md` § Active Skills Counting)

**Output:** `mentor-light-{timestamp}.json` journal in `{agent_root}/commons/journals/ocas-mentor/{date}/`

### 3. Praxis Journal Ingest

**Purpose:** Scan skill journals for behavioral signals, extract events/lessons/shifts.

**Steps:**
1. Determine unevaluated journals (using mtime-based discovery as workaround for broken dedup)
2. For each unevaluated journal, apply signal extraction with noise filters:
   - **Mentor-light success filter:** if `outcome in ("success", "", None)` and no failure indicators (`gap_detected: true`, `metrics.errors > 0`), skip entirely
   - **Mentor-light gap_detected filter:** if `gap_detected: true` with `outcome: "success"`, skip (cron cadence, not real failure)
   - **Mentor-light low_coverage filter:** skip (measurement artifact, not behavioral signal)
   - **Mentor-light failure_keyword filter:** if outcome is success and no explicit failure indicators, skip ALL generic signal extraction (summary text false positives)
3. Record events to `events.jsonl` with dedup by `(source_journal, signal_type)`
4. Write evidence record and update ingest state

**Output:** `praxis-ingest-{timestamp}.json` journal in `{agent_root}/commons/journals/ocas-praxis/`

## Verification

After all three pipelines complete:
- Each skill directory in `{agent_root}/commons/journals/` should have a new journal entry
- No errors in any pipeline
- All JSONL files have grown by expected deltas

## Pitfalls

- **Do not block on cross-pipeline dependencies.** Each pipeline is independent. If Forge fails, Mentor and Praxis still run.
- **Each pipeline writes its own journal.** The dispatcher does NOT write a summary journal — each skill is responsible for its own.
- **The active_skills_30d correction is NOT optional.** The script's stdin-based count (3-day, single-path) is always wrong. The caller MUST compute the true dual-path 30-day count and write a corrected evidence record. This has been confirmed 12+ times (gotcha #29).
- **Praxis ingest of mentor-light journals will usually produce 0 events.** All 3 dispatch runs in this session produced 0 events because the journals were routine success. This is expected — the noise filters prevent false positives.

## Example Output

```
Dispatch Report — 2026-06-21T04:37Z

| Pipeline | Result | Details |
|----------|--------|---------|
| Forge    | ✅ Clean | 28 proposals all processed |
| Mentor   | ✅ Success | 1,603 files, 2 ingested, active_skills_30d 13→21 |
| Praxis   | ✅ Clean | 3 journals ingested, 0 events |
```
