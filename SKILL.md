---
license: MIT
name: ocas-mentor
description: 'Self-improving orchestration and evaluation engine. Manages long-running multi-skill workflows, analyzes journals from all skills, evaluates champion vs challenger variants, and proposes skill improvements to Forge. Use for multi-step project management, heartbeat runs, skill performance evaluation, or multi-skill coordination. Keywords: self-improving orchestration, multi-skill workflow, skill evaluation, heartbeat, OKR scoring, variant evaluation, proposal generation, cron heartbeats, dispatch pipelines. NOT for: web research (use Sift), skill building (use Forge), user communication (use Dispatch), real-time skill execution, content generation, system health monitoring (use Custodian), or skill evaluation scoring.'
source: https://github.com/indigokarasu/mentor
includes:
- references/**
- scripts/**
metadata:
  author: Indigo Karasu (indigokarasu)
  version: "2.10.0"
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


**Support files:** `references/support-file-map.md` indexes the bundled files not covered inline in this skill — check it before working from assumptions about what is (not) available.

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
- `mentor.projects.tag` — tag every project Finch records (in-progress, active, maintenance, waiting-on-<owner>, waiting-on-external, complete, abandoned) with reason, next step and owning skill; see `references/project-status.md`
- `mentor.projects.route` — `scripts/project_router.py`: hand the next step of in-progress/active projects to the owning skill as a kanban task (no LLM, deduplicated, capped per run)
- `mentor.task.list` — tasks with statuses, dependencies, blocking reasons
- `mentor.heartbeat.light` — lightweight pass: ingest journals, update aggregates, queue work
- `mentor.heartbeat.deep` — deep pass: full scoring, trend analysis, proposals
- `mentor.variants.list` — active champion/challenger pairs with evaluation status
- `mentor.variants.decide` — emit promotion decision for a variant
- `mentor.proposals.list` — pending skill improvement proposals
- `mentor.proposals.create` — generate a VariantProposal for a target skill
- `mentor.status` — active projects, pending evaluations, self-improvement metrics
- `mentor.journal` — write journal for the current run; called at end of every run
- `mentor.update` — pull latest from GitHub source; preserves journals and data. Skill updates now run through the centralized fleet updater (`scripts/update_skill.sh`, invoked by the `skills:update-fleet` cron). See that script for the Quick/Full path procedure.
- `mentor.plan.list` / `mentor.plan.run` / `mentor.plan.status` / `mentor.plan.resume` / `mentor.plan.history` — workflow plan management

## Cron-Mode Constraints

**READ FIRST:** See `references/cron-mode-constraints.md` (full list of confirmed operational constraints for cron mode) and `references/cron-execution-patterns.md` (canonical heartbeat workflow). The constraints below are reproduced in the reference file and confirmed through operational experience.



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
- [ ] Build dual-path file list (commons + profile), `sort -u` → `/tmp/mentor_deep_files.txt` (needed by `deep_ingest_backup.py`, NOT by the run itself)
- [ ] Run `cron-heartbeat-deep-dualpath.py` (standalone — **it IGNORES stdin**; `main()` calls `os.walk()` over both `JOURNALS_PATHS` internally. The `< /tmp/mentor_deep_files.txt` redirect is a harmless no-op, not a scoping input. Confirmed 2026-07-16: 30,740 journals scanned with no stdin fed.)
- [ ] Verify evidence, ingestion, decisions, journal independently
- [ ] Back up via `/tmp/mentor_deep_backup.py` if ingestion delta = 0
- [ ] Run `correct_active_skills_30d.py` (reports `script=None` for deep — expected)
- [ ] NEVER append a second journal for the same `run_id`

See `references/mentor-operational-recipes.md` for the exact shell blocks, the sync Python script, and all confirmed-trap notes.




## Examples

### Example 1 — Light heartbeat (cron)
**Input:** file list from `discover_recent_journals.py` (`/tmp/mentor_files_3d.txt`):
`~/.hermes/commons/journals/ocas-forge/2026-07-14/forge-scan-20260714T060000Z.json`
`~/.hermes/commons/journals/ocas-mentor/2026-07-14/mentor-light-20260714T060026Z.json`

**Command:**
```bash
python3 scripts/cron-heartbeat-light.py < /tmp/mentor_files_3d.txt
```

**Expected:** `Cron heartbeat wrote 1 evidence record, 1 ingestion record, 1 journal.` (verify each file with `wc -l`, not just the script's stdout).

### Example 2 — active_skills_30d correction (every heartbeat)
**Input:** light heartbeat evidence record with `active_skills_30d: 11`.
**Command:** `python3 scripts/correct_active_skills_30d.py`
**Expected:** true 30-day count (e.g. `20`) plus a second evidence record with `correction: true`.

### Example 3 — Deep heartbeat: ingestion delta = 0
1. Run `cron-heartbeat-deep-dualpath.py`.
2. Verify `wc -l` on `ingestion_log.jsonl` delta = 0.
3. If delta = 0: run `deep_ingest_backup.py`, then `mentor_sync_commons.py`.

## Error Handling

| Failure mode | Handling |
|---|---|
| `tirith:pipe_to_interpreter` blocks the whole `terminal()` call | Rewrite as stdin redirect (`python3 script.py < file`) or a `/tmp/*.py` script; never `cmd \| python3` |
| `execute_code` blocked in cron-triggered jobs | Use `terminal()` with inline `python3 /path/to/scripts.py` |
| Evidence write returns 0 delta but script exited 0 | Re-run the full verify-and-backup workflow; check the sync script's exit code, not just stdout |
| Journal already exists for the run_id | Do NOT write a second journal; the script's journal is canonical |
| `active_skills_30d` undercount (9-14, not 18-22) | Always run `correct_active_skills_30d.py` and write the corrected evidence record |
| `wc -l` shows 0 delta after sync (concurrent heartbeat) | Verify with `grep <new_run_id> evidence.jsonl`; if present, sync is already done |
| Journal file-mtimes lag content timestamps ~7h12m | Use `discover_recent_journals.py` (content-timestamp) for tight windows; widen mtime window otherwise |
| `with open()` write silently fails in cron | Verify with `wc -l`; use `cat >`/`echo >>` for critical writes |
| Heredoc `${TS:9:2}` arithmetic error | Use `json.dump()` for JSON; `echo >>` for non-JSON appends |
| Outcome misclassified (list-of-dicts `errors` treated as failure) | Use `_reports_failure()` shape check, not field presence |

## Gotchas / Pitfalls

- Cron-mode constraints are enumerated in `references/cron-mode-constraints.md`; read them before every heartbeat.
- Outcome classification must read the *shape* of a field (`_reports_failure`), not its presence — an `errors` list-of-dicts findings report is not a failed run (10 of 38,436 entries; fixed 2026-09-30).
- `active_skills_30d` is ALWAYS an undercount at the script level; the caller MUST always correct it.
- The script's journal is canonical: never write a second journal for the same `run_id`.
- Journal file-mtimes lag content timestamps by ~7h12m; `find -mmin` is unreliable for tight windows.
- For the full chronological log of confirmed pitfalls, see `references/gotchas-mentor.md`.
## Dispatch / Cron Integration

When triggered by the dispatcher or a cron job, follow the consolidated workflow in
`references/multi-skill-dispatch-workflow.md` (Forge → Mentor → Praxis pipeline,
timing, third-wave mitigation, gap backfill). The full caller workflow, second-wave /
third-wave mitigation details, and recovery contract are in
`references/dispatch-cron-integration.md`.

**Quick reference:**
1. Forge: check for unprocessed proposals/decisions → no-op journal if clean
2. Mentor: build dual-path list → run script → verify 3 writes → correct `active_skills_30d` → sync to commons
3. Praxis: capture timestamp → mtime-based discovery → run dispatch ingest → third-wave mitigation → gap backfill
4. Each pipeline writes its own journal — no cross-pipeline dependencies

**`active_skills_30d` correction is MANDATORY on every run** (because the script counts only stdin (3-day window, single path), undercounting; caller computes dual-path 30-day count). See gotcha #29/#58 and `references/mandatory-correction-workflow.md`.

**Recovery contract** (from `spec-ocas-recovery.md`): every run writes an evidence record (incl. no-ops, with `not_activity_reason`); gap detection at 15min (light) / 24h (deep); degraded mode logs `degraded: <dependency>`; log compaction 30d (no-op) / 90d (error/gap), last 7 days retained.

**Support files:** `references/support-file-map.md` indexes the bundled files (with a "When to read" column) not covered inline — check it before working from assumptions about what is (not) available.

