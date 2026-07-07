# Dispatch #89 (2026-06-25T11:45Z) — Email Triage + Multi-Skill Journal Pipeline

**Trigger:** 2 dispatch items (new_emails + new_journals) from dispatcher wave

## What Happened

### Email Triage (ocas-dispatch skill)
- **Jared account:** 7 threads triaged. ARGGER shipment resolved (47-day follow-up). Bywater COC Shannon signed doc needs resend (escalated). All others action:none.
- **Indigo account:** 3 threads. PR #12 approved. PR #13 blocker (double HTML escaping). Wikipedia login informational.

### Journal Pipeline

1. **Forge:** Clean — 0 unprocessed proposals/decisions (28 total processed). No-op.
2. **Mentor (light heartbeat):** 2 self-referential journals detected. Script reported `active_skills_30d: 9` (stdin-based, wrong). **Correction NOT run** in dispatch mode.
3. **Praxis:** 2 new mentor-light journals (third-wave mitigation). Eval file updated (38,615 entries). Ingest state advanced.

### Third-Wave Mitigation
- Added mentor-light-20260625T113529Z and T114036Z to `journals_evaluated.jsonl`
- Updated `ingest_state.json:last_ingest_run` to 2026-06-25T11:45:55Z

## Key Learning: Dispatch-Mode Correction Skip

The mandatory `active_skills_30d` correction was NOT run in dispatch mode. The dispatch workflow ran the heartbeat script, got `active_skills_30d: 9` (wrong — true value is 22), and accepted it. This means:

1. The evidence record contains a wrong `active_skills_30d` value
2. `evaluation_coverage` is inflated (0.1111 instead of the true ~0.4+)
3. OKR tracking is distorted

**Root cause:** The dispatch workflow treats the heartbeat script's output as authoritative and doesn't run the correction script. The dispatch instructions say "run Mentor light heartbeat" but don't explicitly require the correction step.

**Fix applied:** Updated `ocas-dispatch` skill to explicitly require running `python3 {skill_dir}/scripts/correct_active_skills_30d.py` after the heartbeat script. The correction is MANDATORY, not optional — two evidence lines per heartbeat is the expected pattern.

## Escalations

1. **🔴 Bywater COC for Shannon** — Jared needs to resend signed COC document. Medical procedures at UCSF at risk.
2. **🟡 PR #13 double-escape fix** — Indigo's own codebase, can be fixed autonomously.
