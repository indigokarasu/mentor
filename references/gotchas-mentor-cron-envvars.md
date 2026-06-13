# Mentor Gotcha — Cron Env Var Propagation

## Problem: Env Vars Don't Propagate Through Pipes in Cron `terminal()`

When running the light heartbeat via `terminal()` in cron mode, environment variables set via `export` or inline `VAR=value` may not reach the piped Python process.

### Symptom

`active_skills_30d` reports the 3-day stdin count (e.g., 15) instead of the true 30-day count (e.g., 35), despite `MENTOR_ACTIVE_SKILLS_30D=35` being set.

### Root Cause

The terminal tool may split command blocks into separate subshell invocations. Even `export VAR=value` followed by `cmd1 | cmd2` in the same `terminal()` block may not propagate `VAR` to `cmd2`.

### Patterns Tested

| Pattern | Works? | Notes |
|---------|--------|-------|
| `VAR=value cat file \| python3 script.py` | ❌ | Var only applies to `cat`, not `python3` |
| `export VAR=value` then `cat file \| python3 script.py` | ⚠️ Unreliable | May fail if terminal splits into subshells |
| `cat file \| VAR=value python3 script.py` | ✅ Safest | Var placed directly before target command on same pipeline stage |

### Recommended Fix

```bash
# SAFEST — env var inline before the target command:
cat /tmp/mentor_files_3d.txt | MENTOR_ACTIVE_SKILLS_30D=35 python3 scripts/cron-heartbeat-light.py
```

### Related Gotchas

- Gotcha #30 in `gotchas-mentor.md` — original env var pipe issue
- Gotcha #23 in `gotchas-mentor.md` — Python `with open()` writes silently fail in cron
- Gotcha #46 in `gotchas-mentor.md` — verify-before-write pattern

### History

- 2026-06-05: First caught — inline `VAR=value` before `cat` didn't reach `python3`
- 2026-06-06: Even `export VAR=value` in the same terminal block failed; `active_skills_30d: 15` instead of `35`
