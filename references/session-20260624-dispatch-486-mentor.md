# Dispatch #486 — 2026-06-24T18:08Z (Mentor in Multi-Skill Dispatch)

**Trigger:** Multi-skill dispatch (Forge + Mentor + Praxis), `skill: "multi"`

## Input
- Dispatcher `new_files`: 2 journals (esc-run custodian, mentor-light)
- Dual-path 3-day file list: 1163 files

## Outcome
- **Script result:** success (evidence +1, ingestion +2, journal written)
- **Script `active_skills_30d`:** 9 (stdin-based, wrong as expected)
- **Corrected `active_skills_30d`:** 22 (OCAS: 18)
- **Correction mandatory:** YES — script succeeded on all 3 writes but count was still wrong

## Assessment
Routine multi-skill dispatch. Script completed successfully on all writes (evidence, ingestion, journal) but `active_skills_30d` undercounted (9 vs true 22). This is confirmation #24+ of gotcha #29 — the correction is mandatory regardless of script success. Two evidence lines written: script's version (undercount) + caller's corrected version.

## Key Metrics
- `evaluation_coverage`: 0.1111 (1 skill with new / 9 script-counted)
- `new_files_ingested`: 2
- `errors`: 0
- `gap_detected`: false
- `active_anomalies`: 0
