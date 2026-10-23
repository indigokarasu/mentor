#!/usr/bin/env python3
"""Mentor project router: turn Mentor's project tags into kanban tasks for the owning skill.

Deterministic, no LLM. mentor:projects (an agent run) judges each project's status and the
skill that owns its next step and writes data/ocas-mentor/project-status.json. This script
hands that next step to the owning skill as a kanban task, which the kanban dispatcher runs
under the skill's own rules. Mentor itself never does the work.

Routed: status in-progress or active, route_to names an installed ocas-* skill, next_step set.
Never routed: waiting-on-<owner>, waiting-on-external, maintenance, complete, abandoned,
route_to "owner" or "none".
Each (project, next step) is routed once (state in data/ocas-mentor/routes.json, plus the
kanban idempotency key). At most MAX_NEW tasks per run, waiting work first by age.

Paths come from OCAS_COMMONS (default ~/.hermes/commons) and HERMES_SKILLS_DIR
(default ~/.hermes/skills). Usage: project_router.py [--dry-run]
"""
import hashlib
import json
import os
import subprocess
import sys
import time

COMMONS = os.environ.get("OCAS_COMMONS", os.path.expanduser("~/.hermes/commons"))
SKILLS = os.environ.get("HERMES_SKILLS_DIR", os.path.expanduser("~/.hermes/skills"))
PROFILE = os.environ.get("MENTOR_ROUTE_PROFILE", "default")
STATUS = os.path.join(COMMONS, "data/ocas-mentor/project-status.json")
ROUTES = os.path.join(COMMONS, "data/ocas-mentor/routes.json")
JOURNAL_DIR = os.path.join(COMMONS, "journals/ocas-mentor")
MAX_NEW = int(os.environ.get("MENTOR_ROUTE_MAX_NEW", "2"))
ROUTABLE = {"in-progress", "active"}

BODY = """Project: {name} (id {pid})
Mentor status: {status} since {since}
Why: {reason}

Do this next step, and only this: {next_step}

Rules:
- Work under the {skill} skill and follow all of its rules. For anything in the owner's own
  mailbox that means drafts in the original thread only; never send as the owner.
- Do not message the owner unless {skill}'s own rules call for it. Never invent facts for them
  (rates, availability, commitments).
- If the step needs the owner's decision or someone outside, stop and record that in {skill}'s
  journal instead of guessing; Mentor will re-tag the project.
- When done, write {skill}'s usual journal entry and include the line "project: {pid}" so Finch
  and Mentor can see the step finished.
Evidence: {evidence}
"""


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1)
    with open(tmp, encoding="utf-8") as f:
        json.load(f)
    os.replace(tmp, path)


def skill_installed(name):
    return name.startswith("ocas-") and os.path.isfile(os.path.join(SKILLS, name, "SKILL.md"))


def main():
    dry = "--dry-run" in sys.argv
    status = load(STATUS, {}).get("projects") or {}
    routes = load(ROUTES, {})
    picked, skipped = [], {}
    for pid, p in status.items():
        skill, step = (p.get("route_to") or "").strip(), (p.get("next_step") or "").strip()
        why = None
        if p.get("status") not in ROUTABLE:
            why = "status " + str(p.get("status"))
        elif not step:
            why = "no next step"
        elif not skill_installed(skill):
            why = "route_to " + (skill or "empty")
        key = "mentor:%s:%s" % (pid, hashlib.sha1(step.encode()).hexdigest()[:10])
        if not why and key in routes:
            why = "already routed"
        if why:
            skipped[why] = skipped.get(why, 0) + 1
            continue
        picked.append((p.get("since") or "", pid, p, skill, step, key))
    picked.sort()
    created = []
    for _, pid, p, skill, step, key in picked[:MAX_NEW]:
        title = "%s: %s" % (p.get("name") or pid, step)[:120]
        body = BODY.format(name=p.get("name") or pid, pid=pid, status=p.get("status"), since=p.get("since") or "?",
                           reason=p.get("reason") or "", next_step=step, skill=skill,
                           evidence=", ".join(p.get("evidence") or [])[:600] or "none")
        if dry:
            print("DRY", skill, "|", title)
            continue
        r = subprocess.run(["hermes", "-p", PROFILE, "kanban", "create", title, "--assignee", PROFILE,
                            "--skill", skill, "--idempotency-key", key, "--max-runtime", "30m",
                            "--max-retries", "2", "--created-by", "mentor:route", "--body-file", "-", "--json"],
                           input=body, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            print("FAILED", pid, r.stderr.strip()[:300], file=sys.stderr)
            continue
        try:
            task_id = json.loads(r.stdout).get("id")
        except ValueError:
            task_id = r.stdout.strip()[:40]
        routes[key] = {"project": pid, "skill": skill, "step": step, "task": task_id,
                       "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        created.append(routes[key])
    if not dry:
        save(ROUTES, routes)
        if created:
            os.makedirs(JOURNAL_DIR, exist_ok=True)
            save(os.path.join(JOURNAL_DIR, "route-%s.json" % time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())),
                 {"created": created, "skipped": skipped, "deferred": max(0, len(picked) - MAX_NEW)})
    print("routed %d, deferred %d, skipped %s" % (len(created) if not dry else min(len(picked), MAX_NEW),
                                                  max(0, len(picked) - MAX_NEW), skipped))


if __name__ == "__main__":
    main()
