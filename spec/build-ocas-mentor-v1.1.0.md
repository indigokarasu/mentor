# build.ocas.mentor.v1.1.0.md

## Build Target

Build a complete OpenClaw skill named `ocas-mentor`.

This is a **single skill** with **internal modularization**, not multiple skills.

Mentor has two invocation modes:

1. **Runtime orchestration mode**
   - Triggered when invoked directly by a user or another skill for a complex or long-running task.
   - Acts like a project manager, workflow orchestrator, and repair loop.

2. **Heartbeat evolution mode**
   - Triggered periodically by the host runtime / heartbeat.
   - Analyzes journals, evaluates champion vs challenger runs, proposes skill improvements, and emits build proposals for Forge.

Mentor must be designed so these two modes share state, telemetry, and learning, but do not behave the same way.

---

---

## Responsibility Boundary

Mentor observes system behavior and architecture.

Mentor proposes system optimization, architectural improvements, and skill redesign.

User behavior analysis, environment signals, and research pattern detection belong to Corvus.

Mentor never analyzes user activity patterns or preference signals directly.

---

## High-Level Purpose

Mentor is the control plane for long-running autonomous work.

It must:

- decompose complex goals into task graphs
- schedule and supervise execution across skills
- detect and repair failures
- continuously evaluate its own orchestration quality
- analyze telemetry from all skills
- compare champion vs challenger skill variants
- generate structured skill-improvement proposals for Forge
- improve both the ecosystem and its own orchestration behavior over time

Mentor must **not** perform irreversible real-world side effects itself.

---

## OpenClaw Skill Requirements

Generate a valid `SKILL.md` with YAML frontmatter.

Use this frontmatter:

```yaml
---
name: ocas-mentor
description: Self-improving orchestration and evaluation skill for long-running multi-skill workflows
metadata:
  author: Indigo Karasu
  version: "1.1.0"
compatibility:
  environment: openclaw
---
```

Do **not** include custom frontmatter fields that OpenClaw does not use.

---

## Core Design Constraint

Mentor is **one skill** because it must learn from the exact orchestration process it is running.

Do **not** split runtime orchestration and background evolution into separate skills.

Implement these as internal subsystems inside one skill.

---

## Internal Subsystems

Mentor must contain these internal subsystems:

### 1. Orchestration Subsystem

Purpose:
Manage active long-running tasks.

Responsibilities:
- goal intake
- goal decomposition
- task graph generation
- dependency management
- task scheduling
- skill selection
- progress tracking
- retry / repair / escalation
- runtime journal writing

### 2. Evaluation Subsystem

Purpose:
Turn journals into scored evidence.

Responsibilities:
- journal ingestion
- journal schema validation
- journal aggregation
- universal OKR scoring
- skill-specific OKR scoring
- champion / challenger pairing
- comparison scoring
- anomaly detection

### 3. Evolution Subsystem

Purpose:
Improve skills and Mentor itself.

Responsibilities:
- detect improvement opportunities
- generate skill variant proposals for Forge
- evaluate active variants over rolling windows
- emit promote / continue / archive decisions
- generate proposals for improving Mentor’s own runtime heuristics

---

## Operational Modes

### Mode A — Runtime Orchestration Mode

Triggered by explicit invocation.

Examples:
- "Investigate this organization"
- "Manage this long research project"
- "Coordinate a multi-step trading analysis"

Behavior:
- create a project record
- build an initial task graph
- execute and supervise tasks
- dynamically replan when blocked
- record telemetry continuously

Runtime artifacts:
- `project_state.json`
- `task_graph.json`
- `execution_state.json`
- mentor journal entries

### Mode B — Heartbeat Evolution Mode

Triggered by periodic background execution.

Behavior:
- scan newly written journals
- validate journal structure
- compute scores and trends
- evaluate champion vs challenger runs
- propose new skill variants
- emit promotion decisions
- analyze Mentor’s own orchestration telemetry

Heartbeat artifacts:
- `journal_ingestion_report.json`
- `variant_proposal.json`
- `variant_evaluation.json`
- `variant_decision.json`
- heartbeat journal entries

---

