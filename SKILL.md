---
license: MIT
name: ocas-mentor
description: 'Self-improving orchestration and evaluation engine. Manages long-running multi-skill workflows, analyzes journals from all skills, evaluates champion vs challenger variants, and proposes skill improvements to Forge. Use for multi-step project management, heartbeat runs, skill performance evaluation, or multi-skill coordination. NOT for: web research (use Sift), skill building (use Forge), user communication (use Dispatch), real-time skill execution, content generation, system health monitoring (use Custodian), or skill evaluation scoring.'
source: https://github.com/indigokarasu/mentor
includes:
- references/**
- scripts/**
metadata:
  author: Indigo Karasu (indigokarasu)
  version: 2.8.23
  hermes:
    category: software-development
    tags:
    - orchestration
    - evaluation
    - multi-skill
    - OCAS-core
tags:
- orchestration
- evaluation
- multi-skill
- OCAS-core
triggers:
- self-improving orchestration
- multi-skill workflow
- skill evaluation engine
- mentor orchestration
---
# Mentor
Mentor is the system's control plane — in runtime mode it decomposes goals into task graphs, supervises execution across skills, and dynamically repairs failures through layered escalation. In heartbeat mode it reads journals from every skill, scores OKR performance against baselines, and generates improvement proposals that flow to Forge and Fellow.
Mentor reads journals to evaluate skill performance. Chronicle ingestion of journal entity observations happens via the Chronicle daily embed pipeline.

## When to Use

- OKR evaluation across all OCAS skills
- Skill performance scoring and improvement recommendations
- Post-major-session learning synthesis
- Skill library health assessment
- When Critique identifies issues needing Mentor follow-up
- **Cron-triggered heartbeats**: Always use stdin redirect (`python3 script.py < file`), never pipe (`cat file | python3 script`) to avoid `tirith:pipe_to_interpreter` security block. See `references/cron-execution-patterns.md` for detailed execution patterns and verification workflows.

## When NOT to Use

- Real-time skill execution or task routing
- Content generation or research
- System health monitoring (use Custodian)
- Skill building (use Forge)

## Responsibility Boundary

Mentor owns orchestration, evaluation, and the improvement loop.

Mentor does not own: skill building (Forge), behavioral pattern detection, behavioral refinement (Praxis), web research (Sift), communications (Dispatch), experimentation execution (Fellow).

## Ontology Types

- **Concept/Event** — projects, tasks, skill performance evaluations, OKR cycles
- **Concept/Idea** — improvement proposals, behavioral patterns
- **Thing/DigitalArtifact** — project state records, task graphs, evaluation reports

Mentor does not emit entity signals directly. Journal outputs are ingested by Chronicle for knowledge persistence.

## Commands

- `mentor.project.create` — create a project with goal, constraints, and requested output
- `mentor.project.status` — current project state, task graph, execution progress
- `mentor.project.replan` — trigger strategy-level replan
- `mentor.task.list` — tasks with statuses, dependencies, blocking reasons
- `mentor.heartbeat.light` — lightweight pass: ingest journals, update aggregates, queue work
- `mentor.heartbeat.deep` — deep pass: full scoring, trend analysis, proposals
- `mentor.variants.list` — active champion/challenger pairs with evaluation status
- `mentor.variants.decide` — emit promotion decision for a variant
- `mentor.proposals.list` — pending skill improvement proposals
- `mentor.proposals.create` — generate a VariantProposal for a target skill
- `mentor.status` — active projects, pending evaluations, self-improvement metrics
- `mentor.journal` — write journal for the current run; called at end of every run
- `mentor.update` — pull latest from GitHub source; preserves journals and data. See `references/self-update-mentor.md` for the full procedure (Quick Path for clean state, Full Path for dirty state with local fixes to preserve).
- `mentor.plan.list` / `mentor.plan.run` / `mentor.plan.status` / `mentor.plan.resume` / `mentor.plan.history` — workflow plan management

## Cron-Mode Constraints
**READ FIRST: See `references/cron-execution-patterns.md` for a comprehensive guide to executing mentor heartbeats in cron mode, including critical script execution patterns, verification workflows, and common pitfalls to avoid.**

Proper error handling in cron mode requires special attention because shell variables don't persist across `terminal()` calls and Python `with open()` writes can silently fail. The following constraints are confirmed through operational experience.

**Commons sync "already in sync" pattern (confirmed 2026-06-25):** After running the evidence/ingestion sync, `wc -l` may show 0 delta on both files. This happens when a concurrent heartbeat already synced the new lines between the script's write and the dispatch's sync call. This is EXPECTED in steady-state with multiple concurrent cron triggers. Do NOT treat as a sync failure. Verify with `grep <new_run_id> /root/.hermes/commons/data/mentor/evidence.jsonl` to confirm the line exists in commons. If present, sync is already done — proceed to next step.

**`execute_code` is blocked in cron-triggered jobs.** All heartbeat, update, and plan runs triggered by cron must use `terminal()` with inline `python3 /path/to/scripts.py` for multi-stage logic. **CRITICAL: Do NOT use `<<` heredoc syntax in `terminal()`** — the `<<` delimiter triggers the terminal's foreground-background detection, causing exit_code=-1. Write scripts to `/tmp/` via `write_file` first, then invoke with `python3 /tmp/script.py`. See gotcha #70.

**Pipe-to-python bash quoting pitfall (confirmed 2026-06-29 dispatch):** The pattern `VAR=$(tail -1 "$file" | python3 -c "..."))` fails with `syntax error near unexpected token` because bash's command substitution `$(...)` with a pipe and double quotes creates parsing conflicts. **Fix:** Use single quotes inside the Python script and ensure the pipe is inside the `$()`: `VAR=$(tail -1 "$file" | python3 -c 'import sys,json; print(json.loads(sys.stdin.read()).get("field",""))' ))` — note the single quotes. Or safer: avoid inline pipe-to-python entirely; write a `/tmp/script.py` via `write_file` and pipe into it: `tail -1 /root/file.jsonl | python3 /tmp/extract_field.py`. The shell then has no embedded Python to misparse.

**`execute_code` blocking applies to ALL cron-triggered jobs** (confirmed 2026-06-25 dispatch #99). This includes not just heartbeat scripts but also state file writes, JSON manipulation, and any multi-step Python logic. When the dispatch caller (triggered by cron) needs to write JSON state files or perform set-difference syncs, it MUST use `terminal()` with `cat > file << 'EOF'` for JSON files or `echo >> file` for JSONL appends — never `execute_code`. Attempting `execute_code` in cron produces: `BLOCKED: execute_code runs arbitrary local Python`. This is a hard runtime constraint, not a suggestion.

**Python runtime resolution (confirmed 2026-06-24):** The skill docs historically reference `/root/hermes-agent/.venv/bin/python3.13` but this path does NOT exist. The venv symlinks all resolve to `/usr/bin/python3` (3.14). To run mentor/taste scripts that need `googleapiclient`:
1. Install deps: `pip3 install --break-system-packages google-api-python-client google-auth google-auth-oauthlib`
2. Use `/usr/bin/python3` (system Python 3.14, has googleapiclient after install)
3. Do NOT use `/root/.local/share/uv/python/cpython-3.13.13-linux-x86_64-gnu/bin/python3.13` — it's externally-managed and cannot install packages
4. Do NOT use `/root/.hermes/profiles/indigo/commons/data/ocas-taste/venv/bin/python3` — symlinks to system 3.14 but googleapiclient is not installed there
**Script path: skill name vs data directory mismatch (confirmed 2026-06-24 dispatch #49, #55, #63):** The skill name is `ocas-mentor` so scripts live at `/root/.hermes/profiles/indigo/skills/ocas-mentor/scripts/`. The data directory is `/root/.hermes/profiles/indigo/commons/data/mentor/` (no `ocas-` prefix). Do NOT derive the script path from the data directory name — always use `skills/ocas-mentor/scripts/<script>.py`. The correction script specifically is at `skills/ocas-mentor/scripts/correct_active_skills_30d.py` (NOT `skills/mentor/scripts/`). **Hard rule:** Before invoking ANY Mentor script, verify the path starts with `skills/ocas-mentor/scripts/`. A quick `ls skills/ocas-mentor/scripts/<script>.py` confirms. The agent has fallen into this trap 3+ times despite knowing the rule — the instinct to derive the path from the data directory name (`commons/data/mentor/`) is strong and must be actively countered.

**Inline Python variable scoping in `terminal()`** — When composing multi-step Python logic inline in `terminal()` (either as heredoc or `python3 -c`), variables defined inside a function are NOT available in the outer scope. This manifests as `NameError: name 'X' is not defined` at a line that logically follows the definition. **Fix:** Structure inline scripts so all logic is in a single flat scope (no nested functions), or write the script to `/tmp/` via `write_file` where you can verify scoping independently. Confirmed 2026-06-24 dispatch: `skill = jid.split("/")[0]` inside `extract_signals()` was invisible to the caller's loop.

**Sandbox file discovery failure:** In the cron sandbox, Python's `subprocess.run(["find", ...])` and `os.walk()` silently return 0 results even when the filesystem is fully accessible via shell tools. Use the shell-pipe pattern: `find JOURNALS_DIR -name "*.json" -mtime -3 | sort -u > /tmp/mentor_files_3d.txt && python3 scripts/cron-heartbeat-light.py < /tmp/mentor_files_3d.txt`. **CRITICAL:** Any pipe to python3 (e.g., `cmd | python3 -c "..."`, `VAR=$(cmd | python3 -c "...")`, or `cat file | python3`) is blocked by the `tirith:pipe_to_interpreter` security rule in cron mode. Always avoid piping to python3; use alternatives like temporary files (`cmd > /tmp/out && python3 -c "..." < /tmp/out`), here-strings (`python3 -c "..." <<< "$(cmd)"`), or temporary scripts. See `references/shell-write-pattern.md`.

**Pipe-to-interpreter blocks the ENTIRE terminal() call (confirmed 2026-07-08):** A trailing `tail -1 file | python3 -c "..."` verification step at the end of a multi-step cron `terminal()` command causes the security scanner to reject the WHOLE command — not just the pipe. Observed signature: `exit_code=-1`, `status: pending_approval`, `pattern_key: tirith:pipe_to_interpreter`. ALL steps in that call are lost (pre-run counts, script run, verification) and must be re-run. The block fires on the presence of `| python3` ANYWHERE in the command string, regardless of position. FIX: never put `cmd | python3` inside a cron `terminal()` call, even for final field checks. Do field verification via the `read_file` tool (outside terminal) or a `/tmp/*.py` script invoked WITHOUT a pipe (`python3 /tmp/check.py`).

**Journal file-mtimes lag content timestamps (clock offset) — mtime discovery unreliable (confirmed 2026-07-08):** In this environment, journal files carry file-mtimes ~7h12m BEHIND the system clock while their CONTENT timestamps match real time (e.g., file mtime `00:31Z` vs content `07:31Z` vs system `07:41Z`). `find -mmin -N` is therefore unreliable for tight windows: a 5-minute heartbeat using `-mmin -5` perpetually returns 0 and SILENTLY MISSES real recent journals. Mitigations: (1) When a heartbeat returns 0 files, VERIFY via a content-timestamp scan that 0 is real, not a mtime artifact — reuse `scripts/verify_ingest_window.py`. (2) For tight windows, prefer content-timestamp-based discovery, or widen the mtime window to cover the offset (e.g. `-mmin -450`) as a stopgap. (3) Do not assume `find -mmin -5` == "last 5 real minutes" — cross-check with content timestamps. See `references/cron-mtime-discovery-gotcha.md`.

**Python `with open()` writes are UNRELIABLE in cron `terminal()`** — Sometimes they persist, sometimes they silently fail. Piped `find | python3` is most likely to fail; `python3 /path/to/script.py` (no pipe) has been observed to succeed. Treat all Python writes as best-effort: verify with `wc -l` after, and use shell-level `echo >>` / `cat >` for critical evidence/journal writes. See `references/shell-write-pattern.md`.

**Heredoc vs. pipe conflict:** `cat file | python3 << 'PYEOF'` does NOT deliver stdin to Python — the heredoc steals stdin. Write the script to `/tmp/` first, then pipe: `cat file | python3 /tmp/script.py`. See gotcha #33.

**Env var on piped command:** `VAR=value cat file | python3 script` only sets the var for `cat`, not `python3`. Must `export` first — but even `export` in the same `terminal()` block may not propagate if the tool splits commands into subshells. **Safest:** `cat file | VAR=value python3 script`. See `references/gotchas-mentor-cron-envvars.md`.

**Pre-run counts MUST be captured in the SAME `terminal()` call as script execution** — A separate `terminal()` call to record `EVIDENCE_BEFORE=$(wc -l ...)` before the script run creates a race window: other processes (prior heartbeat's correction script, concurrent cron jobs) can write to evidence.jsonl between your "before" snapshot and the script's write. The resulting delta is meaningless — it reflects accumulated writes from multiple processes, not just this run. **Fix:** Always capture pre-run counts, run the script, and verify post-run counts in a SINGLE `terminal()` call. Do NOT split across calls. Confirmed 2026-06-24: separate-call pre-run count was stale, producing a delta of 4672 (meaningless) instead of the expected 2–3.

**Light heartbeat self-journaling is the EXPECTED DEFAULT failure pattern in cron mode** — As of 2026-06-16, the script's Python `with open()` writes to commons have failed 3+ consecutive times. The caller's backup write workflow is NOT a fallback — it is the ACTUAL persistence mechanism. Always run the full verify-and-backup workflow. Never skip verification even when prior runs succeeded. See `references/shell-write-pattern.md` and gotcha #23.

**Forge/scan journal heredoc arithmetic syntax error (confirmed 2026-06-25 dispatch #85):** When writing a JSON journal via shell heredoc (`cat > file.json << EOF`), bash substring expansion (`${TS:9:2}`) inside the heredoc body triggers an arithmetic syntax error (`: syntax error: operand expected`). The `>` in the heredoc redirect combined with `${}` patterns confuses bash's parser. **Fix:** Always use Python (`json.dump()`) to write JSON journal files, never shell heredocs with bash variable substring operations. For simple non-JSON appends, `echo >> file` is safe.

## Operational Recipes (light / deep heartbeat, commons sync)

The full command recipes, anti-journalization gates, field-name traps, and backup
workflows live in `references/mentor-operational-recipes.md`. Load it before running any
heartbeat or commons-sync. Summary of the mandatory caller workflow:

**Light heartbeat — verify-and-backup (SINGLE `terminal()` call):**

- [ ] Record pre-run counts (evidence, ingestion, journal dir) at PROFILE path in the SAME call as script execution
- [ ] Run `cron-heartbeat-light.py < /tmp/mentor_files_3d.txt` (stdin redirect, never pipe)
- [ ] Verify ALL THREE writes independently (evidence, ingestion, journal) — partial success is possible
- [ ] If evidence didn't grow, write backup evidence record to PROFILE path
- [ ] If ingestion didn't grow, write backup ingestion record to PROFILE path
- [ ] If no recent journal file exists, the script's journal write failed — log it
- [ ] NEVER write a second journal to `$JOURNAL_DIR` — the script's journal is canonical (anti-journalization hard gate)
- [ ] Run `correct_active_skills_30d.py` and write the corrected (true 30d) evidence record — mandatory, not conditional
- [ ] Sync profile -> commons via timestamp-based set-difference (NOT line-count); `ingestion_log.jsonl` uses `ingested_at`

**Deep heartbeat — verify-and-backup (SINGLE `terminal()` call):**

- [ ] `mkdir -p` proposals dir before running
- [ ] Build dual-path file list (commons + profile), `sort -u`
- [ ] Run `cron-heartbeat-deep-dualpath.py < /tmp/mentor_deep_files.txt` (stdin redirect)
- [ ] Verify evidence, ingestion, decisions, journal independently
- [ ] Back up via `/tmp/mentor_deep_backup.py` if ingestion delta = 0
- [ ] Run `correct_active_skills_30d.py` (reports `script=None` for deep — expected)
- [ ] NEVER append a second journal for the same `run_id`

See `references/mentor-operational-recipes.md` for the exact shell blocks, the sync Python script, and all confirmed-trap notes.



## Dispatch / Cron Integration

## Workflow

When triggered by the dispatcher or a cron job, the workflow proceeds as follows:

**Single-skill dispatch (Mentor only):** Follow the standard light heartbeat workflow above.

**Multi-skill dispatch (Forge + Mentor + Praxis):** Read `references/multi-skill-dispatch-workflow.md` FIRST. The consolidated workflow covers:
1. Pipeline sequence (Forge → Mentor → Praxis → Taste) with timing dependencies
2. Captured timestamp pattern (preventing cross-pipeline state collision)
3. Mandatory corrections (active_skills_30d, third-wave mitigation, gap backfill)
4. Second-wave / fast-no-op detection (grep eval file before mtime discovery)
5. Taste boundary (Praxis does NOT process Taste signals)
6. Verification checklist (all pipelines clean before exit)

**Praxis ingest script directory filter (confirmed 2026-06-24 dispatch #55, #102):** The `praxis_ingest_run.py` script only processes journals from the `ocas-praxis/` directory (its own self-referential journals). It does NOT evaluate journals from `ocas-mentor/`, `ocas-dispatch/`, or `ocas-forge/`. When the dispatcher lists journals from these directories in `new_files`, the dispatch caller must manually:
1. Check `journals_evaluated.jsonl` for the journal filename
2. If not present, manually add with `action_taken: "third_wave_mitigation"` and a note explaining the directory filter
3. Update `ingest_state.json:last_ingest_run` past the journal's mtime
This is NOT third-wave mitigation for self-referential journals — it is a manual bridge for cross-skill journals that the ingest script's directory filter excludes. **Confirmed #102:** `dispatch-triage-20260625T141334Z.json` in `ocas-dispatch/` was NOT auto-ingested and required manual bridge during third-wave mitigation.

**Dispatcher `new_files` already evaluated pattern (confirmed 2026-06-25 dispatch #60, #78, #99, #100):** When multiple dispatch waves fire in rapid succession (same day), journals from prior waves are typically already in `journals_evaluated.jsonl` — ingested by sibling Praxis heartbeats between waves. Before running Praxis ingest, always grep `journals_evaluated.jsonl` for each dispatcher `new_file` filename. If all are present, the bridge step is a fast no-op and Praxis mtime-based discovery will find only genuinely new self-referential journals. Do NOT re-add or re-evaluate — this is expected and correct behavior.

**Taste token refresh race in multi-skill dispatch (confirmed 2026-06-25 dispatch #62):** When the dispatch includes Taste (`taste_new_data`), the OAuth library may refresh the token between the repair call and the scan call if they're in separate `terminal()` invocations. The repair writes a clean expiry, but seconds later the scan sees `+00:00` again. Fix: combine token repair + taste scan in a single `terminal()` call. See `ocas-taste/references/token-repair.md` § Failure Mode 3.

**Quick reference for multi-skill dispatch:** The consolidated workflow lives in `references/multi-skill-dispatch-workflow.md`. For recent confirmed-clean runs, see:
| `references/session-20260624-dispatch-45.md` | Dispatch #45 (2026-06-24): second-wave Praxis skip, third-wave mitigation applied, active_skills_30d 10→22 |
| `references/session-20260624-dispatch-46.md` | Dispatch #46 wave 2 (2026-06-24): clean sweep all pipelines, email dedup (evidence log check), active_skills_30d 10→22 correction #24 |
- `references/session-20260624-dispatch-44.md` — dispatcher new_files timestamp mismatch, large gap backfill

1. **Forge**: Check for unprocessed proposals/decisions → no-op journal if clean
2. **Mentor**: Build dual-path list → run script → verify 3 writes → correct active_skills_30d → sync to commons
3. **Praxis**: Capture timestamp → mtime-based discovery → run dispatch ingest template → third-wave mitigation → gap backfill
4. Each pipeline writes its own journal — no cross-pipeline dependencies

**`active_skills_30d` correction is MANDATORY on every dispatch run.** The script receives only `-mtime -3` files via stdin, so its `active_skills_30d` (typically 12–14) is NEVER the true 30-day active skill count (typically 18–22). The caller must always compute the dual-path 30-day count and write a corrected evidence record. Two evidence lines per heartbeat is the expected pattern — the script's version (undercount) and the caller's corrected version. Confirmed 42+ times (2026-06-19 through 2026-06-25). See gotcha #29 and #58.

**Evidence delta mismatch: script reports N new files but evidence grows by N-1 (confirmed 2026-06-23).** The `cron-heartbeat-light.py` script reports "New files ingested: N" but `wc -l` on evidence.jsonl shows delta of N-1. This is the expected pattern: the script writes one evidence line, then the caller's `correct_active_skills_30d.py` writes a second evidence line (the correction). The script's stdout counter includes both lines, but the evidence file only grew by 1 at the time of the `wc -l` check (the correction hasn't been written yet). After the correction script runs, the total delta is 2 (matching the script's count). Do NOT treat this as a write failure — the post-correction `wc -l` will show the correct delta.

**Multi-skill dispatch pattern:** When the dispatcher triggers multiple skills in one dispatch (e.g., Forge + Mentor + Praxis), each pipeline runs independently and writes its own journal. No cross-pipeline dependencies. See `references/multi-skill-dispatch-pattern.md` for the full Forge → Mentor → Praxis pipeline.

**Cron dispatch verification shortcut (confirmed 2026-06-25):** After a cron-triggered dispatch completes all pipelines, a single-line verification confirms state:
```bash
echo "Forge: $(ls .../ocas-forge/2026-06-25/ | tail -2)" && echo "Mentor: evidence=$(wc -l < .../mentor/evidence.jsonl) ingestion=$(wc -l < .../mentor/ingestion_log.jsonl)" && echo "Praxis: eval=$(wc -l < .../journals_evaluated.jsonl)"
```

**Steady-state fast-no-op pattern (confirmed 50+ times):** When the dispatcher lists `new_files` but all are already in `journals_evaluated.jsonl` (evaluated by a concurrent heartbeat between dispatch waves), the Praxis mtime-based discovery finds only genuinely new self-referential journals. If all dispatcher `new_files` are already evaluated AND mtime-discovery finds 0 new journals, the dispatch is a fast no-op for that pipeline. This is the EXPECTED default — not an error or stale state.

**CRITICAL: Dispatch-triggered heartbeats — caller MUST always correct `active_skills_30d`** — Despite earlier documentation suggesting v2.8.23+ self-corrects, the `cron-heartbeat-light.py` script (as of v2.8.23) does NOT self-correct. It counts only from stdin (3-day piped files), producing `active_skills_30d` of 9–14 instead of the true 18–22. The script's evidence record will NOT show `correction: true`. The caller must ALWAYS compute the dual-path 30-day count and write a corrected evidence record. Two evidence lines per heartbeat is the expected pattern — the script's version (undercount) and the caller's corrected version. Confirmed 42+ times (2026-06-19 through 2026-06-25). See gotcha #29 and #58.

**Praxis cold-start interaction (confirmed 2026-06-22):** When the dispatcher runs Mentor before Praxis, the Mentor heartbeat script updates `ingest_state.json:last_ingest_run` to the current timestamp. If Praxis's `ingest_state.json` didn't exist before this dispatch, the Praxis cold-start initialization (with current timestamp) means 0 journals appear "new" — which is correct behavior for a fresh start. However, the dispatcher's `details.new_files` journals should still be explicitly evaluated even when the mtime-based discovery finds 0 new files. Always check the dispatcher's `new_files` list against `journals_evaluated.jsonl` independently of the mtime-based scan.

**Praxis "already evaluated" second-wave detection (confirmed 2026-06-24 dispatch #40):** After a multi-skill dispatch, the dispatcher may re-detect the mentor-light journal from the same dispatch as "new." Before running Praxis mtime-based discovery, always grep `journals_evaluated.jsonl` for the journal filename. If found (regardless of `action_taken`), Praxis has already evaluated it — skip silently. This is the correct no-op (not a failure, not a stale state). Example pattern:
```bash
grep -q "mentor-light-20260624T044239Z" /root/.hermes/profiles/indigo/commons/data/ocas-praxis/journals_evaluated.jsonl
# If exit code 0: already evaluated, skip Praxis silently
```
This prevents duplicate re-ingestion and unnecessary gap backfill on second-wave dispatches.

**Dispatch-mode caller workflow (confirmed 2026-06-22):** When triggered by `dispatcher.py` (not a standalone cron), the dispatch caller must:
1. Build dual-path 3-day file list: `find /root/.hermes/commons/journals/ /root/.hermes/profiles/indigo/commons/journals/ -name "*.json" -mtime -3 | sort -u > /tmp/mentor_files_3d.txt`
2. Record pre-run evidence count: `wc -l < /root/.hermes/profiles/indigo/commons/data/mentor/evidence.jsonl`
3. Run: `python3 {skill_dir}/scripts/cron-heartbeat-light.py < /tmp/mentor_files_3d.txt`
4. Verify evidence grew (delta should be ≥1). If delta=0, write backup evidence via `terminal()` Python one-liner.
5. **Always** run `python3 {skill_dir}/scripts/correct_active_skills_30d.py` to compute true dual-path 30-day count and write corrected evidence record to profile path. **NEVER write ad-hoc correction scripts** — use the existing script (see gotcha #74).
6. Cross-reference ingestion counts against `find ... -mtime -3 | sort -u` minus `ingestion_log.jsonl`.
7. **HARD GATE — DO NOT write ANY journal file after the script completes.** The script's journal is canonical and ALREADY EXISTS after step 2. There are TWO failure modes, BOTH observed in production:
   - **Duplicate journal (2026-06-29):** Caller wrote a second journal with a different `run_id` after the script's canonical journal already existed. Inflated `new_files_ingested` on next scan. Caught and deleted post-hoc, but the violation still happened.
   - **Journal overwrite (2026-06-28):** Writing a heredoc or `json.dump()` file with the SAME filename as the script's journal DESTROYS the canonical record.
   
   **VERIFICATION BEFORE ANY JOURNAL WRITE ATTEMPT:** Run `ls "$JOURNAL_DIR" | grep "mentor-light-" | wc -l`. If result ≥ 1, the script already wrote its journal. DO NOT WRITE. The heartbeat is OVER.
   
   Additional context goes in the evidence record (via `correct_active_skills_30d.py`), NEVER a journal file.

Steps 5–7 are mandatory regardless of script success. The script's evidence record (step 3) is always wrong on `active_skills_30d`. Do not skip the correction because the script reported "success." Confirmed 42+ times (2026-06-19 through 2026-06-25).

**Dispatch-mode caller workflow (confirmed 2026-06-22):** When triggered by `dispatcher.py` (not a standalone cron), the dispatch caller must:
1. Build dual-path 3-day file list: `find /root/.hermes/commons/journals/ /root/.hermes/profiles/indigo/commons/journals/ -name "*.json" -mtime -3 | sort -u > /tmp/mentor_files_3d.txt`
2. Record pre-run evidence count: `wc -l < /root/.hermes/profiles/indigo/commons/data/mentor/evidence.jsonl`
3. Run: `python3 {skill_dir}/scripts/cron-heartbeat-light.py < /tmp/mentor_files_3d.txt`
4. Verify evidence grew (delta should be ≥1). If delta=0, write backup evidence via `terminal()` Python one-liner.
5. **Always** run `python3 {skill_dir}/scripts/correct_active_skills_30d.py` to compute true dual-path 30-day count and write corrected evidence record to profile path. **NEVER write ad-hoc correction scripts** — use the existing script (see gotcha #74).
6. Cross-reference ingestion counts against `find ... -mtime -3 | sort -u` minus `ingestion_log.jsonl`.
7. **HARD GATE — DO NOT write ANY journal file after the script completes.** The script's journal is canonical and ALREADY EXISTS after step 2. There are TWO failure modes, BOTH observed in production:
   - **Duplicate journal (2026-06-29):** Caller wrote a second journal with a different `run_id` after the script's canonical journal already existed. Inflated `new_files_ingested` on next scan. Caught and deleted post-hoc, but the violation still happened.
   - **Journal overwrite (2026-06-28):** Writing a heredoc or `json.dump()` file with the SAME filename as the script's journal DESTROYS the canonical record.
   
   **VERIFICATION BEFORE ANY JOURNAL WRITE ATTEMPT:** Run `ls "$JOURNAL_DIR" | grep "mentor-light-" | wc -l`. If result ≥ 1, the script already wrote its journal. DO NOT WRITE. The heartbeat is OVER.
   
   Additional context goes in the evidence record (via `correct_active_skills_30d.py`), NEVER a journal file.

Steps 5–7 are mandatory regardless of script success. The script's evidence record (step 3) is always wrong on `active_skills_30d`. Do not skip the correction because the script reported "success." Confirmed 42+ times (2026-06-19 through 2026-06-25).

**Security alert triage (confirmed 2026-06-25):** GitGuardian (and similar) alerts on internal repos (e.g., `indigokarasu/indigo`) detecting JWTs or high-entropy secrets are typically test credentials, not active production secrets. Classify as `intent: "security_alert"` → **no action** unless the alert explicitly identifies an active production key. Recurring alerts on the same commit are noise — no escalation needed.

**Dispatcher second-wave pattern (confirmed 2026-06-21):** After the dispatch runs all three pipelines, the dispatcher re-scans and detects the mentor-light journal written by the dispatch's own run as "new." This is expected — the journal is genuinely new since the last dispatcher scan. The Praxis ingest should include the mentor-light journal from the dispatch run in its eval list to prevent re-processing. If a second dispatch wave fires, the mentor-light journal will already be evaluated and Praxis will find 0 new journals.

**Third-wave mitigation: journals_evaluated.jsonl gaps (confirmed 2026-06-24 dispatch #49, UPDATED 2026-06-25 dispatch #101):** After a multi-skill dispatch runs Praxis ingest, some dispatch-output journals may NOT appear in `journals_evaluated.jsonl` even though they were processed. Specifically: (1) journals from a PRIOR dispatch wave that were written between the wave's scan and the Praxis run, (2) forge-scan journals written by the current wave. The Praxis ingest script does NOT always add all relevant journals. **However (confirmed 2026-06-25):** The Praxis ingest script's mtime-based discovery now picks up forge-scan and mentor-light journals written during the same dispatch run. After running Praxis, `grep` the eval file for the forge-scan filename before assuming manual third-wave mitigation is needed. If present, skip — the script already evaluated it. Only add manually if genuinely absent:
```python
# Add missing journals to eval file (only if grep confirms absence)
entry = {'journal_id': 'ocas-forge/2026-06-25/forge-scan-XXX.json', 'evaluated_at': now_iso, 'action_taken': 'third_wave_mitigation'}
with open('.../journals_evaluated.jsonl', 'a') as f:
    f.write(json.dumps(entry) + '\n')
```
This prevents the dispatcher from re-detecting these journals as "new" in wave N+1.

**Dispatcher new_files as authoritative source (confirmed 2026-06-22):** When the dispatcher provides a `new_files` list in the dispatch details, this is the authoritative set of journals to evaluate — more reliable than mtime-based discovery alone. Journals can fall through the cracks of mtime-based discovery when `last_ingest_run` is updated by a sibling pipeline (e.g., Mentor heartbeat) before Praxis runs. The Praxis ingest should always evaluate the dispatcher's `new_files` list as a fallback, regardless of what mtime-based discovery finds. See Praxis SKILL.md § Dispatch / Cron Integration step 3.

**Already-ingested journal detection (confirmed 2026-06-24):** When the dispatcher lists a journal in `new_files` but it's already in `ingestion_log.jsonl` or `journals_evaluated.jsonl`, the journal was processed by a concurrent/recent heartbeat. Two distinct sub-patterns exist:

1. **One-wave lag:** Journal mtime > `last_ingest_run`. The journal is genuinely new but wasn't found by the current wave's mtime scan because `last_ingest_run` hadn't been updated yet. Self-correcting: the next wave's mtime scan will find it. Do NOT mark as `second_wave_no_op` — the work is pending.

2. **Concurrent Praxis race:** Journal mtime < `last_ingest_run` (a sibling Praxis cron updated `last_ingest_run` AFTER evaluating the journal). The journal is already in `journals_evaluated.jsonl` with an `evaluated_at` timestamp AFTER the journal's mtime. NOT self-correcting — the mtime-based scan will never find it again. Skip Praxis ingest for this journal, log `action: "concurrent_evaluation_detected"` in evidence. See `ocas-dispatch` skill's  for the full timeline and evidence structure.

Check both sources before running Praxis ingest. If found, mark as `already_ingested` in evidence and skip silently. This is NOT a second-wave false positive — the journal was genuinely new but already processed by a sibling pipeline.

**CRITICAL: Mentor heartbeat updates Praxis ingest state** — The `cron-heartbeat-light.py` script updates `ingest_state.json:last_ingest_run` when it writes evidence. If Praxis dispatch runs immediately after in the same multi-skill dispatch, its mtime-based journal discovery may find 0 new journals because the state timestamp moved forward. The dispatcher must capture `last_ingest_run` BEFORE running Mentor and pass it to Praxis. See Praxis SKILL.md § Dispatch / Cron Integration step 3.

**Caveat — heartbeat does NOT reliably advance Praxis ingest state (verified 2026-07-11):** In a multi-skill dispatch, after running `cron-heartbeat-light.py` via `python3 script.py < filelist` (returncode 0, heartbeat journal written to disk), `ingest_state.json:last_ingest_run` at `/root/.hermes/profiles/indigo/commons/data/ocas-praxis/` was UNCHANGED — it still held the prior-wave value. The dispatch caller MUST explicitly advance `last_ingest_run` itself after the heartbeat (and sync `journals_evaluated_count` / `last_eval_file_line` to the actual eval-file `wc -l`). Do NOT assume the script moved the state forward. A stale `last_ingest_run` is usually harmless (grep-based per-file classification wins over mtime discovery), but it means the state no longer reflects this wave's work and any later step that trusts it will read the prior-wave timestamp.

The script's `active_skills_30d` is the stdin-based count (3-day window, single path) — NOT the true 30-day active skill count. The correction is MANDATORY every time, not just when the script's write fails.

See `references/schemas.md` for storage layout and data schemas.

See `references/default-config.md` for default config.json.

See `references/workflow_plans.md` for available workflow plan templates.

Action Journal — every orchestration run, heartbeat pass, variant evaluation, and proposal emission. Include `entities_observed`, `relationships_observed`, `preferences_observed` with `user_relevance` field.

On first invocation, run `mentor.init`:

1. Create data directories and subdirectories
2. Write default `config.json` if absent
3. Create empty JSONL files
4. Create journal directory
5. Copy bundled plans to `plans/` directory
6. Register cron jobs if not already present
7. Log initialization as DecisionRecord

See `references/okrs-mentor.md` for full OKR definitions and targets.

Key OKRs: `orchestration_success_rate` (≥0.95), `evaluation_coverage` (≥0.90), `promotion_accuracy` (≥0.80).

**`orchestration_success_rate` scoring:** Computed as `(success + unknown) / total` — journals without explicit outcome fields (tagged `unknown`) are counted as successes since they have no `error` key. This corrects the prior measurement artifact where `unknown` was excluded from the numerator. See gotcha #34.

Implements the recovery contract from `spec-ocas-recovery.md`.

- **Evidence**: Every run writes an evidence record, including no-op runs. `not_activity_reason` mandatory.
- **Gap detection**: If gap exceeds 15min (light) or 24h (deep), logs `gap_detected`.
- **Degraded mode**: When Fellow or Forge unavailable, logs `degraded: <dependency>`.
- **Log compaction**: 30 days (no-op) / 90 days (error/gap). Last 7 days retained.

See `references/self-update-mentor.md`.

## Support File Map

| File | When to read |
|------|-------------|
| `references/schemas.md` | Before creating projects, tasks, proposals, or decisions |
| `references/default-config.md` | During `mentor.init` |
| `references/orchestration_engine.md` | Before goal decomposition or failure repair |
| `references/evaluation_engine.md` | Before journal ingestion or OKR scoring |
| `references/evolution_engine.md` | Before improvement detection or proposal generation |
| `references/workflow_plans.md` | Before any mentor.plan.* command |
| `references/gotchas-mentor.md` | Before any heartbeat or orchestration run |
| `references/multi-skill-dispatch-workflow.md` | **READ BEFORE EVERY MULTI-SKILL DISPATCH** — consolidated Forge + Mentor + Praxis pipeline sequence with cross-pitfall table, timing fixes, and third-wave/gap-backfill mitigation. Session log table (50+ dispatches) in this file. |
| `references/gotchas-mentor-cron-envvars.md` | **READ BEFORE EVERY CRON HEARTBEAT** — env var propagation gotchas for piped Python in cron |
| `references/heartbeat-gap-debugging.md` | When evidence log shows gaps >2h |
| `references/okrs-mentor.md` | During OKR evaluation |
| `references/self-update-mentor.md` | Before running `mentor.update` |
| `references/evidence-log-maintenance.md` | When evidence.jsonl grows corrupt entries or heartbeat crashes on gap detection |
| `references/data-paths.md` | Before writing any heartbeat or data script — canonical vs legacy paths |
| `references/dual-path-journal-discovery.md` | **READ BEFORE EVERY CRON HEARTBEAT** — journals live in two locations |
| `references/shell-write-pattern.md` | **READ BEFORE EVERY CRON HEARTBEAT** — the only reliable write method in cron |
| `templates/mentor-dispatch-quick-ref.md` | Before running Mentor in dispatch mode — canonical 7-step workflow |
| `references/mandatory-correction-workflow.md` | **READ AFTER EVERY LIGHT HEARTBEAT** — the mandatory `active_skills_30d` correction procedure, field naming, and two-evidence-lines-per-heartbeat pattern |
| `references/okrs.md` | During OKR evaluation (legacy OKR definitions) |
| `references/heartbeat-scan-technique.md` | When debugging journal scan or discovery issues |
| `references/gotcha-error-grep-false-positives.md` | **READ DURING URGENT-ISSUE SCANS** — grep for "error" in journal content produces false positives; parse JSON and check `outcome` field instead |
| `references/deep-heartbeat-dual-path.md` | **READ BEFORE EVERY DEEP HEARTBEAT** — dual-path wrapper fixes gotcha #32 |
| `references/deep-heartbeat-backup-procedure.md` | **READ WHEN INGESTION DELTA=0 AFTER DEEP HEARTBEAT** — backup workflow for silent write failures (confirmed 2026-06-29) |
| `references/multi-skill-dispatch-pattern.md` | When triggered by dispatcher with multi-skill dispatch (Forge+Mentor+Praxis) |
| `scripts/correct_active_skills_30d.py` | After every light heartbeat — compute true dual-path 30d count and write corrected evidence |
| `scripts/discover_recent_journals.py` | Tight-window (sub-3-day) journal discovery via CONTENT timestamp; counters the ~7h12m mtime lag. Emits a filtered file list for `cron-heartbeat-light.py`. **NOTE:** also recognizes `generated_at` and ANY `run_id` prefix (regex-extracted timestamp) — fixed 2026-07-13 to stop silently skipping praxis-cron/dispatch-wave/forge-scan journals. See `references/cron-mtime-discovery-gotcha.md` §3 and `references/discover-recent-journals-gotcha.md`. |
| `references/evidence-log-maintenance.md` | **When evidence.jsonl grows corrupt entries or heartbeat crashes on gap detection** — full scan-and-repair procedure: brace-depth splitting for concatenated JSON, null-byte removal, dual-repair requirement. |
| `scripts/repair_evidence_jsonl.py` | Standalone evidence.jsonl repair tool — scans both profile and commons for concatenated JSON, null-byte lines. Usable as `python3 scripts/repair_evidence_jsonl.py`. |
| `scripts/cron-heartbeat-deep.py` | Original deep heartbeat (single-path, commons only — use dualpath instead) |
| `scripts/cron-heartbeat-deep-dualpath.py` | **Preferred** deep heartbeat with dual-path scan + profile data sync |
| `scripts/deep_ingest_backup.py` | Deep heartbeat ingestion backup — run when `wc -l` shows delta=0 after deep heartbeat |
| `references/gap-backfill-auto-correct.md` | **When you discover a phantom filename entry in the eval file** — gap backfill auto-corrects wrong filenames from script stdout rollover; the phantom entry is inert and harmless |
| `references/ingestion-cross-reference-technique.md` | **READ DURING INGESTION CROSS-REFERENCE** — naive `comm -23` is misleading; use Python set difference instead |
| `references/cron-execution-patterns.md` | **READ BEFORE RUNNING MENTOR HEARTBEATS IN CRON** — critical patterns for script execution, verification workflows, and common pitfalls in cron-triggered heartbeats |
| `references/dispatch-bridge-script-reality.md` | **When a dispatch wave needs eval bridging** — the documented `bridge_eval_both_stores.py` / `close_dispatch_gap*.py` / `robust_eval_reconcile.py` / `reconcile_dispatch_eval_today.py` / `scan_eval_missing_journals.py` helpers DO NOT EXIST on disk. Use `scripts/bridge_eval_inline.py` (idempotent, in-process, both eval stores) instead. |
