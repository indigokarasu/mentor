# 🎓 Mentor

> **Multi-skill orchestration and self-improvement engine — the control plane for your agent.**

## Why Mentor?

When you have 26+ skills, someone needs to coordinate them. Mentor is the control plane: it decomposes goals into task graphs, supervises execution across skills, and dynamically repairs failures. In heartbeat mode, it reads journals from every skill, scores performance against baselines, and generates improvement proposals. It's the reason the OCAS suite works as a system instead of a pile of disconnected tools.

Skill packages follow the [agentskills.io](https://agentskills.io/specification) open standard and are compatible with OpenClaw, Hermes Agent, Claude, and any agentskills.io-compliant client.

## Quick Start

```
# Create a project
"Research the competitive landscape for AI calendar tools and write a summary"

# Check progress
"What's the status of my research project?"

# Run a workflow plan
"Run contact-enrichment for person_abc123"
```

Mentor auto-initializes on first use, including registering heartbeat and cron jobs.

## What It Does

Mentor operates in two modes. In **runtime mode** it decomposes goals into task graphs, supervises execution, and repairs failures through layered escalation. In **heartbeat mode** it reads journals from every skill, scores OKRs against baselines, and generates improvement proposals routed to Forge and Fellow. It also supports named **Workflow Plans** — pre-authored, parameterized task sequences invokable by name.

## Commands

| Command | Description |
|---|---|
| `mentor.project.create` | Create a project with goal and constraints |
| `mentor.project.status` | Current project state and task graph |
| `mentor.project.replan` | Trigger strategy-level replan |
| `mentor.task.list` | Tasks with statuses and dependencies |
| `mentor.heartbeat.light` | Lightweight pass: ingest journals, queue work |
| `mentor.heartbeat.deep` | Deep pass: full scoring, trend analysis, proposals |
| `mentor.plan.list` | List available workflow plans |
| `mentor.plan.run` | Execute a named workflow plan |
| `mentor.plan.status` | State of a running or recent plan |
| `mentor.plan.resume` | Continue a paused or failed plan |
| `mentor.plan.history` | Recent plan run summaries |
| `mentor.status` | Active projects, pending evaluations |
| `mentor.journal` | Write journal for the current run |
| `mentor.update` | Self-update from GitHub source |

## Dependencies

- [Forge](https://github.com/indigokarasu/forge) — receives VariantProposal/VariantDecision files
- [Fellow](https://github.com/indigokarasu/fellow) — runs controlled benchmark experiments
- [Elephas](https://github.com/indigokarasu/elephas) — Chronicle read-only for evaluation
- [Corvus](https://github.com/indigokarasu/corvus) — pattern data for anomaly context
- All skills — reads journals from all skills

## Workflow Plans

| Plan | Description |
|---|---|
| `contact-enrichment` | Enriches a Weave contact via Gmail + Scout + Sift |

## Scheduled Tasks

| Job | Schedule | Command |
|---|---|---|
| `mentor:deep` | `0 5 * * *` | Full OKR scoring, trend analysis, proposals |
| `mentor:light` | Every heartbeat | Ingest journals, update aggregates |
| `mentor:update` | `0 0 * * *` | Self-update |

## Changelog

### v2.6.6 — April 26, 2026
- Added Pitfalls — heartbeat execution journal-schema inconsistencies

### v2.3.0 — March 25, 2026
- Workflow Plans system, bundled contact-enrichment plan

### v2.0.0 — March 18, 2026
- Initial release

---

*Mentor is part of the [OCAS Agent Suite](https://github.com/indigokarasu).*