## Layered Evaluation Loops

Mentor must implement four nested loops.

### Layer 1 — Micro Action Loop
Timescale: milliseconds to seconds

Purpose:
Validate single actions and outputs.

Examples:
- malformed JSON
- missing fields
- invalid extraction
- broken schema

Allowed actions:
- immediate retry
- local repair
- fallback formatting

### Layer 2 — Task Execution Loop
Timescale: seconds to minutes

Purpose:
Ensure each task completes.

Monitors:
- task stalls
- repeated retries
- missing artifacts
- dependency blocks

Allowed actions:
- retry task
- refine instructions
- switch skill
- split task

### Layer 3 — Strategy / Project Loop
Timescale: minutes to hours

Purpose:
Improve the active project plan while work is underway.

Monitors:
- dependency ordering
- bottlenecks
- redundant tasks
- parallelization opportunities

Allowed actions:
- reorder dependencies
- insert new tasks
- merge redundant tasks
- parallelize branches

### Layer 4 — Evolution Loop
Timescale: hours to weeks

Purpose:
Improve skills and orchestration policies over time.

Monitors:
- run quality trends
- OKR regressions
- skill/model pairing quality
- recurring failure patterns
- Mentor’s own orchestration efficiency

Allowed actions:
- propose new variants
- continue / promote / archive active variants
- propose changes to Mentor’s own orchestration process

---

## Runtime Data Model

### Project Record

Required fields:
- `project_id`
- `goal`
- `constraints`
- `requested_output`
- `status`
- `created_at`
- `updated_at`

### Task Node

Required fields:
- `task_id`
- `title`
- `description`
- `dependencies`
- `candidate_skill`
- `status`
- `retry_count`
- `priority`
- `expected_artifacts`
- `blocking_reason`
- `created_at`
- `updated_at`

Task statuses:
- `pending`
- `ready`
- `running`
- `blocked`
- `failed`
- `complete`
- `archived`

---

## Scheduling Rules

Mentor must:

- execute only tasks whose dependencies are complete
- prioritize critical-path tasks
- allow bounded parallelism
- avoid unnecessary fan-out
- enforce bounded retry count before escalation
- prefer repair over abandonment
- replan before deadlock whenever possible

---

## Skill Invocation Rules

Mentor may orchestrate any compatible skill.

It must maintain a per-task invocation record with:
- `task_id`
- `skill_name`
- `skill_version`
- `input_hash`
- `start_time`
- `end_time`
- `success`
- `retry_count`
- `artifacts_produced`

Mentor must be model-aware when possible and store:
- `model`
- `provider`
- `context_window`
- `node` if available

This model data must be available for later analysis of skill-to-model pairings.

---

## Failure Repair Policy

When a task fails, Mentor must attempt recovery in this order:

1. retry same task with refined framing
2. retry with alternate compatible skill
3. split task into smaller tasks
4. revise task ordering / dependencies
5. mark blocked and escalate to strategy loop

Every repair action must be journaled.

Mentor must never retry indefinitely.

---

## Journals Requirements

Every skill in the ecosystem, including Mentor, must write journals in a consistent structure.

Forge must build Mentor with a deep built-in understanding of the journals contract.

Do not treat journals as an optional add-on.

Mentor must both write and read journals.

### Journal Identity Requirements

Each run entry must contain:

- `comparison_group_id`
- `run_id`
- `run_role` (`champion` or `challenger`)
- `skill_name`
- `skill_version`
- `normalized_input_hash`
- `timestamp_start`
- `timestamp_end`

### Runtime Section

Each entry must contain runtime metadata when available:

- `model`
- `provider`
- `temperature`
- `context_window`
- `node`
- `oc_version`

### Decision Section

Each entry must record the decision or result of the run.

### Action Section

Each entry must record:
- `side_effect_intent`
- `side_effect_executed`

Variants must have:
- `side_effect_executed: false`

### Metrics Section

Each entry must contain metrics sufficient to compute OKRs and run quality.

### OKR Evaluation Section

Each entry must include scored universal OKRs plus any relevant skill-specific OKR evaluation.

### Journal Invariants

