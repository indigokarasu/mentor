# Dispatch 2026-06-24 — Python Runtime Resolution

**Trigger:** Multi-skill dispatch (email + journals + taste), all pipelines needed Python with googleapiclient

## Problem
Both `ocas-mentor` and `ocas-taste` skills reference `/root/hermes-agent/.venv/bin/python3.13` which does NOT exist.
The venv symlinks all resolve to `/usr/bin/python3` (Python 3.14.4).

## Diagnosis
```
ls -la /root/.hermes-agent/.venv/bin/python* → symlinks → /usr/bin/python3 (3.14)
/root/.local/share/uv/python/cpython-3.13.13-linux-x86_64-gnu/bin/python3.13 → exists but externally-managed (can't pip install)
/root/.hermes/profiles/indigo/commons/data/ocas-taste/venv/bin/python3 → symlinks to /usr/bin/python3 but googleapiclient missing
```

## Resolution
1. Install googleapiclient for system Python: `pip3 install --break-system-packages google-api-python-client google-auth google-auth-oauthlib`
2. Use `/usr/bin/python3` (system 3.14) for all OCAS scripts
3. Token repair was also needed (timezone suffix `+00:00` in expiry field)

## Evidence
- Mentor: script ran successfully with `/usr/bin/python3`, evidence grew by 1, correction 9→22 applied
- Taste: token repair + `/usr/bin/python3` produced 1 signal (Lavash via DoorDash)
- Both skills patched with runtime resolution guidance

## Lesson
**Always verify Python paths before assuming a venv binary exists.** The skill docs referenced a path from a prior environment state. When a `ModuleNotFoundError` for googleapiclient occurs:
1. Check if packages installed for system Python: `/usr/bin/python3 -c "import googleapiclient"`
2. If not: `pip3 install --break-system-packages google-api-python-client google-auth google-auth-oauthlib`
3. Use `/usr/bin/python3` as the runtime
4. Update the skill docs with the current working pattern
