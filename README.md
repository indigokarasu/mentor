# ⚙️ Mentor

  <img src="./assets/readme/hero.jpg" width="100%" alt="Mentor">

Self-improving orchestration and evaluation engine. Manages long-running multi-skill workflows, analyzes journals from all skills, evaluates champion vs challenger variants, and proposes skill improvements to Forge. Use for multi-step project management, heartbeat runs, skill performance evaluation, or multi-skill coordination. NOT for: web research (use Sift), skill building (use Forge), user communication (use Dispatch), real-time skill execution, content generation, system health monitoring (use Custodian), or skill evaluation scoring.

**Skill name:** `ocas-mentor`
**Version:** 2.8.23
**Type:** 
**Layer:** software-development
**Author:** Indigo Karasu

---

## 📖 Overview

Self-improving orchestration and evaluation engine. Manages long-running multi-skill workflows, analyzes journals from all skills, evaluates champion vs challenger variants, and proposes skill improvements to Forge. Use for multi-step project management, heartbeat runs, skill performance evaluation, or multi-skill coordination. NOT for: web research (use Sift), skill building (use Forge), user communication (use Dispatch), real-time skill execution, content generation, system health monitoring (use Custodian), or skill evaluation scoring.

---

## 🔧 Capabilities

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
- `references/session-20260624-dispatch-44.md` — dispatcher new_files timestamp mismatch, large gap backfill

---

## 📊 Outputs

See `SKILL.md` for outputs, journals, and persistence rules.

---

## 📄 Files

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition |
| `references/` | Supporting documentation |
| `scripts/` | Helper scripts |


## Changelog

- [2.6.6] - 2026-04-26
- Added
- [2.6.5] - 2026-04-12
- Removed
- [2026-04-04] Spec Compliance Update
- Changes
- Validation
- [2.6.1] - 2026-04-08

---

## 📚 Documentation

Read `SKILL.md` for operational details, schemas, and validation rules.

Read `references/` for detailed specifications and examples.


---

## 📄 License

MIT License — see `LICENSE` for details.