- append-only
- immutable after write
- atomic writes
- invalid journals must be quarantined, not trusted

---

## Universal OKRs

Mentor must evaluate these universal OKRs across all skills.

### Reliability
- `success_rate` — maximize
- `failure_rate` — minimize
- `retry_rate` — minimize

### Validation Integrity
- `validation_failure_rate` — minimize
- `artifact_acceptance_rate` — maximize

### Efficiency
- `avg_latency_ms` — minimize over trend
- `repair_events` — minimize

### Context Stability
- `context_utilization` — minimize
- `overflow_rate` — minimize

### Observability
- `journal_completeness` — maximize, target = 1.0

Forge must generate Mentor with these universal OKRs built in as standard scoring inputs.

---

## Mentor-Specific OKRs

Forge must define Mentor’s own skill-specific OKRs using the same structure as any other skill.

Mentor-specific OKRs must include at minimum:

- `task_completion_rate` — maximize
- `blocked_task_rate` — minimize
- `repair_success_rate` — maximize
- `mean_time_to_task_completion` — minimize
- `task_graph_revision_efficiency` — maximize
- `orchestration_retry_rate` — minimize
- `project_completion_rate` — maximize
- `journal_analysis_latency` — minimize
- `improvement_proposal_precision` — maximize

These should be implemented as rolling-window metrics rather than single-run judgments wherever possible.

---

## Champion / Challenger Evaluation

Mentor must evaluate champion vs challenger runs by pairing entries with the same `comparison_group_id`.

A valid pair requires:

- one champion run
- one challenger run
- identical `normalized_input_hash`
- valid journal schema
- challenger executed no side effects

For each pair, Mentor must compare:
- universal OKRs
- skill-specific OKRs
- latency
- retries
- reliability
- downstream outcome if available

Mentor must build an aggregate evaluation dataset over multiple runs.

Do not promote variants on a single-run basis except for explicit emergency rollback recommendation logic.

---

## Variant Proposal Generation

Mentor must emit structured build proposals that Forge can consume directly.

Each proposal must contain:

- `proposal_id`
- `target_skill`
- `base_version`
- `proposal_timestamp`
- `observed_problem`
- `supporting_evidence`
- `proposed_changes`
- `expected_improvement`
- `evaluation_plan`
- `minimum_runs`
- `critical_non_regression_conditions`

Example observed problems:
- high retry rate
- low OKR performance
- rising latency
- poor model pairing
- recurring orchestration bottleneck
- poor claim verification
- unstable decision quality

Mentor must be allowed to generate proposals for:
- other skills
- itself

---

## Promotion Decision Output

Mentor must not directly modify champion skills.

Instead it emits decision artifacts for Forge.

Allowed decisions:
- `promote`
- `continue_testing`
- `archive`
- `reject`
- `emergency_rollback_recommendation`

Each decision artifact must contain:
- `variant_id`
- `target_skill`
- `evaluation_window`
- `aggregate_scores`
- `confidence`
- `decision`
- `rationale`
- `non_regression_check`
- `timestamp`

---

## Mentor Self-Improvement

Mentor must analyze its own orchestration journals the same way it analyzes other skills.

Mentor should be able to improve:
- task decomposition heuristics
- dependency graph ordering
- retry policy
- repair sequencing
- skill routing preferences
- evaluation thresholds
- heartbeat analysis cadence
- journaling completeness

This is the reason Mentor remains one skill with internal subsystems rather than being split.

---

## Heartbeat Execution Plan

In heartbeat mode, Mentor must execute this pipeline:

1. ingest newly written journals
2. validate schema and quarantine malformed entries
3. update aggregate metrics
4. pair new champion/challenger runs
5. recompute rolling OKR scores
6. detect anomalies and regressions
7. evaluate active variants
8. generate new variant proposals where justified
9. emit promotion decisions where justified
10. write heartbeat journal output

Mentor should support:
- lightweight heartbeat pass
- deep evaluation pass

The lightweight pass updates aggregates and queues work.
The deep pass performs full scoring, trend analysis, and proposal generation.

---

## Required Outputs

Forge must implement Mentor so it can generate at minimum these artifact classes.

