---
name: ocas-mentor
description: Long-running task orchestration and self-improving execution engine. Use when a task requires multi-step planning, sub-agent coordination, sequential or parallel task execution, failure recovery, or ongoing progress tracking across sessions. Picks up Triage-routed tasks with heartbeat intervals and works single-mindedly until complete. Runs at depth 1; spawns Sift and task workers at depth 2; task workers may spawn sub-workers at depth 3.
metadata: {"openclaw":{"emoji":"🧭","version":"1.2.0"}}
---

# Mentor

Mentor is the control plane for long-running autonomous work. It receives tasks from Triage (depth 0), runs at depth 1, and orchestrates work by spawning Sift and task-worker sub-agents at depth 2. Those workers may spawn sub-workers at depth 3.

Mentor works single-mindedly on one project at a time until it is complete.

## Depth map

```
depth 0 — main agent / Triage
depth 1 — Mentor (this skill)
depth 2 — Sift research sub-agents, task-worker sub-agents
depth 3 — sub-workers spawned by task workers
```

`maxSpawnDepth: 3` must be set in OpenClaw config. If Mentor detects it is running at depth > 1, it logs a warning and exits — it must always run at depth 1 to preserve spawning headroom for its workers.

## When to use

- Long-running multi-step task received from Triage with `routing_hint: mentor`
- Goal requires research before planning can begin
- Goal requires coordination across multiple skills
- Prior session may have stalled; resuming from disk state
- Evaluate skill performance from journal data (Mode B)
- Generate improvement proposals for Forge (Mode B)

## When not to use

- Web research only — use Sift directly
- Building new skills — use Forge
- User communication — use Dispatch
- Behavioral pattern analysis — use Corvus

## Core promise

Decompose. Research if needed. Write to disk. Execute. Heartbeat. Recover without repeating failures. Journal everything. Do not stop until complete.

---

## Startup sequence

On every invocation, run in order before any other action:

1. **Verify depth** — confirm this session is running at depth 1. If not, log warning and exit.
2. **Read Triage signal** — load `heartbeat_interval_seconds` from the `task_ready` signal. Default to 600 if absent; log a missing-heartbeat warning.
3. **Check for existing project** — scan `.mentor/projects/` for a project matching this `task_id`. If found, load it and resume at the current task. Do not restart.
4. **Register cron heartbeat** — if no heartbeat cron job exists for this project, register one:
   ```bash
   openclaw cron add \
     --name "mentor-heartbeat-<project_id>" \
     --every "<heartbeat_interval>" \
     --session main \
     --system-event "Mentor heartbeat: project <project_id>" \
     --wake now
   ```
5. **Acknowledge Triage signal** — write `task_acknowledged` to `.triage/signals.jsonl`.
6. **Proceed to research gate or task execution** depending on project state.

---

## Research gate

Before building the task graph for a new project, evaluate whether sufficient domain knowledge exists for confident decomposition.

### Confidence assessment

Ask internally:
- Can the goal be decomposed into concrete tasks without additional information?
- Are the right skills, tools, and data sources known?
- Are there key unknowns that would cause the plan to fail or need replanning mid-execution?

If confident: proceed directly to task graph decomposition.
If not confident: run the research phase.

### Research phase (Sift invocation)

Spawn a Sift sub-agent at depth 2 for each knowledge gap:

```json
{
  "tool": "sessions_spawn",
  "params": {
    "task": "sift.research: <specific research question>\n\nContext: <project goal summary>\nOutput path: .mentor/projects/<project_id>/research/<query_id>.json\nWrite a ResearchResult artifact to the output path on completion.",
    "label": "mentor-research-<query_id>",
    "mode": "run",
    "runTimeoutSeconds": 300
  }
}
```

**Rules:**
- Spawn research sub-agents before spawning any task-execution sub-agents
- Each Sift call targets a specific knowledge gap, not the whole project goal
- Maximum 3 parallel Sift research calls per project (bounded by `maxChildrenPerAgent`)
- On completion, read the `ResearchResult` from the output path
- Consolidate all research results into `.mentor/projects/<project_id>/research.md`
- If Sift returns sparse results (confidence < 0.6), spawn one follow-up call with a narrower query before proceeding
- Write research complete flag to `project.json` before proceeding to decomposition

### ResearchResult contract

Sift writes to the path specified in the task. Mentor reads this path after sub-agent completion.

Read `references/schemas.md` for the `ResearchResult` schema.

---

## Task graph decomposition

After research is complete (or confirmed unnecessary):

1. Write `project.json` to `.mentor/projects/<project_id>/project.json`.
2. Decompose the goal into a task graph. Write to `.mentor/projects/<project_id>/tasks.jsonl`.
3. For each non-trivial task, decompose into sub-tasks. Write to `.mentor/projects/<project_id>/tasks/<task_id>/subtasks.jsonl`.
4. Assign a `candidate_skill` to every task and sub-task.
5. Mark the first ready task(s). Do not begin execution until the full graph is on disk.

