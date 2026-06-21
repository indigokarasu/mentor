# Deep Heartbeat Dual-Path Fix (2026-06-13)

## Problem
`cron-heartbeat-deep.py` uses `os.walk("/root/.hermes/commons/journals/")` which only scans **168 files** across 9 skill dirs. The real data lives under `/root/.hermes/profiles/indigo/commons/journals/` with **6,597 files** across 41 skill dirs. This caused:
- `evaluation_coverage` to report ~0.19 instead of 1.0
- Skill health stats based on <3% of actual journals
- OKR scores meaningless due to tiny sample size

## Solution
Use the dual-path wrapper script `scripts/cron-heartbeat-deep-dualpath.py` which:
1. Scans both `/root/.hermes/commons/journals/` AND `/root/.hermes/profiles/indigo/commons/journals/`
2. Uses absolute paths for dedup keys (works across both roots)
3. Writes evidence/OKR data to BOTH commons and profile-scoped data dirs
4. Caps `active_coverage` at 1.0 (raw >1.0 indicates historical ingestion, not an error)

## Key Metrics from First Dual-Path Run (2026-06-13 19:05Z)
| Metric | Stock Script | Dual-Path Wrapper |
|--------|-------------|-------------------|
| Journals scanned | 168 | 6,781 |
| Skills evaluated | 9 | 41 |
| evaluation_coverage | ~0.19 | 1.0 |
| orchestration_success_rate | N/A | 0.9978 |
| error_rate | N/A | 0.0022 |

## Second Dual-Path Run (2026-06-14 19:01Z)
| Metric | Value |
|--------|-------|
| Journals scanned | 7,341 |
| New ingested | 7,340 |
| Skills evaluated | 41 |
| evaluation_coverage | 1.0 |
| orchestration_success_rate | 0.9980 |
| error_rate | 0.0020 |
| Parse errors | 15 |
| Proposals | 2 (ocas-taste, ocas-dispatch — both auth-related, see gotcha #37a) |

## Usage
The cron job `mentor:deep` should be updated to:
```
python3 /root/.hermes/profiles/indigo/skills/ocas-mentor/scripts/cron-heartbeat-deep-dualpath.py
```

## Evidence Schema Difference
The evidence record includes `"dual_path": true` and `"active_coverage_raw"` fields not present in stock script output. Display code should handle both schemas.

## Profile-Scoped Data Sync
After each deep heartbeat run, the wrapper writes evidence + OKR state to `/root/.hermes/profiles/indigo/commons/data/mentor/` so the profile-scoped evidence log stays in sync with commons. This is needed because light heartbeats read from both locations.