Runtime mode:
- `project_state.json`
- `task_graph.json`
- `execution_state.json`
- runtime journal entries

Heartbeat mode:
- `journal_ingestion_report.json`
- `anomaly_report.json`
- `variant_proposal.json`
- `variant_evaluation.json`
- `variant_decision.json`
- heartbeat journal entries

---

## Safety Invariants

Mentor must enforce these invariants:

- challenger variants never execute side effects
- comparisons only occur on identical normalized inputs
- malformed journals are not trusted
- promotion requires sufficient evidence
- universal OKRs are always scored
- Mentor journals its own orchestration decisions
- retries are bounded
- runtime orchestration is separated from irreversible actions

---

## Forge Deliverable Requirements

Forge must produce a complete `ocas-mentor` skill with:

- valid `SKILL.md`
- internal logic for both modes
- internal modularization matching this build file
- journal writing behavior
- journal ingestion and evaluation behavior
- OKR scoring logic
- variant proposal generation logic
- promotion decision generation logic
- self-improvement logic for Mentor itself

Do not leave placeholder sections.
Do not omit heartbeat mode.
Do not omit Mentor-specific OKRs.
Do not omit journal schema validation behavior.
Do not assume prior knowledge of any ecosystem acronym or undocumented context.

---

## Final Expected Behavior

When invoked manually, Mentor behaves like a long-running autonomous project manager.

When invoked by heartbeat, Mentor behaves like a system evaluator and evolution engine.

Over time, Mentor must improve:
- the skills it supervises
- the skill/model pairings it chooses
- its own orchestration process

This is the intended behavior of `ocas-mentor`.

---

## Skill Identity

- Skill name: `ocas-mentor`
- Version: `1.1.0`
- Skill type: `system`
- Author: `Indigo Karasu`
- Email: `mx.indigo.karasu@gmail.com`

---

## Optional Skill Cooperation

This skill may cooperate with other skills when present but must never depend on them.
If a cooperating skill is absent, this skill must still function normally.

- Forge — emit variant proposals that Forge consumes to build skill packages.
- All skills — orchestrate and supervise any compatible skill during runtime mode.

---

## Journal Outputs

This skill emits the following journal types as defined in the OCAS Journal Specification (spec-ocas-Journals.md):

- Action Journal

Mentor emits Action Journal entries for orchestration decisions, variant proposals, and promotion decisions. Mentor also reads all journal types during heartbeat evaluation.

---

## Visibility

visibility: public

---

## Required Package Output

Forge must produce a complete Agent Skill package:

```text
ocas-mentor/
  skill.json
  SKILL.md
  references/
    schemas.md
    orchestration_engine.md
    evaluation_engine.md
    evolution_engine.md
```

### `skill.json` Requirements

Create a valid `skill.json` with:
- `name`: `ocas-mentor`
- `version`: `1.1.0`
- `description`: routing-optimized text
- `author`: `Indigo Karasu`
- `email`: `mx.indigo.karasu@gmail.com`

The description must make clear that this skill is for:
- orchestrating long-running multi-skill workflows
- task decomposition, scheduling, and failure repair
- journal analysis and skill performance evaluation
- champion vs challenger variant comparison
- generating skill improvement proposals for Forge
- self-improving orchestration over time

### `SKILL.md` Requirements

`SKILL.md` must begin on line 1 with valid YAML frontmatter delimited by `---`.

Target size: 250 to 350 lines.

Mentor is a single skill with two invocation modes. `SKILL.md` must clearly separate these modes.

#### Required `SKILL.md` Sections

The markdown body must contain these sections in this order:

1. `# Mentor`
2. `## When to use`
3. `## When not to use`
4. `## Core promise`
5. `## Commands`
6. `## Mode A — Runtime orchestration`
7. `## Mode B — Heartbeat evolution`
8. `## Layered evaluation loops`
9. `## Failure repair policy`
10. `## Safety invariants`
11. `## Support file map`
12. `## Storage layout`
13. `## Validation rules`

### Commands

The built skill must implement these commands:

