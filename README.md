# 👨‍🏫 Mentor

Long-running task orchestration and self-improving execution engine. Use when a task requires multi-step planning, sub-agent coordination, sequential or parallel task execution, failure recovery, or ongoing progress tracking across sessions. Picks up Triage-routed tasks with heartbeat intervals and works single-mindedly until complete. Runs at depth 1; spawns Sift and task workers at depth 2; task workers may spawn sub-workers at depth 3.

---

## 📖 Overview

Mentor is a core OCAS component. It decomposes complex goals into task graphs, supervises execution across skills, detects and repairs failures, and evaluates quality over time. During heartbeat cycles, Mentor analyzes journals, compares champion vs challenger variants, and proposes improvements. Mentor learns continuously, improving both individual skills and the orchestration ecosystem.

---

## 🔧 Tool Surface

- `mentor.project.create` — create a project with goal, constraints, output requirements
- `mentor.project.status` — current state, task graph, execution progress
- `mentor.project.replan` — trigger strategy-level replan
- `mentor.task.list` — all tasks with status, dependencies, blocking reasons
- `mentor.heartbeat.light` — update aggregates, queue work
- `mentor.heartbeat.deep` — full scoring, trend analysis, improvement proposals
- `mentor.variants.list` — active champion/challenger pairs with evaluation status
- `mentor.variants.decide` — emit promotion decision for a variant
- `mentor.proposals.list` — pending skill improvement proposals
- `mentor.proposals.create` — generate variant proposal for target skill
- `mentor.status` — active projects, pending evaluations, self-improvement metrics

---

## 📊 Output & Journals

Project execution logs, task records, evaluation reports, and skill improvement proposals. Champion/challenger comparison records.

---

## ⏱️ Heartbeat & Background Tasks

**Cron Heartbeat Registration** (NEW in 1.2.0): On first project creation, Mentor registers a named cron job (`mentor-heartbeat-<project_id>`) via `openclaw cron add`. Interval is sourced from the Triage signal. Cron job is removed on project completion.

**Continuous Evaluation & Evolution**: Light heartbeat (frequent) updates metrics and queues work. Deep heartbeat (periodic) performs full OKR scoring, variant pairing, anomaly detection, and generates improvement proposals. Mentor runs layer-by-layer failure repair: retry → alternate skill → split task → reorder → strategy escalation.

**Startup Sequence** (NEW in 1.2.0): Mandatory ordered steps on every invocation: depth verification, Triage signal read, existing project check, cron heartbeat registration, Triage acknowledgment.

---

## 🛠️ New in v1.2.0

- **Depth enforcement** — Mentor verifies it is running at depth 1 on startup
- **Cron heartbeat registration** — automatic heartbeat scheduling from Triage signals
- **Research gate** — spawns Sift sub-agents at depth 2 for knowledge gap filling
- **ResearchResult consumption** — reads and consolidates Sift outputs
- **Progress markers** — written after every unit of work for stall detection
- **Failure log** — prevents repeated attempts of excluded approaches
- **Sub-agent depth map** — explicit depth annotation (0=Triage, 1=Mentor, 2=Workers, 3=Sub-workers)

---

## 📚 Documentation

Read `SKILL.md` for operational details, schemas, and validation rules.

See `references/` for detailed specifications and examples.

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
