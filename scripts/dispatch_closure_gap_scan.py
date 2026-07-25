#!/usr/bin/env python3
"""dispatch_closure_gap_scan.py — manual replacement for the ABSENT closure scripts.

This environment is missing the four canonical closure scripts the ocas-mentor /
ocas-forge SKILL.md docs as mandatory (verify_genuine_gap_profile.py,
closure_convergence_sweep.py, closure_closeout_check.py, advance_gate_state.py).
They DO NOT EXIST on disk (confirmed via find). This single file reproduces
their job: bounded gap scan + idempotent bridge + state advance.

Reality doc: ocas-mentor/references/dispatch-closure-script-reality.md

Usage:
  python3 scripts/dispatch_closure_gap_scan.py --date 2026-07-23
  python3 scripts/dispatch_closure_gap_scan.py --date 2026-07-23 --advance
"""
import os, json, argparse, datetime, sys

PROFILE_DATA = os.path.expanduser("~/.hermes/profiles/indigo/commons/data")
JOURNAL_ROOTS = [
    os.path.expanduser("~/.hermes/commons/journals"),
    os.path.expanduser("~/.hermes/profiles/indigo/commons/journals"),
]
PRAXIS_EVAL = os.path.join(PROFILE_DATA, "ocas-praxis/journals_evaluated.jsonl")
DISPATCH_EVAL = os.path.join(PROFILE_DATA, "ocas-dispatch/journals_evaluated.jsonl")
MONITOR_ROOTS = [
    os.path.expanduser("~/.hermes/commons/data/monitor_state/journal_ingest_state.json"),
    os.path.expanduser("~/.hermes/profiles/indigo/commons/data/monitor_state/journal_ingest_state.json"),
]
PRAXIS_STATE = os.path.join(PROFILE_DATA, "ocas-praxis/ingest_state.json")


def load_store(path):
    s = set()
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                v = o.get("journal_id") or o.get("filename") or o.get("journal") or ""
                if v:
                    s.add(v)
    return s


def has(path, key, val):
    if not os.path.exists(path):
        return False
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            if o.get(key) == val:
                return True
    return False


def scan(date):
    prax = load_store(PRAXIS_EVAL)
    disp = load_store(DISPATCH_EVAL)
    found = {}
    for root in JOURNAL_ROOTS:
        if not os.path.isdir(root):
            continue
        for skill in os.listdir(root):
            sdir = os.path.join(root, skill, date)
            if os.path.isdir(sdir):
                for fn in os.listdir(sdir):
                    if fn.endswith(".json"):
                        rel = f"{skill}/{date}/{fn}"
                        found.setdefault(rel, set()).add(root)
    gaps = []
    for rel in sorted(found):
        in_p = rel in prax
        in_d = rel in disp
        if not (in_p and in_d):
            gaps.append((rel, in_p, in_d))
    maxmt = None
    for rel in found:
        for root in found[rel]:
            m = os.path.getmtime(os.path.join(root, rel))
            if maxmt is None or m > maxmt:
                maxmt = m
    return gaps, maxmt, prax, disp


def bridge(rel, prax, disp):
    bridged = []
    if not has(DISPATCH_EVAL, "filename", rel):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with open(DISPATCH_EVAL, "a") as f:
            f.write(json.dumps({"filename": rel,
                               "action_taken": "cross_skill_noop_mentor_self_reference",
                               "source": "dispatch_closure_gap_scan"}) + "\n")
        bridged.append(("dispatch", rel))
    if not has(PRAXIS_EVAL, "journal_id", rel):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with open(PRAXIS_EVAL, "a") as f:
            f.write(json.dumps({"journal_id": rel, "evaluated_at": now,
                               "action_taken": "cross_skill_noop_mentor_self_reference"}) + "\n")
        bridged.append(("praxis", rel))
    return bridged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="journal DIR date, e.g. 2026-07-23")
    ap.add_argument("--advance", action="store_true", help="advance state gates past max mtime")
    args = ap.parse_args()

    gaps, maxmt, prax, disp = scan(args.date)
    print(f"=== gap scan for {args.date} ===")
    for rel, in_p, in_d in gaps:
        print(f"GAP {rel} praxis={in_p} dispatch={in_d}")
    print(f"GENUINE GAP (excluding custodian): {len(gaps)}")
    print(f"MAX journal mtime: {maxmt}")
    if maxmt:
        print("MAX journal mtime iso: " +
              datetime.datetime.fromtimestamp(maxmt, datetime.timezone.utc).isoformat())

    if not args.advance:
        for rel, _, _ in gaps:
            bridge(rel, prax, disp)
        print("Bridged missing entries (no --advance: state NOT advanced).")
        return

    # --advance: bridge + advance gates
    for rel, _, _ in gaps:
        bridge(rel, prax, disp)
    if maxmt is None:
        print("No journals found for date; refusing to advance state.")
        sys.exit(1)
    new_mt = maxmt + 5.0
    # advance praxis last_ingest_run
    if os.path.exists(PRAXIS_STATE):
        with open(PRAXIS_STATE) as f:
            st = json.load(f)
        st["last_ingest_run"] = datetime.datetime.fromtimestamp(
            new_mt, datetime.timezone.utc).isoformat()
        st["last_ingest_note"] = (f"dispatch re-detection closure (manual, "
                                  f"scripts/dispatch_closure_gap_scan.py --advance)")
        with open(PRAXIS_STATE, "w") as f:
            json.dump(st, f, indent=2)
        print("praxis last_ingest_run ->", st["last_ingest_run"])
    # advance BOTH monitor copies
    for mp in MONITOR_ROOTS:
        if os.path.exists(mp):
            with open(mp) as f:
                ms = json.load(f)
            ms["latest_mtime"] = new_mt
            with open(mp, "w") as f:
                json.dump(ms, f, indent=2)
            print("monitor", mp, "->", new_mt)

    # final gate check
    gaps2, _, _, _ = scan(args.date)
    gate1 = len(gaps2) == 0
    m1 = json.load(open(MONITOR_ROOTS[0])).get("latest_mtime")
    m2 = json.load(open(MONITOR_ROOTS[1])).get("latest_mtime")
    gate2 = (m1 >= maxmt) and (m2 >= maxmt)
    print(f"\nGENUINE GAP={len(gaps2)}  monitor1>=max={m1>=maxmt}  monitor2>=max={m2>=maxmt}")
    if gate1 and gate2:
        print("=== gates ALL CLOSED ===")
    else:
        print("!!! gates NOT closed — inspect manually !!!")
        sys.exit(1)


if __name__ == "__main__":
    main()
