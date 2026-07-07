# Session 2026-06-22 Light Heartbeat — Gotcha #73 Violation

**Date**: 2026-06-22T07:22Z
**Run ID**: mentor-light-20260622T072035Z
**Trigger**: Direct cron

## What Happened

All 3 script writes succeeded (evidence, ingestion, journal). The heartbeat then:
1. Wrote corrected evidence (active_skills_30d: 14→22) ✅
2. **Incorrectly wrote a separate caller journal** (`mentor-light-20260622T072251Z.json`) — violating gotcha #73 ❌
3. Detected the duplicate, removed it ✅

## Root Cause

The Dispatch/Cron Integration workflow steps said "Write journal" (step 7) while gotcha #73 said "Caller must NOT write a separate journal." The agent followed the workflow steps literally, producing a duplicate.

## Skill Fixes Applied

1. **Step 7 of Dispatch/Cron Integration**: Changed from "Write journal" to "DO NOT write a separate journal — the script's journal is canonical (gotcha #73)."
2. **Step 7 of Dispatch-mode caller workflow**: Same fix.
3. **Verify-and-backup workflow code block**: Changed all paths from commons to profile path, added explicit "DO NOT write a separate caller journal" comment.
4. **New gotcha entry**: "Workflow/gotcha contradiction caused duplicate journal" — documents this specific failure pattern.

## Metrics

- Files scanned: 4757
- New files ingested: 2
- active_skills_30d: 14 (script) → 22 (corrected), 18 OCAS
- Correction count: 17th confirmed correction (2026-06-19 through 2026-06-22)
- All 3 writes succeeded, ingestion delta matched script report
- Gap: 4.1 min (no gap detected)
- Active anomalies: 0
