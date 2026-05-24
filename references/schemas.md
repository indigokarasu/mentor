# Mentor Schemas

## Project
```json
{"project_id":"string","goal":"string","constraints":"object","requested_output":"string","status":"string","created_at":"string","updated_at":"string"}
```

## TaskNode
```json
{"task_id":"string","title":"string","description":"string","dependencies":["string"],"candidate_skill":"string","status":"string — pending|ready|running|blocked|failed|complete|archived","retry_count":"number","priority":"number","expected_artifacts":["string"],"blocking_reason":"string|null"}
```

## SkillInvocation
```json
{"task_id":"string","skill_name":"string","skill_version":"string","input_hash":"string","start_time":"string","end_time":"string","success":"boolean","retry_count":"number","artifacts_produced":["string"],"model":"string|null","provider":"string|null"}
```

## VariantProposal
See spec-ocas-shared-schemas.md for the canonical VariantProposal schema.

Written to: the `variant_proposal` payload field in the journal entry

## VariantDecision
See spec-ocas-shared-schemas.md for the canonical VariantDecision schema.

Written to: the `variant_decision` payload field in the journal entry

## Storage Layout

```
{agent_root}/commons/data/ocas-mentor/
  config.json
  projects/
  evaluations/
  ingestion_log.jsonl
  intents.jsonl
  evidence.jsonl
  decisions.jsonl
  fellow_results_ingested.jsonl
  experiment-requests/
    {experiment_id}.json
  plans/
    {plan_id}.plan.md
  plan-runs/
    {plan_run_id}/
      state.json
      decisions.jsonl

{agent_root}/commons/journals/ocas-mentor/
  YYYY-MM-DD/
    {run_id}.json
```


## Default Configuration

```yaml
skill_okrs:
  - name: orchestration_success_rate
    metric: fraction of projects reaching completion without manual rescue
    direction: maximize
    target: 0.85
    evaluation_window: 30_runs
  - name: evaluation_coverage
    metric: fraction of installed skills that have emitted at least one journal (skills-with-journals / total-installed-skills)
    direction: maximize
    target: 0.99
    evaluation_window: 30_runs
  - name: variant_decision_quality
    metric: fraction of promotions not rolled back within 30 days
    direction: maximize
    target: 0.90
    evaluation_window: 30_runs
  - name: repair_escalation_rate
    metric: fraction of failures requiring strategy-level escalation
    direction: minimize
    target: 0.10
    evaluation_window: 30_runs
  - name: schedule_adherence
    metric: fraction of scheduled heartbeat/cron runs that completed within their expected window
    direction: maximize
    target: 0.95
    evaluation_window: 30_runs
  - name: data_integrity
    metric: fraction of evidence records with valid schema and no missing mandatory fields
    direction: maximize
    target: 0.99
    evaluation_window: 30_runs
```

