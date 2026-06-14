---
name: ocas-mentor
description: 'Self-improving orchestration and evaluation engine. Manages long-running multi-skill workflows, analyzes journals from all skills, evaluates champion vs challenger variants, and proposes skill improvements to Forge. Use for multi-step project management, heartbeat runs, skill performance evaluation, or multi-skill coordination. Do not use for web research (use Sift), skill building (use Forge), user communication (use Dispatch), real-time skill execution, content generation, system health monitoring (use Custodian), or skill evaluation scoring.'
license: MIT
source: https://github.com/indigokarasu/mentor
includes:
- references/**
- scripts/**
metadata:
  author: Indigo Karasu (indigokarasu)
  version: 2.8.20
tags:
- orchestration
- evaluation
- multi-skill
- OCAS-core
triggers:
- self-improving orchestration
- multi-skill workflow
- skill evaluation engine
- mentor orchestration
---

# Mentor

Mentor is the system's control plane — in runtime mode it decomposes goals into task graphs, supervises execution across skills, and dynamically repairs failures through layered escalation. In heartbeat mode it reads journals from every skill, scores OKR performance against baselines, and generates improvement proposals that flow to Forge and Fellow.

Mentor and Elephas are parallel journal consumers: Mentor reads journals to evaluate skill performance, Elephas reads them to extract entity knowledge into Chronicle.

## When to Use

- OKR evaluation across all OCAS skills
- Skill performance scoring and improvement recommendations
- Post-major-session learning synthesis
- Skill library health assessment
- When Critique identifies issues needing Mentor follow-up

## When NOT to Use

- Real-time skill execution or task routing
- Content generation or research
- System health monitoring (use Custodian)
- Skill building (use Forge)

## Responsibility Boundary

Mentor owns orchestration, evaluation, and the improvement loop.

Mentor does not own: skill building (Forge), behavioral pattern detection (Corvus), behavioral refinement (Praxis), knowledge graph (Elephas), web research (Sift), communications (Dispatch), experimentation execution (Fellow).

## Ontology Types

- **Concept/Event** — projects, tasks, skill performance evaluations, OKR cycles
- **Concept/Idea** — improvement proposals, behavioral patterns
- **Thing/DigitalArtifact** — project state records, task graphs, evaluation reports

Mentor does not emit Signals to Elephas directly. Elephas consumes Mentor journals for reference.

## Commands

- `mentor.project.create` — create a project with goal, constraints, and requested output
- `mentor.project.status` — current project state, task graph, execution progress
- `mentor.project.replan` — trigger strategy-level replan
- `mentor.task.list` — tasks with statuses, dependencies, blocking reasons
- `mentor.heartbeat.light` — lightweight pass: ingest journals, update aggregates, queue work
- `mentor.heartbeat.deep` — deep pass: full scoring, trend analysis, proposals
- `mentor.variants.list` — active champion/challenger pairs with evaluation status
- `mentor.variants.decide` — emit promotion decision for a variant
- `mentor.proposals.list` — pending skill improvement proposals
- `mentor.proposals.create` — generate a VariantProposal for a target skill
- `mentor.status` — active projects, pending evaluations, self-improvement metrics
- `mentor.journal` — write journal for the current run; called at end of every run
- `mentor.update` — pull latest from GitHub source; preserves journals and data. See `references/self-update-mentor.md` for the full procedure (Quick Path for clean state, Full Path for dirty state with local fixes to preserve).
- `mentor.plan.list` / `mentor.plan.run` / `mentor.plan.status` / `mentor.plan.resume` / `mentor.plan.history` — workflow plan management

## Mode A — Runtime Orchestration

Triggered by explicit invocation. Creates a project record, builds a task graph, executes and supervises tasks, dynamically replans when blocked.

Task states: pending, ready, running, blocked, failed, complete, archived.

Scheduling: execute only tasks with complete dependencies. Prioritize critical path. Bounded parallelism. Bounded retries.

## Mode B — Heartbeat Evolution

Triggered periodically. Pipeline: ingest journals → validate schema → aggregate metrics → pair champion/challenger → score OKRs → detect anomalies → evaluate variants → generate proposals → emit decisions → write journal.

Mentor reads journals from all skills at: `{agent_root}/commons/journals/` (recursive scan). **NOTE:** The deep heartbeat script (`cron-heartbeat-deep.py`) currently only scans `/root/.hermes/commons/journals/` and misses profile-scoped journals under `/root/.hermes/profiles/indigo/commons/journals/`. The light heartbeat handles this via dual-path `find`. See gotcha #32. Tracks ingested run_ids via `ingestion_log.jsonl`.

## Layered Evaluation Loops

- **Layer 1 — Micro Action** (ms-sec): validate single outputs. Retry, local repair, fallback.
- **Layer 2 — Task Execution** (sec-min): ensure task completion. Retry, switch skill, split task.
- **Layer 3 — Strategy** (min-hr): improve active project plan. Reorder, insert, merge, parallelize.
- **Layer 4 — Evolution** (hr-wk): improve skills and policies. Propose variants, promote/archive.

## Failure Repair Policy

Order: retry with refined framing → alternate skill → split task → revise ordering → escalate to strategy loop. Never retry indefinitely.

## Safety Invariants

- Challenger variants never execute side effects
- Comparisons only on identical normalized inputs
- Malformed journals quarantined, not trusted
- Promotion requires sufficient evidence over multiple runs
- Mentor journals its own orchestration decisions

## Inter-skill Interfaces

**Mentor → Fellow:** Writes ExperimentRequest files, then invokes `fellow.experiment.run`.

**Fellow → Mentor:** Fellow writes CycleResult files; Mentor reads and tracks consumed `cycle_ids`.

**Mentor → Forge:** Writes VariantProposal and VariantDecision files via journal payload.

See `spec-ocas-interfaces.md` for schemas and handoff contracts.

## Run Completion

After every Mentor command (orchestration or heartbeat):

1. Read CycleResult files. Track consumed `cycle_id` values in `fellow_results_ingested.jsonl`.
2. Persist project state, evaluation results, or proposals
3. For experiment requests: write ExperimentRequest file, invoke `fellow.experiment.run`
4. For variant proposals: write VariantProposal file
5. For variant decisions: write VariantDecision file
6. Log material decisions to `decisions.jsonl`
7. Write journal via `mentor.journal`

## Cron-Mode Constraints

**`execute_code` is blocked in cron-triggered jobs.** All heartbeat, update, and plan runs triggered by cron must use `terminal()` with inline `python3 << 'PYEOF'` heredocs for multi-stage logic.

**Sandbox file discovery failure:** In the cron sandbox, Python's `subprocess.run(["find", ...])` and `os.walk()` silently return 0 results even when the filesystem is fully accessible via shell tools. Use the shell-pipe pattern: `find JOURNALS_DIR -name "*.json" -mtime -3 | python3 scripts/cron-heartbeat-light.py`. See `references/shell-write-pattern.md`.

**Python `with open()` writes are UNRELIABLE in cron `terminal()`** — Sometimes they persist, sometimes they silently fail. Piped `find | python3` is most likely to fail; `python3 /path/to/script.py` (no pipe) has been observed to succeed. Treat all Python writes as best-effort: verify with `wc -l` after, and use shell-level `echo >>` / `cat >` for critical evidence/journal writes. See `references/shell-write-pattern.md`.

**Heredoc vs. pipe conflict:** `cat file | python3 << 'PYEOF'` does NOT deliver stdin to Python — the heredoc steals stdin. Write the script to `/tmp/` first, then pipe: `cat file | python3 /tmp/script.py`. See gotcha #33.

**Env var on piped command:** `VAR=value cat file | python3 script` only sets the var for `cat`, not `python3`. Must `export` first — but even `export` in the same `terminal()` block may not propagate if the tool splits commands into subshells. **Safest:** `cat file | VAR=value python3 script`. See `references/gotchas-mentor-cron-envvars.md`.

**Light heartbeat self-journaling is INTERMITENT in cron mode** — The `cron-heartbeat-light.py` script writes its own evidence and ingestion records via Python `with open()`, but these writes are intermittent. As of 2026-06-14, a run succeeded on all 3 files simultaneously (evidence +1, ingestion +4, journal written) — the first full-success run after 8+ consecutive partial-failure runs. The pattern is shifting from "reliably fails" to "intermittent." The caller's backup write workflow is NOT a fallback — it is the ACTUAL persistence mechanism. Always run the full verify-and-backup workflow. Never skip verification even when prior runs succeeded. See `references/shell-write-pattern.md` and gotcha #23.

# CRITICAL: Use `python3 << 'PYEOF'` heredoc for backup writes, NOT shell `printf` with variable interpolation — Shell variable expansion inside heredocs can introduce stray braces (e.g., `${DATA_DIR}}`) that silently break paths. The safe pattern for writing evidence/ingestion backups is a Python heredoc with hardcoded paths (no shell variable interpolation):
```bash
python3 << 'PYEOF'
import json, os
from datetime import timezone, datetime
# ... write to /tmp/, validate with os.path.getsize(), then open(..., 'a') ...
PYEOF
```
NEVER use `printf '%s\\n' "${SOME_VAR}" >> path` where `path` contains shell variables — the `}` in `${VAR}` can double up and produce paths like `file.jsonl}`. If you must use shell interpolation, use `$VAR` without braces.

**CRITICAL: Journal directory date must use UTC** — Use `date -u +%Y-%m-%d` for `JOURNAL_DIR`, NOT `date +%Y-%m-%d` (which uses local time). The `run_id` is UTC-based, so the directory must be too. A mismatch puts the journal in yesterday's directory and creates confusion during cross-reference.

- ~~**Script journal filename missing `mentor-light-` prefix**~~ **FIXED 2026-06-08**: Script line 264 changed to use `f"mentor-light-{run_id}.json"`. Filename now matches the `run_id` field. Confirmed working as of 2026-06-08T22:46Z. `run_id = now.strftime("%Y%m%dT%H%M%SZ")` (just the timestamp), then line 264 writes to `f"{run_id}.json"` producing e.g. `20260607T045155Z.json`. But the journal's `run_id` *field* (line 249) is `f"mentor-light-{run_id}"` = `mentor-light-20260607T045155Z`. The filename doesn't match the `run_id` inside the file. Fix: change line 264 to `f"mentor-light-{run_id}.json"` or compose `run_id` with the prefix from the start. See run 2026-06-07T04:51Z for confirmation.

**Partial success is possible (confirmed 2026-06-06T21:34Z and 2026-06-07T03:38Z):** Evidence and ingestion writes can succeed while the journal write fails in the same run — or vice versa. The three writes are independent. The verify-and-backup workflow must check ALL THREE files (`evidence.jsonl`, `ingestion_log.jsonl`, and the journal directory) independently. Do NOT assume that because evidence grew, the journal was also written.

**MANDATORY verify-and-backup workflow after every light heartbeat (SINGLE terminal() call):**
```bash
# ALL steps MUST be in ONE terminal() call — shell variables don't persist across calls.
# See gotcha #49.

# 1. Record pre-run counts
EVIDENCE_BEFORE=$(wc -l < /root/.hermes/commons/data/mentor/evidence.jsonl)
INGESTION_BEFORE=$(wc -l < /root/.hermes/commons/data/mentor/ingestion_log.jsonl)
JOURNAL_DIR="/root/.hermes/profiles/indigo/commons/journals/ocas-mentor/$(date -u +%Y-%m-%d)"

# 2. Run the script
cat /tmp/mentor_files_3d.txt | python3 scripts/cron-heartbeat-light.py

# 3. Verify ALL THREE files independently (partial success is possible)
EVIDENCE_AFTER=$(wc -l < /root/.hermes/commons/data/mentor/evidence.jsonl)
INGESTION_AFTER=$(wc -l < /root/.hermes/commons/data/mentor/ingestion_log.jsonl)
RECENT_JOURNAL=$(find "$JOURNAL_DIR" -name "mentor-light-*.json" -mmin -5 2>/dev/null | head -1)

# 4. If evidence didn't grow, write backup via shell
if [ "$EVIDENCE_AFTER" -eq "$EVIDENCE_BEFORE" ]; then
    printf '%s\\n' '{...evidence json...}' >> /root/.hermes/commons/data/mentor/evidence.jsonl
fi

# 5. If ingestion didn't grow, write backup ingestion records via shell
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
```

**Light heartbeat caller MUST correct `active_skills_30d` AND write a complete evidence record** — The script receives only `-mtime -3` files via stdin, so its `active_skills_30d` count (e.g., 15) is NOT the true 30-day active skill count (e.g., 35). **The script does NOT read the `MENTOR_ACTIVE_SKILLS_30D` env var** — that var is only for the caller's reference. The caller must compute the true count separately via a dual-path 30-day `find` (see `references/dual-path-journal-discovery.md`) and write a corrected evidence record with the true value. The script's evidence record will undercount unless overridden by the caller's backup evidence. Additionally, the script's evidence record may have `run_id: null` and lack an `outcome` field (see gotcha #58). The caller's backup evidence record is NOT a duplicate — it is a correction. Two evidence lines per heartbeat is the expected pattern. See gotcha #29 and #58.

**Recommended skill counting technique (confirmed 2026-06-14):** Use `grep -oP` to extract unique skill names from journal file paths — avoids all edge cases of `awk -F/` on absolute paths (see gotcha #44a):
```bash
# OCAS-only count (fastest, most reliable)
ACTIVE_OCAS_30D=$(find /root/.hermes/commons/journals/ /root/.hermes/profiles/indigo/commons/journals/ -name "*.json" -mtime -30 2>/dev/null | grep -oP 'ocas-[a-z]+' | sort -u | wc -l)

# All skills count (OCAS + non-OCAS)
ACTIVE_ALL_30D=$(find /root/.hermes/commons/journals/ /root/.hermes/profiles/indigo/commons/journals/ -name "*.json" -mtime -30 2>/dev/null | grep -oP 'commons/journals/([a-z][a-z0-9_-]+)' | sed 's|commons/journals/||' | sort -u | wc -l)
```

**`active_anomalies` counting fixed in v2.8.10** — The light heartbeat script now uses `a.get("timestamp") or a.get("detected_at")` to correctly read anomalies regardless of which date field they use. Prior to v2.8.10, `active_anomalies` always reported 0 due to the field mismatch (gotcha #36).

**Light heartbeat caller MUST cross-reference ingestion counts** — The script's `new_files_ingested` is an upper bound. Pipe truncation (gotcha #26) and path normalization mismatches (gotcha #24) mean the script can report N while the true new-file count differs. After every heartbeat, cross-reference: `find ... -mtime -3 | sort -u` minus paths in `ingestion_log.jsonl`. If counts differ, note the discrepancy in the evidence record. Re-ingestions are harmless (idempotent).

**Evidence record uses FLAT schema — no `metrics` wrapper** — The `cron-heartbeat-light.py` script writes evidence as a flat JSON object with top-level keys (`timestamp`, `heartbeat_type`, `total_files_scanned`, `new_files_ingested`, `errors`, `active_skills_30d`, `evaluation_coverage`, etc.). There is NO nested `metrics` dict. When writing backup evidence or correcting fields, use the flat schema. Accessing `record['metrics']['active_skills_30d']` will raise `KeyError`. Correct path: `record['active_skills_30d']`. Fixed 2026-06-09.

**Deep heartbeat is self-journaling:** `scripts/cron-heartbeat-deep.py` writes its own journal entry. The caller must NOT append a separate journal entry for the same `run_id` — this produces duplicates.

**Deep heartbeat dual-path wrapper (2026-06-13):** Use `scripts/cron-heartbeat-deep-dualpath.py` instead of the stock `cron-heartbeat-deep.py`. The stock script only scans commons journals (168 files) while the dual-path wrapper scans both commons + profile-scoped journals (6,781 files). See `references/deep-heartbeat-dual-path.md` for the full fix details, metrics comparison, and usage instructions.

**Heredoc journal file naming:** `cat > "$JOURNAL_DIR/${RUN_ID}.json" << 'EOF'` may create a file literally named `.json`. Compose the filename in a separate variable first, then reference without braces. Always `ls` the output to verify.

## Background Tasks

| Job | Schedule | Command |
|-----|----------|---------|
| `mentor:deep` | `0 5 * * *` | `mentor.heartbeat.deep` |
| `mentor:light` | `*/5 * * * *` | `mentor.heartbeat.light` |
| `mentor:update` | `0 0 * * *` | `mentor.update` |

## Storage and Configuration

See `references/schemas.md` for storage layout and data schemas.

See `references/default-config.md` for default config.json.

See `references/workflow_plans.md` for available workflow plan templates.

## Journal Outputs

Action Journal — every orchestration run, heartbeat pass, variant evaluation, and proposal emission. Include `entities_observed`, `relationships_observed`, `preferences_observed` with `user_relevance` field.

## Initialization

On first invocation, run `mentor.init`:

1. Create data directories and subdirectories
2. Write default `config.json` if absent
3. Create empty JSONL files
4. Create journal directory
5. Copy bundled plans to `plans/` directory
6. Register cron jobs if not already present
7. Log initialization as DecisionRecord

## OKRs

See `references/okrs-mentor.md` for full OKR definitions and targets.

Key OKRs: `orchestration_success_rate` (≥0.95), `evaluation_coverage` (≥0.90), `promotion_accuracy` (≥0.80).

**`orchestration_success_rate` scoring:** Computed as `(success + unknown) / total` — journals without explicit outcome fields (tagged `unknown`) are counted as successes since they have no `error` key. This corrects the prior measurement artifact where `unknown` was excluded from the numerator. See gotcha #34.

## Recovery Behavior

Implements the recovery contract from `spec-ocas-recovery.md`.

- **Evidence**: Every run writes an evidence record, including no-op runs. `not_activity_reason` mandatory.
- **Gap detection**: If gap exceeds 15min (light) or 24h (deep), logs `gap_detected`.
- **Degraded mode**: When Fellow or Forge unavailable, logs `degraded: <dependency>`.
- **Log compaction**: 30 days (no-op) / 90 days (error/gap). Last 7 days retained.

## Self-Update

See `references/self-update-mentor.md`.

## Gotchas — Critical

See `references/gotchas-mentor.md` for the full gotcha catalog (50+ entries).

See `references/gotchas-mentor-cron-envvars.md` for env var propagation gotchas specific to cron `terminal()` piped commands.

Key gotchas:

- **`outcome`/`status` can be str or dict** — Always check `isinstance()` before comparing
- **Most journals (80-90%) lack explicit `outcome` fields** — Default absent outcomes to `success` when no `error` key present
- **`duration_ms` vs `duration_seconds` naming varies** — Normalize: values < 100 are likely seconds
- **`run_id` can be empty string** — Use file path as fallback identifier
- **Proposal stall loop** — If ≥3 consecutive proposals target same skill+issue without Fellow evaluation, escalate instead of re-proposing
- **Anomaly staleness** — Mark anomalies unchanged for ≥5 consecutive heartbeats as `stale: true`
- **`MENTOR_DATA` path must be `commons/data/mentor/`, NOT `commons/data/ocas-mentor/`** — Legacy alias causes evidence to be written to a separate location
- **Coverage denominator** — `evaluation_coverage` must be `skills_with_new / active_skills_30d`, NOT `active_skills_30d / total_skill_dirs`
- **`orchestration_success_rate` measurement artifact** — A FAIL with error_rate=0.0 means outcome normalization gaps, not real failures. Extend `normalize_outcome()` success-value set.
- **Safe timestamp parsing** — Always use the centralized `parse_dt()` helper; never call `datetime.fromisoformat()` inline.
- **`JOURNALS_DIR` path must match `find` output** — Must be `/root/.hermes/commons/journals`, NOT the profile-scoped path.
- **Pretty-printed JSON state files break `tail -1`** — Always parse via `json.load(open('file'))` — never `tail -1`.
- **`find -exec sh -c` with complex quoting silently fails** — Write scan logic to `/tmp/script.py` instead.
- **Script stdin pipe can drop files** — Cross-reference `new_files_ingested` count against manual `find` minus ingestion_log. See gotcha #26.
- **Script self-journaling can silently fail** — Always `wc -l` evidence.jsonl after the script exits; write backup via shell if count unchanged. See gotcha #27.
- **Script-reported new-files count is an upper bound** — Path normalization mismatches between script dedup and ingestion log can cause harmless re-ingestions. Cross-reference for ground truth. See gotcha #28.
- **`cp -n` silently skips profile-to-commons sync** — `cp -n` does not overwrite existing files, so when the heartbeat script writes to profile (making it newer than commons), the sync silently skips. Use line-level Python set-difference for JSONL files (diff commons paths vs profile lines, append only new lines) and `cp -f` for non-JSONL state files. Confirmed 2026-06-14.
- **Deep heartbeat f-string syntax** — Nested f-strings with escaped quotes cause `SyntaxError`. Extract to separate variable first. See gotcha #33.
- **`orchestration_success_rate` OKR now counts `unknown` as success** — Fixed 2026-06-06: scoring changed from `success/total` to `(success+unknown)/total` to match `normalize_outcome()` semantics. See gotcha #34.
- **`bc -l` float output breaks JSON** — `bc -l` produces `.0285` (no leading zero), invalid when embedded in JSON strings. Always use Python `round()` for float-to-JSON. See gotcha #39.
- **Ingestion log path format mismatch** — Log stores both relative and absolute paths. Naive `comm` shows 800+ false "new" files. Extract+normalize via Python before dedup. See gotcha #42.
- **Backup journal double-prefix** — If RUN_ID already contains `mentor-light-`, filename is `"$RUN_ID.json"` not `"mentor-light-${RUN_ID}.json"`. See gotcha #43.

## Support File Map

| File | When to read |
|------|-------------|
| `references/schemas.md` | Before creating projects, tasks, proposals, or decisions |
| `references/default-config.md` | During `mentor.init` |
| `references/orchestration_engine.md` | Before goal decomposition or failure repair |
| `references/evaluation_engine.md` | Before journal ingestion or OKR scoring |
| `references/evolution_engine.md` | Before improvement detection or proposal generation |
| `references/workflow_plans.md` | Before any mentor.plan.* command |
| `references/gotchas-mentor.md` | Before any heartbeat or orchestration run |
| `references/gotchas-mentor-cron-envvars.md` | **READ BEFORE EVERY CRON HEARTBEAT** — env var propagation gotchas for piped Python in cron |
| `references/heartbeat-gap-debugging.md` | When evidence log shows gaps >2h |
| `references/okrs-mentor.md` | During OKR evaluation |
| `references/self-update-mentor.md` | Before running `mentor.update` |
| `references/evidence-log-maintenance.md` | When evidence.jsonl grows corrupt entries or heartbeat crashes on gap detection |
| `references/data-paths.md` | Before writing any heartbeat or data script — canonical vs legacy paths |
| `references/dual-path-journal-discovery.md` | **READ BEFORE EVERY CRON HEARTBEAT** — journals live in two locations |
| `references/shell-write-pattern.md` | **READ BEFORE EVERY CRON HEARTBEAT** — the only reliable write method in cron |
| `references/timestamp-parsing.md` | When parsing journal timestamps or debugging date-related errors |
| `references/heredoc-journal-naming.md` | When writing journal files via heredoc to avoid filename collisions |
| `references/okrs.md` | During OKR evaluation (legacy OKR definitions) |
| `references/heartbeat-scan-technique.md` | When debugging journal scan or discovery issues |
| `references/deep-heartbeat-dual-path.md` | **READ BEFORE EVERY DEEP HEARTBEAT** — dual-path wrapper fixes gotcha #32 |
| `references/session-2026-06-14-light.md` | Session-specific: light heartbeat corrections, commons sync fix, journal write pattern |
| `scripts/cron-heartbeat-light.py` | Reference implementation for light heartbeat in cron mode |
| `scripts/cron-heartbeat-deep.py` | Original deep heartbeat (single-path, commons only — use dualpath instead) |
| `scripts/cron-heartbeat-deep-dualpath.py` | **Preferred** deep heartbeat with dual-path scan + profile data sync |
