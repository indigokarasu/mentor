# Project status and routing

Mentor is the OCAS control plane for projects. Finch observes and records what is in flight;
Mentor judges each project's status and decides which skill owns the next step; the owning skill
does the work. Mentor never does project work itself and never messages the owner.

## Data contract (all under the commons root)

| File | Written by | Read by |
|---|---|---|
| `data/ocas-finch/tracker.json` (+ `tracker.md`) | Finch (`finch:track`) | Mentor, Vesper |
| `data/ocas-mentor/project-status.json` | Mentor (`mentor:projects`) | Finch (for tracker.md), Vesper, the router |
| `data/ocas-mentor/routes.json` | `scripts/project_router.py` | the router |
| `journals/ocas-mentor/projects-*.json` | Mentor, one per run: status changes and why | Vesper, Finch |
| `journals/ocas-mentor/route-*.json` | the router: tasks created | Finch |

Each skill writes only its own folder, so no two jobs write the same file.

`project-status.json`:

```json
{"as_of": "ISO time",
 "projects": {"<finch project id>": {"name": "...", "status": "in-progress", "since": "ISO time",
   "reason": "one line", "next_step": "one line", "route_to": "ocas-dispatch",
   "evidence": ["session or journal references"]}}}
```

## Statuses (exactly one per project)

- `in-progress`: real work in the last 7 days.
- `active`: a live goal, nothing blocking, no work in the last 7 days.
- `maintenance`: shipped and running; upkeep only.
- `waiting-on-<owner>`: the next step needs the owner (decision, reply, approval, login, payment).
  Deployments name it after the owner.
- `waiting-on-external`: the next step belongs to someone outside (client, vendor, upstream, quota reset).
- `complete`: finished, with evidence.
- `abandoned`: the owner dropped it, or 30 days of silence with nothing pending.

The waiting states win over `in-progress`/`active`, so stuck work stays visible.
`route_to` is the OCAS skill that owns the next step (`ocas-dispatch`, `ocas-sands`, `ocas-custodian`,
`ocas-forge`, `ocas-voyage`, `ocas-rally`, ...), `owner`, or `none`.

## Routing (`scripts/project_router.py`, no LLM)

Runs after `mentor:projects`. For each project tagged `in-progress` or `active` whose `route_to` is an
installed `ocas-*` skill and that has a `next_step`, it creates one kanban task for the deployment's
profile with that skill loaded, an idempotency key of project id + hash of the step, a 30-minute runtime
cap and at most 2 retries. Each (project, step) is routed once; at most `MENTOR_ROUTE_MAX_NEW` (default 2)
new tasks per run. The task body tells the skill to follow its own rules, to stop and journal when the
owner or an outside party is needed, and to write `project: <id>` in its journal when the step is done,
which is how Finch and Mentor see it finish.

Environment: `OCAS_COMMONS` (default `~/.hermes/commons`), `HERMES_SKILLS_DIR` (default `~/.hermes/skills`),
`MENTOR_ROUTE_PROFILE` (default `default`), `MENTOR_ROUTE_MAX_NEW`. `--dry-run` prints what it would create.

## Tool limits

`mentor:projects` runs with file access and session search only, no MCP servers. The router is a
plain script. Neither touches email, calendar or Drive.
