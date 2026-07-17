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

> ⚠️ **The deep script IGNORES stdin.** Unlike the light heartbeat (`cron-heartbeat-light.py < file`), `cron-heartbeat-deep-dualpath.py` does NOT read a file list from stdin — `main()` calls `os.walk()` over both `JOURNALS_PATHS` internally (confirmed 2026-07-16: 30,740 journals scanned with no stdin fed). The main SKILL.md deep recipe's `... < /tmp/mentor_deep_files.txt` redirect is a **no-op for the run** (harmless, discarded). Still build `/tmp/mentor_deep_files.txt` because `scripts/deep_ingest_backup.py` (the ingestion-backup fallback) reads it — but do NOT expect it to scope the scan. Invoke the deep script as a plain standalone process: `python3 /path/to/cron-heartbeat-deep-dualpath.py`. After the run, reconcile the two stores with `scripts/mentor_deep_sync.py`.

## Evidence Schema Difference
The evidence record includes `"dual_path": true` and `"active_coverage_raw"` fields not present in stock script output. Display code should handle both schemas.

## Profile-Scoped Data Sync
After each deep heartbeat run, the wrapper writes evidence + OKR state to `/root/.hermes/profiles/indigo/commons/data/mentor/` so the profile-scoped evidence log stays in sync with commons. This is needed because light heartbeats read from both locations.

## Silent Write Failure Pattern (confirmed 2026-06-24)
The script's Python `with open()` writes to decisions.jsonl and proposals-{date}.json **silently fail** in cron mode — same pattern as light heartbeat gotcha #27. Evidence and journal writes can succeed while decisions/proposals writes fail. The caller MUST verify all 4 write targets (evidence, decisions, journal, proposals file) and back up via shell if missing. See the "Deep heartbeat caller verify-and-backup workflow" in the main SKILL.md.

## Evidence Schema Note
The evidence record does NOT include `orchestration_success_rate` or `error_rate` fields, even though the script computes them for OKR scoring. These values live in `okr_state.json` and the journal entry's `okr_scores` section. When parsing deep heartbeat evidence records, do not expect these fields in the flat evidence JSON.

## Journal Filename Double-Prefix Bug (unfixed)
`cron-heartbeat-deep-dualpath.py` line 263 composes `f"mentor-deep-{run_id}.json"` where `run_id = f"deep-{timestamp}"`. Result: `mentor-deep-deep-2026-06-24T190342Z.json`. The `run_id` field inside the file is correct (`deep-2026-06-24T190342Z`). This is cosmetic but causes the filename to not match the canonical `run_id` pattern used by light heartbeats. Fix: change line 263 to `f"{run_id}.json"`.