- `mentor.project.create` — create a new project with goal, constraints, and requested output
- `mentor.project.status` — return current project state, task graph, and execution progress
- `mentor.project.replan` — trigger a strategy-level replan of the current project
- `mentor.task.list` — list tasks with statuses, dependencies, and blocking reasons
- `mentor.heartbeat.light` — run a lightweight heartbeat pass (update aggregates, queue work)
- `mentor.heartbeat.deep` — run a deep evaluation pass (full scoring, trend analysis, proposal generation)
- `mentor.variants.list` — list active champion/challenger variant pairs with evaluation status
- `mentor.variants.decide` — emit a promotion decision (promote|continue_testing|archive|reject) for a variant
- `mentor.proposals.list` — list pending skill improvement proposals
- `mentor.proposals.create` — generate a new variant proposal for a target skill
- `mentor.status` — return Mentor state including active projects, pending evaluations, and self-improvement metrics

### Storage Layout

```text
.mentor/
  config.json
  projects/
    {project_id}/
      project_state.json
      task_graph.json
      execution_state.json
  evaluations/
    journal_ingestion_report.json
    variant_proposals.jsonl
    variant_evaluations.jsonl
    variant_decisions.jsonl
  journals.jsonl
  decisions.jsonl
```

### Config

File: `.mentor/config.json`

Required fields:
- `orchestration.max_parallel_tasks`: maximum concurrent tasks
- `orchestration.max_retries`: maximum retries before escalation
- `evaluation.rolling_window_runs`: number of runs for rolling OKR evaluation
- `evaluation.promotion_min_runs`: minimum runs before promotion is allowed
- `evolution.self_improvement_enabled`: whether Mentor can propose changes to itself
- `heartbeat.light_interval_minutes`: frequency of light heartbeat
- `heartbeat.deep_interval_hours`: frequency of deep heartbeat

### `references/schemas.md`

Must define schemas for:
- `Project` — project_id, goal, constraints, requested_output, status, created_at, updated_at
- `TaskNode` — task_id, title, description, dependencies, candidate_skill, status (pending|ready|running|blocked|failed|complete|archived), retry_count, priority, expected_artifacts, blocking_reason
- `SkillInvocation` — task_id, skill_name, skill_version, input_hash, start_time, end_time, success, retry_count, artifacts_produced, model, provider
- `VariantProposal` — proposal_id, target_skill, base_version, observed_problem, supporting_evidence, proposed_changes, expected_improvement, evaluation_plan, minimum_runs
- `VariantEvaluation` — variant_id, evaluation_window, aggregate_scores, confidence, champion_scores, challenger_scores
- `VariantDecision` — variant_id, target_skill, decision (promote|continue_testing|archive|reject|emergency_rollback_recommendation), rationale, non_regression_check, timestamp
- `DecisionRecord` — decision_id, decision_type, evidence_refs, outcome, timestamp

### `references/orchestration_engine.md`

Must document:
- goal decomposition into task graphs
- dependency management and scheduling rules
- skill selection and invocation protocol
- the four-layer evaluation loop (micro action, task execution, strategy/project, evolution) with timescales
- failure repair sequence (retry → alternate skill → split task → revise ordering → escalate)
- bounded retry policy
- model-awareness and skill-to-model pairing data

### `references/evaluation_engine.md`

Must document:
- journal ingestion and schema validation
- journal aggregation across skills
- universal OKR scoring with targets
- skill-specific OKR scoring
- champion/challenger pairing rules (same comparison_group_id, identical normalized_input_hash, challenger never executed side effects)
- rolling-window aggregate evaluation
- anomaly and regression detection
- why single-run promotion is not allowed except for emergency rollback

### `references/evolution_engine.md`

Must document:
- how improvement opportunities are detected from journal trends
- variant proposal generation structure
- evaluation plan requirements for new variants
- promotion decision criteria and confidence thresholds
- Mentor self-improvement: what Mentor can propose changing about its own orchestration
- the full heartbeat pipeline (ingest → validate → aggregate → pair → score → detect → evaluate → propose → decide → journal)


---

## Final Response Format for the Coder

Return:

1. package tree
2. full contents of every file
3. brief validation summary

Do not return planning commentary, process narration, or references to absent documents.
