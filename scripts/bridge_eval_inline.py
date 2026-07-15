#!/usr/bin/env python3
"""
bridge_eval_inline.py — Working, in-process replacement for the MISSING
bridge_eval_both_stores.py (and the rest of the documented-but-absent
close/bridge helper scripts in ocas-mentor).

WHY THIS EXISTS (verified 2026-07-14): a filesystem search of
skills/ocas-mentor/scripts/ and the whole skills tree found NONE of the
bridge/close helpers the SKILL.md references (bridge_eval_both_stores.py,
close_dispatch_gap.py, robust_eval_reconcile.py, close_gap_profile.py,
verify_genuine_gap_independent.py, bridge_dispatch_eval_one_sided.py,
reconcile_dispatch_eval_today.py, verify_genuine_gap_profile.py,
close_dispatch_gap_finalizer.py). The doc's present-tense "Reusable helper"
claims are stale. Use this script instead.

WHAT IT DOES: bridges one or more journal relative paths into BOTH
authoritative eval stores in one idempotent, in-process pass (NO shell pipe
to python3 — cron-safe):

  commons/data/ocas-dispatch/journals_evaluated.jsonl  (key: "filename")
  commons/data/ocas-praxis/journals_evaluated.jsonl    (key: "journal_id")

Paths are relative to commons/journals/ — e.g.
  "ocas-mentor/2026-07-14/mentor-light-20260714T064026Z.json"

Membership is keyed on the FULL relative path (basename-only checks miss).
Idempotent: entries already present (full-path match) are skipped.

USAGE:
  python3 scripts/bridge_eval_inline.py <rel_path> [<rel_path2> ...] [--action <label>]

Default action_taken: "post_dispatch_cleanup".
"""
import json
import sys
import os
from datetime import datetime, timezone

BASE = "/root/.hermes/profiles/indigo"
DISP = os.path.join(BASE, "commons/data/ocas-dispatch/journals_evaluated.jsonl")
PRAX = os.path.join(BASE, "commons/data/ocas-praxis/journals_evaluated.jsonl")


def load_membership(path, key):
    s = set()
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                v = e.get(key)
                if v:
                    s.add(v)
    return s


def main(argv):
    action = "post_dispatch_cleanup"
    rels = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--action":
            if i + 1 < len(argv):
                action = argv[i + 1]
            i += 2
            continue
        rels.append(a)
        i += 1
    if not rels:
        print("usage: bridge_eval_inline.py <rel_path> [..] [--action <label>]")
        return 2
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    disp_set = load_membership(DISP, "filename")
    prax_set = load_membership(PRAX, "journal_id")

    n_d = n_p = 0
    with open(DISP, "a") as fd, open(PRAX, "a") as fp:
        for rel in rels:
            if rel not in disp_set:
                fd.write(json.dumps({
                    "filename": rel,
                    "action_taken": action,
                    "bridged_at": ts,
                    "source": "bridge_eval_inline",
                }) + "\n")
                disp_set.add(rel)
                n_d += 1
            if rel not in prax_set:
                fp.write(json.dumps({
                    "journal_id": rel,
                    "action_taken": action,
                    "bridged_at": ts,
                    "source": "bridge_eval_inline",
                }) + "\n")
                prax_set.add(rel)
                n_p += 1
    print(f"dispatch eval appended: {n_d}")
    print(f"praxis eval appended: {n_p}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
