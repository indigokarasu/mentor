# 👨‍🏫 Mentor

Mentor is the control plane for autonomous work. It decomposes complex goals into task graphs, supervises execution across skills, detects and repairs failures, and evaluates quality over time. During heartbeat cycles, Mentor analyzes journals, compares champion vs challenger variants, and proposes improvements. Mentor learns continuously, improving both individual skills and the orchestration ecosystem.

---

## 📖 Overview

Self-improving orchestration and evaluation engine for long-running multi-skill workflows. Analyzes journals, evaluates variants, and proposes skill improvements.

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

Produces: Produces project execution logs, task records, evaluation reports, and skill improvement proposals. Maintains champion/challenger comparison records.

---

## ⏱️ Heartbeat & Background Tasks

**Continuous Evaluation & Evolution**: Light heartbeat (frequent) updates metrics and queues work. Deep heartbeat (periodic) performs full OKR scoring, variant pairing, anomaly detection, and generates improvement proposals. Mentor runs layer-by-layer failure repair: retry → alternate skill → split task → reorder → strategy escalation.

---

## 📚 Documentation

Read `SKILL.md` for operational details, schemas, and validation rules.

See `references/` for detailed specifications and examples.

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