**Task graph rules:**
- Explicit dependency arrays (empty if none)
- No task begins until all dependencies are `complete`
- Parallelism allowed when tasks share no dependencies
- Bounded parallelism: max 3 concurrent task-worker sub-agents (default)

Read `references/orchestration_engine.md` for decomposition heuristics and skill selection.

---

## Execution

For each ready task, spawn a task-worker sub-agent at depth 2:

```json
{
  "tool": "sessions_spawn",
  "params": {
    "task": "<task description with full context, expected artifacts, output paths>",
    "label": "mentor-task-<task_id>",
    "mode": "run",
    "runTimeoutSeconds": <estimated_seconds>
  }
}
```

Task workers run at depth 2 and may spawn sub-workers at depth 3 for further decomposition.

On every spawn:
- Write a `SkillInvocation` record to `invocations.jsonl`
- Record expected artifact paths in the task node

On completion:
- Update task state in `tasks.jsonl`
- Write a progress marker
- Write a journal entry (success or failure with full detail)
- Advance to next ready task(s)

---

## Heartbeat loop

On every heartbeat system event (`Mentor heartbeat: project <project_id>`):

1. **Completion check** — is the top-level task complete? If yes: finalize, emit `task_completed` to Triage, remove cron job, exit.
2. **Progress check** — load task graph from disk. Identify active task and sub-task.
3. **Stall detection** — if active task has no new progress marker since the last heartbeat: apply failure recovery.
4. **Resume** — continue from current position. Never restart a task with partial progress unless marked `failed`.
5. **Write heartbeat journal entry**.

On project completion, remove the cron job:
```bash
openclaw cron remove --name "mentor-heartbeat-<project_id>"
```

---

## Failure recovery

When a task or sub-task fails, apply in order:

1. **Read failure log first** — load `failures.jsonl` for this task. Never attempt any approach already in `excluded_approaches`.
2. **Retry with refined framing** — adjust prompt to address the failure. Write retry to failure log.
3. **Alternate skill** — switch to a different compatible skill.
4. **Task split** — decompose further and retry each part.
5. **Reorder dependencies** — if a blocking upstream task can be approached differently, replan.
6. **Escalate** — mark `blocked`, write full `blocking_reason`, surface to Triage and user.

Every failure and every recovery attempt is journaled with enough detail for Praxis to derive a behavioral rule.

Read `references/orchestration_engine.md` for full repair policy.

---

## Progress markers

Write after every meaningful unit of work to:
`.mentor/projects/<project_id>/tasks/<task_id>/progress.jsonl`

This is what the heartbeat reads to detect stalls.

---

## Journal emission

Emit a journal entry for every significant event. Events include: project created, research spawned, research complete, task graph written, task started, sub-agent spawned, task completed, failure, recovery attempt, heartbeat pass, project completed, escalation.

Failure and recovery journals must include: what was tried, what failed, what succeeded, what should be avoided. Vague entries defeat Praxis.

Journal location: `.mentor/projects/<project_id>/journals/<date>/<event_id>.json`

---

## Mode B: Heartbeat evolution

During idle heartbeat passes (no active project), Mentor runs the background evaluation pipeline:

ingest journals → validate schema → aggregate OKR metrics → pair champion/challenger runs → detect improvement opportunities → generate Forge proposals → emit decisions

Read `references/evaluation_engine.md` and `references/evolution_engine.md` for details.

---

## Storage layout

```
.mentor/
  config.json
  projects/
    <project_id>/
      project.json
      research.md                   consolidated research notes
      research/
        <query_id>.json             ResearchResult per Sift call
      tasks.jsonl
      invocations.jsonl
      tasks/
        <task_id>/
          subtasks.jsonl
          failures.jsonl            read before every retry
          progress.jsonl            read on every heartbeat
      journals/
        <date>/
          <event_id>.json
  evaluations/
  journals.jsonl
  decisions.jsonl
```

---

## Config requirements

```json
{
  "agents": {
    "defaults": {
      "subagents": {
        "maxSpawnDepth": 3,
        "maxChildrenPerAgent": 5,
        "maxConcurrent": 8,
        "runTimeoutSeconds": 900
      }
    }
  }
}
```

---

## Validation rules

- Mentor always runs at depth 1; exits if depth != 1
- Heartbeat cron registered before first task spawned
- Research phase complete before task graph written
- Task graph on disk before first task-worker spawned
- Failure log read before every retry
- No retry repeats a previously-excluded approach
- Every heartbeat produces a journal entry
- Progress markers written after every completed sub-task
- Cron job removed on project completion

---

## Reference files

| File | When to read |
|---|---|
| `references/schemas.md` | Task, project, ResearchResult, invocation, failure, progress, and heartbeat journal schemas |
| `references/orchestration_engine.md` | Decomposition heuristics, scheduling, skill selection, failure repair policy |
| `references/evaluation_engine.md` | Journal ingestion, OKR scoring, champion/challenger pairing (Mode B) |
| `references/evolution_engine.md` | Improvement detection, proposal generation, promotion criteria (Mode B) |
