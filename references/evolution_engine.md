# Mentor Evolution Engine

## Improvement Detection
Detect from journal trends: high retry rate, low OKR performance, rising latency, poor model pairing, recurring bottlenecks, unstable decision quality.

## Proposal Generation
Each proposal follows the VariantProposal schema from spec-ocas-shared-schemas.md. Fields: target skill, base version, observed problem, evidence, proposed changes, expected improvement, evaluation plan, minimum runs, critical non-regression conditions.

Write proposals to: `{agent_root}/commons/data/ocas-forge/{proposal_id}.json`

## Proposal Stall Detection
Before generating a new proposal, check `evaluations/proposal_stall_tracking.jsonl` for existing proposals targeting the same skill+issue. If ≥3 consecutive proposals exist with no Fellow evaluation (no matching cycle_id in `fellow_results_ingested.jsonl`):

- **Do NOT write another identical proposal.**
- If the issue is a low-risk efficiency fix (no side effects, no user-facing behavior change): write a VariantDecision with `auto_approved: true` and rationale, then notify via Dispatch.
- If the issue is not auto-approvable: write a single escalation note to `decisions.jsonl` and stop re-proposing until Fellow responds or the user intervenes.
- Track all proposal counts and stall state in `evaluations/proposal_stall_tracking.jsonl`.

This prevents the infinite re-proposal loop that occurs when Fellow is not evaluating proposals.

## Promotion Criteria
Promote when: sufficient runs completed, aggregate scores exceed champion, no non-regression failures. Continue testing if inconclusive. Archive if consistently worse.

Write decisions to: `{agent_root}/commons/data/ocas-forge/{decision_id}.json`

## Self-Improvement
Mentor analyzes its own orchestration journals. May improve: task decomposition heuristics, dependency ordering, retry policy, skill routing preferences, evaluation thresholds, heartbeat cadence.
