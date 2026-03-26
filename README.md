# 🎓 Mentor

Mentor is the system's control plane -- in runtime mode it decomposes goals into task graphs, supervises execution across skills, and dynamically repairs failures through a layered escalation policy from local retry up to full strategy replan. In heartbeat mode it reads journals from every skill, scores OKR performance against baselines, and generates improvement proposals that flow to Forge and Fellow for empirical evaluation and promotion.

---

## Overview

Mentor operates in two modes that share state and telemetry. In runtime mode it acts as an orchestration engine -- decomposing goals into task graphs, supervising execution across skills, and repairing failures through a layered escalation policy from local retry up to full strategy replan. In heartbeat mode it reads journals from every skill, scores OKRs against baselines, generates improvement proposals that go to Forge for building, and routes experiments to Fellow for empirical evaluation. Together these modes form a self-improving control plane. Mentor and Elephas are parallel journal consumers -- neither blocks the other.

## Commands

| Command | Description |
|---|---|
| `mentor.project.create` | Create a project with goal, constraints, and requested output |
| `mentor.project.status` | Current project state, task graph, execution progress |
| `mentor.project.replan` | Trigger strategy-level replan |
| `mentor.task.list` | Tasks with statuses, dependencies, blocking reasons |
| `mentor.heartbeat.light` | Lightweight pass: ingest journals, update aggregates, queue work |
| `mentor.heartbeat.deep` | Deep pass: full scoring, trend analysis, proposals |
| `mentor.variants.list` | Active champion/challenger pairs with evaluation status |
| `mentor.variants.decide` | Emit promotion decision for a variant |
| `mentor.proposals.list` | Pending skill improvement proposals |
| `mentor.proposals.create` | Generate a VariantProposal for a target skill |
| `mentor.status` | Active projects, pending evaluations, self-improvement metrics |
| `mentor.journal` | Write journal for the current run |

## Setup

`mentor.init` runs automatically on first invocation and creates all required directories, config.json, and JSONL files. It also registers the `mentor:deep` cron job (daily 5am) and the `mentor:light` heartbeat entry. No manual setup is required.

## Dependencies

**OCAS Skills**
- [Forge](https://github.com/indigokarasu/forge) -- receives VariantProposal and VariantDecision files via intake directory
- [Fellow](https://github.com/indigokarasu/fellow) -- invoked to run controlled benchmark experiments
- [Elephas](https://github.com/indigokarasu/elephas) -- Chronicle read-only for evaluation context
- [Corvus](https://github.com/indigokarasu/corvus) -- pattern data for anomaly context
- All skills -- reads journals from all skills for evaluation

**External**
- None

## Scheduled Tasks

| Job | Mechanism | Schedule | Command |
|---|---|---|---|
| `mentor:deep` | cron | `0 5 * * *` (daily 5am) | Full OKR scoring, trend analysis, variant proposals |
| `mentor:light` | heartbeat | Every heartbeat pass | Ingest journals, update aggregates, queue work |

## Changelog

### v2.2.0 -- March 22, 2026
- Routing improvements

### v2.1.0 -- March 22, 2026
- Run completion with Forge intake integration
- Initialization with cron and heartbeat registration
- Background task definitions

### v2.0.0 -- March 18, 2026
- Initial release as part of the unified OCAS skill suite
---

*Mentor is part of the [OpenClaw Agent Suite](https://github.com/indigokarasu) -- a collection of interconnected skills for personal intelligence, autonomous research, and continuous self-improvement. Each skill owns a narrow responsibility and communicates with others through structured signal files, shared journals, and Chronicle, a long-term knowledge graph that accumulates verified facts over time.*
