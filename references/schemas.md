# Mentor Schemas

## Project
```json
{
  "project_id": "string",
  "task_id": "string — from Triage task_ready signal",
  "goal": "string",
  "constraints": "object",
  "requested_output": "string",
  "status": "string — planning | researching | decomposing | active | blocked | complete | archived",
  "heartbeat_interval_seconds": "number — injected from Triage signal",
  "heartbeat_cron_name": "string — mentor-heartbeat-<project_id>",
  "research_complete": "boolean",
  "task_graph_written": "boolean",
  "spawn_depth": "number — must be 1",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

## ResearchResult

Written by Sift to `.mentor/projects/<project_id>/research/<query_id>.json` when invoked as a sub-agent. Read by Mentor after the sub-agent completes.

```json
{
  "query_id": "string",
  "original_question": "string",
  "summary": "string — synthesized answer to the research question",
  "confidence": "string — high | med | low",
  "sources": [
    {
      "url": "string",
      "domain": "string",
      "trust_score": "number",
      "key_findings": "string"
    }
  ],
  "entities_extracted": ["ExtractedEntity — see Sift schemas"],
  "knowledge_gaps_remaining": ["string — questions still unresolved"],
  "enrichment_candidates": ["EnrichmentCandidate — see Sift schemas"],
  "timestamp": "ISO8601"
}
```

**Mentor reads:**
- `summary` and `confidence` to decide whether to proceed or spawn a follow-up query
- `knowledge_gaps_remaining` to determine whether additional research calls are needed
- `entities_extracted` to seed the task graph with known entities

**Follow-up threshold:** if `confidence` is `low` or `knowledge_gaps_remaining` is non-empty and material, spawn one follow-up Sift call with a narrower query targeting the specific gap. Maximum one follow-up per original query.

## TaskNode
```json
{
  "task_id": "string",
  "project_id": "string",
  "title": "string",
  "description": "string",
  "dependencies": ["string — task_ids"],
  "candidate_skill": "string",
  "status": "string — pending | ready | running | blocked | failed | complete | archived",
  "retry_count": "number",
  "priority": "number",
  "expected_artifacts": ["string"],
  "blocking_reason": "string | null",
  "attempts_exhausted": "boolean"
}
```

## SubTask
```json
{
  "subtask_id": "string",
  "parent_task_id": "string",
  "title": "string",
  "description": "string",
  "status": "string — pending | running | complete | failed",
  "candidate_skill": "string | null",
  "retry_count": "number",
  "blocking_reason": "string | null"
}
```

## FailureRecord

Written to `.mentor/projects/<project_id>/tasks/<task_id>/failures.jsonl`.
**Must be read before every retry. Never attempt any approach in `excluded_approaches`.**

```json
{
  "failure_id": "string",
  "task_id": "string",
  "subtask_id": "string | null",
  "timestamp": "ISO8601",
  "attempt_number": "number",
  "approach_tried": "string",
  "failure_reason": "string",
  "excluded_approaches": ["string"],
  "remaining_approaches": ["string"],
  "next_attempt": "string | null"
}
```

## ProgressMarker

Written to `.mentor/projects/<project_id>/tasks/<task_id>/progress.jsonl` after every meaningful unit of work. Read on every heartbeat to detect stalls.

```json
{
  "task_id": "string",
  "subtask_id": "string | null",
  "timestamp": "ISO8601",
  "marker": "string",
  "artifacts_produced": ["string"],
  "next_step": "string"
}
```

## SkillInvocation
```json
{
  "invocation_id": "string",
  "task_id": "string",
  "skill_name": "string",
  "spawn_depth": "number — 2 for direct Mentor spawns",
  "input_hash": "string",
  "start_time": "ISO8601",
  "end_time": "ISO8601 | null",
  "success": "boolean | null",
  "retry_count": "number",
  "artifacts_produced": ["string"],
  "model": "string | null",
  "provider": "string | null"
}
```

## HeartbeatJournalEntry

Written on every heartbeat pass.

```json
{
  "heartbeat_id": "string",
  "project_id": "string",
  "timestamp": "ISO8601",
  "interval_seconds": "number",
  "task_complete": "boolean",
  "active_task_id": "string | null",
  "active_subtask_id": "string | null",
  "last_progress_marker": "string | null",
  "last_progress_timestamp": "ISO8601 | null",
  "stall_detected": "boolean",
  "stall_action": "string | null",
  "next_step": "string"
}
```

## VariantProposal
```json
{
  "proposal_id": "string",
  "target_skill": "string",
  "base_version": "string",
  "observed_problem": "string",
  "supporting_evidence": ["string"],
  "proposed_changes": "string",
  "expected_improvement": "string",
  "minimum_runs": "number"
}
```

## VariantDecision
```json
{
  "variant_id": "string",
  "target_skill": "string",
  "decision": "string — promote | continue_testing | archive | reject | emergency_rollback",
  "rationale": "string",
  "aggregate_scores": "object",
  "confidence": "string",
  "timestamp": "ISO8601"
}
```
