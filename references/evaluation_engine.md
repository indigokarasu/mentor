# Mentor Evaluation Engine

## Journal Ingestion
Read newly written journals from all skills at `{agent_root}/commons/journals/` (recursive scan). Validate schema per spec-ocas-journal.md v1.3. Quarantine malformed entries. Track ingested run_ids in `{agent_root}/commons/data/ocas-mentor/ingestion_log.jsonl`.

Mentor and Elephas are parallel consumers of the same journal files. Neither blocks the other. Mentor evaluates for performance; Elephas ingests for knowledge.

### Journal File Layout
- Files are `.json` (NOT `.jsonl`), one file per run, organized in date subdirectories
- Example path: `ocas-lucid/2026-05-28/lucid-dream-20260528-173415.json`
- Each file contains either a single JSON object or a JSON array of objects
- Always use `os.walk()` recursively; do NOT glob for `*.jsonl`
- Handle both `list` and `dict` top-level types when parsing

### execute_code Sandbox Constraint
Temp files written in `/tmp/` during an `execute_code` call are **not** available in subsequent calls. For multi-stage heartbeat processing:
- Write intermediate state to a persistent path under `{agent_root}/commons/data/ocas-mentor/tmp/`, OR
- Complete all file read/write within a single `execute_code` invocation

## OKR Scoring
Score universal OKRs plus skill-specific OKRs. Evaluate over rolling windows.

### Key OKRs
- **completion_rate**: fraction of runs that succeeded (target >=0.95)
- **error_rate**: fraction of runs with explicit errors (target <=0.05)
- **escalation_rate**: fraction of runs with escalations (target <=0.10)
- **evaluation_coverage**: active-skills-with-journals / total-active-skills (informational, not pass/fail). Active = produced a journal in last 30 days. Do NOT use total-installed-skills as denominator.

### Scoring Notes
- ~90% of journals lack explicit `outcome` fields; default absent outcomes to "success" when no `error` key is present
- `outcome`/`status` can be str OR dict — always `isinstance()` check before comparing
- `duration_ms` vs `duration_seconds` naming varies; normalize values < 100 as seconds
- Skills may use non-standard outcome values (e.g., `done`, `ok`, `no_action_needed` instead of `success`) — treat these as success when scoring

## Champion/Challenger Pairing
Pair runs with same comparison_group_id. Require identical normalized_input_hash. Verify challenger did not execute side effects. Compare universal OKRs, skill-specific OKRs, latency, retries, reliability.

## Aggregate Evaluation
Build evaluation dataset over multiple runs. Do not promote on single-run basis except emergency rollback.
