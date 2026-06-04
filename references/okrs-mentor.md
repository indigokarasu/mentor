# Mentor — OKR Definitions

## Skill-Specific OKRs

| OKR | Target | Window | Measurement |
|-----|--------|--------|-------------|
| `orchestration_success_rate` | ≥0.95 | 30 runs | Fraction of orchestration runs completing without strategy-layer replan |
| `evaluation_coverage` | ≥0.90 | 30 runs | `active-skills-with-journals / total-active-skills` (active = journaled in last 30 days) |
| `promotion_accuracy` | ≥0.80 | 20 decisions | Fraction of promoted variants that improve target metric without regression |
| `proposal_stall_rate` | ≤0.10 | 30 runs | Fraction of proposals targeting same skill+issue without Fellow evaluation after 3+ submissions |
| `anomaly_staleness` | ≤0.05 | 30 runs | Fraction of anomalies flagged stale (≥5 consecutive heartbeats unchanged) |

`evaluation_coverage` is informational — not a pass/fail gate.
