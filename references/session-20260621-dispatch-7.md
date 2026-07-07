# Session 2026-06-21 Dispatch — Shell Var in Heredoc, All Pipelines Clean

**Date**: 2026-06-21T21:25–21:31Z  
**Trigger**: Dispatcher `new_journals` (5 new files)  
**Pipelines**: Forge + Mentor + Praxis

## Shell Variable Not Available Inside `'PYEOF'` Heredoc

**Bug**: Referencing `$JOURNAL_DIR` (a shell variable set earlier in the same `terminal()` block) inside `python3 << 'PYEOF'` produced `NameError: name 'JOURNAL_DIR' is not defined`.

**Root cause**: Single-quoted heredoc (`'PYEOF'`) prevents ALL shell variable expansion. The Python process never sees the shell variable value.

**Fix**: Construct paths inside the Python heredoc, don't reference shell variables:
```python
python3 << 'PYEOF'
import os
journal_dir = f"/root/.hermes/profiles/indigo/commons/journals/ocas-mentor/2026-06-21"
os.makedirs(journal_dir, exist_ok=True)
# ... use journal_dir, not $JOURNAL_DIR ...
PYEOF
```

**Lesson**: When writing Python code via `'PYEOF'` heredoc, never rely on shell variable interpolation. Hardcode paths or construct them in Python.

## Dispatch Summary

| Pipeline | Result | Detail |
|----------|--------|--------|
| Forge | no_op | 0 unprocessed proposals/decisions |
| Mentor | success | 4515 scanned, 4 ingested, active_skills_30d corrected 14→22 |
| Praxis | success | 5 new journals (excl. self), 0 events, all routine no-ops |

**Key technique verified**: Captured `last_ingest_run` from Praxis `ingest_state.json` BEFORE running Mentor heartbeat — prevented cross-pipeline state collision. Confirmed 7+ times, dispatch standard.

## active_skills_30d Correction

Script-reported: 14 (stdin-count, 3-day window).  
True dual-path 30-day count: 22 (all skills) / 18 (OCAS-only).  
Correction is MANDATORY every dispatch run.
