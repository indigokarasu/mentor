---
name: ocas-mentor
description: >
  Mentor: self-improving orchestration and evaluation engine. Manages long-running
  multi-skill workflows, analyzes journals from all skills, evaluates champion vs
  challenger variants, and proposes skill improvements to Forge. Use when managing
  multi-step projects, running heartbeats, evaluating skill performance, or coordinating
  multi-skill workflows. Trigger phrases: "manage this project", "coordinate a
  multi-step analysis", "evaluate skill performance", "run a heartbeat", "how are
  skills performing", "update mentor". Do not use for web research (use Sift),
  skill building (use Forge), user communication (use Dispatch), real-time skill
  execution, content generation, system health monitoring (use Custodian), or
  skill evaluation scoring.
license: MIT
source: https://github.com/indigokarasu/mentor
includes:
- references/**
- scripts/**
metadata:
  author: Indigo Karasu (indigokarasu)
  version: 2.8.0
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
- `mentor.update` — pull latest from GitHub source; preserves journals and data
- `mentor.plan.list` / `mentor.plan.run` / `mentor.plan.status` / `mentor.plan.resume` / `mentor.plan.history` — workflow plan management

## Mode A — Runtime Orchestration

Triggered by explicit invocation. Creates a project record, builds a task graph, executes and supervises tasks, dynamically replans when blocked.

Task states: pending, ready, running, blocked, failed, complete, archived.

Scheduling: execute only tasks with complete dependencies. Prioritize critical path. Bounded parallelism. Bounded retries.

## Mode B — Heartbeat Evolution

Triggered periodically. Pipeline: ingest journals → validate schema → aggregate metrics → pair champion/challenger → score OKRs → detect anomalies → evaluate variants → generate proposals → emit decisions → write journal.

Mentor reads journals from all skills at: `{agent_root}/commons/journals/` (recursive scan). Tracks ingested run_ids via `ingestion_log.jsonl`.

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

## Cran-Mode Constraint

**Cron-mode constraint:** `execute_code` is blocked in cron-triggered jobs. All heartbeat, update, and plan runs triggered by cron must use `terminal()` with inline `python3 << 'PYEOF'` heredocs for multi-stage logic.

## Background Tasks

| Job | Schedule | Command |
|-----|----------|---------|
| `mentor:deep` | `0 5 * * *` | `mentor.heartbeat.deep` |
| `mentor:light` | `*/5 * * * *` | `mentor.heartbeat.light` |
| `mentor:update` | `0 0 * * *` | `mentor.update` |

## Storage Layout and Configuration

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

## Recovery Behavior

Implements the recovery contract from `spec-ocas-recovery.md`.

- **Evidence**: Every run writes an evidence record, including no-op runs. `not_activity_reason` mandatory.
- **Gap detection**: If gap exceeds 15min (light) or 24h (deep), logs `gap_detected`.
- **Degraded mode**: When Fellow or Forge unavailable, logs `degraded: <dependency>`.
- **Log compaction**: 30 days (no-op) / 90 days (error/gap). Last 7 days retained.

## Self-Update

See `references/self-update-mentor.md`.

## Gotchas — Critical

See `references/gotchas-mentor.md` for the full gotcha catalog.

Key gotchas:

- **`outcome`/`status` can be str or dict** — Always check `isinstance()` before comparing
- **Most journals (80-90%) lack explicit `outcome` fields** — Default absent outcomes to `success` when no `error` key present
- **`duration_ms` vs `duration_seconds` naming varies** — Normalize: values < 100 are likely seconds
- **`run_id` can be empty string** — Use file path as fallback identifier
- **Proposal stall loop** — If ≥3 consecutive proposals target same skill+issue without Fellow evaluation, escalate instead of re-proposing
- **Anomaly staleness** — Mark anomalies unchanged for ≥5 consecutive heartbeats as `stale: true`
- **`execute_code` is blocked in cron mode** — Use `terminal()` with heredoc for all heartbeat processing
- **Cron-mode config merge** — Existing `config.json` may lack fields; merge defaults on init
- **Safe timestamp parsing** — Always use a centralized `parse_dt()` helper; never call `datetime.fromisoformat()` inline

## Safe Timestamp Parsing

```python
def parse_dt(ts_str):
    """Parse any OCAS journal timestamp → tz-aware datetime or None."""
    if ts_str is None:
        return None
    s = str(ts_str).strip()
    if not s or s in ("0", "null", "None"):
        return None
    try:
        if isinstance(ts_str, (int, float)):
            ts = float(ts_str)
            return datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts, tz=timezone.utc)
        dt = datetime.fromisoformat(s.replace("Z", "+00:00").replace("z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError, OSError):
        return None
```

## Cron-Mode Script Structure

When writing multi-step heartbeat scripts, define ALL helpers at the top before `main`:

```python
# Helpers first
def parse_dt(ts_str): ...
def normalize_duration(raw_ms): ...

# Then init, then main logic
if __name__ == "__main__":
    main()
```

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
| `references/heartbeat-gap-debugging.md` | When evidence log shows gaps >2h |
| `references/okrs-mentor.md` | During OKR evaluation |
| `references/self-update-mentor.md` | Before running `mentor.update` |
| `scripts/cron-heartbeat-deep.py` | Reference implementation for deep heartbeat journal ingestion — use when building or debugging heartbeat scripts; contains `load_journal_entries()` (multi-format parser) and `normalize_outcome()` helpers |
