# Deep Heartbeat Session — 2026-06-24 19:03Z

## Run Metadata
- **Run ID:** deep-2026-06-24T190342Z
- **Type:** Deep heartbeat (dual-path), cron-triggered
- **Script:** `cron-heartbeat-deep-dualpath.py` v2.8.23
- **Caller verify-and-backup:** Applied (decisions + proposals backup writes needed)

## Metrics
| Metric | Value |
|--------|-------|
| Journals scanned | 14,640 |
| New ingested | 14,658 |
| Parse errors | 31 |
| Skills evaluated | 42 |
| Active skills (30d) | 22 |
| Installed skill dirs | 42 |
| Gap | 3.0 min (OK) |

## OKR Results
| OKR | Value | Status |
|-----|-------|--------|
| orchestration_success_rate | 0.9999 | ✅ PASS |
| evaluation_coverage | 1.0 | ✅ PASS |
| promotion_accuracy | NO_DATA | ⚪ |
| error_rate | 0.0001 | ✅ PASS |
| escalation_rate | 0.0001 | ✅ PASS |

## Proposals Generated
1. `prop-err-ocas-taste-20260624190342` — HIGH — 9 errors in batch, success_rate 79.5%
2. `prop-err-ocas-dispatch-20260624190342` — HIGH — 5 errors in batch, success_rate 94.4%

## Silent Write Failures Confirmed
- **Evidence.jsonl:** Written successfully (delta +1) ✅
- **decisions.jsonl:** NOT written (delta 0) ❌ — caller backup applied
- **proposals-20260624.json:** NOT written (file missing) ❌ — caller notified
- **Journal:** Written successfully (with double-prefix filename) ✅
- **OKR state:** Written successfully ✅

## Evidence Schema Observation
Evidence record missing `orchestration_success_rate` and `error_rate` fields despite script computing them. Values only in `okr_state.json` and journal `okr_scores`.

## Skill Health Red Flags
- koda-em: 0.0% (1 entry)
- ocas-thread: 0.0% (5 entries)
- ocas-forge: 41.8% (1388 entries)
- ocas-reach: 71.4% (7 entries)
- ocas-taste: 79.5% (83 entries)

## Comparison to Last Deep (2026-06-21)
| Metric | 2026-06-21 | 2026-06-24 | Change |
|--------|-----------|-----------|--------|
| Journals scanned | ~7,000 | 14,640 | +109% (profile journals now fully ingested) |
| Skills evaluated | 41 | 42 | +1 |
| evaluation_coverage | 1.0 | 1.0 | stable |
| orchestration_success_rate | ~0.998 | 0.9999 | improved |
| error_rate | ~0.002 | 0.0001 | improved |
| Proposals | 2 (taste, dispatch) | 2 (taste, dispatch) | same skills re-proposed |
