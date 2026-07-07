# Dispatch #49 — 2026-06-24T19:28Z (Mentor in Multi-Skill Dispatch)

**Trigger:** Multi-skill dispatch (email + journals), `skill: "multi"`

## Input
- Dispatcher `new_files`: 2 journals (mentor-light-20260624T191357Z, cron-ingest-20260624T191439Z)
- Dual-path 3-day file list: 1147 files

## Outcome
- **Script result:** success (evidence +1, ingestion +2, journal written)
- **Script `active_skills_30d`:** 9 (stdin-based, wrong as expected)
- **Corrected `active_skills_30d`:** 22 (OCAS: 18)
- **Correction mandatory:** YES — script succeeded on all 3 writes but count was still wrong

## Path Discovery: correct_active_skills_30d.py
The correction script path was initially tried as `/root/.hermes/profiles/indigo/skills/mentor/scripts/correct_active_skills_30d.py` — **WRONG** (doesn't exist). The correct path is `/root/.hermes/profiles/indigo/skills/ocas-mentor/scripts/correct_active_skills_30d.py`. The skill name is `ocas-mentor`, not `mentor`. This seems obvious but the skill directory naming convention (ocas- prefix) is easy to forget under pressure, especially when the data directory is `commons/data/mentor/` (no ocas- prefix).

**Fix:** Always use `skills/ocas-mentor/scripts/` path. The data directory (`commons/data/mentor/`) does NOT match the skill directory (`skills/ocas-mentor/`).

## Third-Wave Mitigation Required
The Praxis ingest at 19:30:13Z processed 6 journals but did NOT automatically add the cron-ingest journal from the prior wave (19:14:39Z) or the forge-scan journal from this wave (19:28:00Z) to `journals_evaluated.jsonl`. Manual addition was required for:
- `ocas-praxis/2026-06-24/cron-ingest-20260624T191439Z.json`
- `ocas-forge/2026-06-24/forge-scan-20260624T192800Z.json`
- `ocas-mentor/2026-06-24/mentor-light-20260624T192817Z.json` (already added by script but included for completeness)

This is a recurring pattern — the Praxis ingest script does NOT always add all dispatch-output journals to the eval file. The third-wave mitigation is the caller's responsibility.

## Assessment
Routine multi-skill dispatch. All 4 pipelines completed clean. Email: all action:none (Jared hard rule enforced, Indigo self-sent filter confirmed). Forge: no-op. Mentor: correction 9→22 (mandatory). Praxis: 6 journals, 4 events (all no-signal). Third-wave mitigation applied.

## Key Metrics
- `evaluation_coverage`: 0.1111 (1 skill with new / 9 script-counted)
- `new_files_ingested`: 2
- `errors`: 0
- `gap_detected`: false
- `active_anomalies`: 0
