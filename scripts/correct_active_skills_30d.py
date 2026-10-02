#!/usr/bin/env python3
"""Correct active_skills_30d in Mentor light heartbeat evidence records.

The cron-heartbeat-light.py script computes active_skills_30d from stdin (3-day, single-path),
which always undercounts. This script computes the true dual-path 30-day count and appends
a corrected evidence record.

Usage:
    python3 correct_active_skills_30d.py
    (Run after every light heartbeat, before journal write)

Output:
    Appends one corrected evidence record to {MENTOR_DATA}/evidence.jsonl
    Prints the corrected count to stdout.
"""
import os, json, time
from datetime import datetime, timezone
import sys

_HELP_ARGS = {"--help", "-h"}
if set(sys.argv[1:]) & _HELP_ARGS:
    print((__doc__ or "").strip() or "Usage: python3 correct_active_skills_30d.py")
    sys.exit(0)

AGENT_ROOT = os.path.expanduser("~/.hermes/profiles/indigo")
MENTOR_DATA = os.path.join(AGENT_ROOT, "commons", "data", "mentor")
EVIDENCE_LOG = os.path.join(MENTOR_DATA, "evidence.jsonl")
JOURNALS_DIRS = [
    os.path.expanduser("~/.hermes/commons/journals"),
    os.path.expanduser("~/.hermes/profiles/indigo/commons/journals"),
]


JOURNAL_SUFFIXES = (".jsonl", ".json", ".jsonl.gz", ".json.gz")
WINDOW_DAYS = 30


def _active_skill_names(window_days=WINDOW_DAYS):
    """Unique skill dirs holding a journal modified within the window.

    Walks Python-side rather than shelling out to `find -name '*.json' | grep -oP`:
    that pipeline (a) ignored JOURNAL_DIRS entirely, (b) could not see `.json.gz`,
    which Genie creates when it compresses journals older than its age threshold, and
    (c) counted root-level files as skills. A gz-only skill counted as zero active.
    """
    cutoff = time.time() - window_days * 86400
    names = set()
    for base in JOURNALS_DIRS:
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fn in files:
                if not fn.endswith(JOURNAL_SUFFIXES):
                    continue
                # Resolve the owner per FILE, not per directory: ownership is the first
                # component of the path relative to base. A file sitting directly in a
                # skill dir (ocas-genie/runs.jsonl) is owned by that skill even though
                # the walk dir itself is only one component deep. Files at the journals
                # root (dispatch-wave-*.json.gz, journals_evaluated.jsonl) are len 1 and
                # have no owner.
                rel = os.path.relpath(os.path.join(root, fn), base).split(os.sep)
                if len(rel) < 2 or not rel[0] or rel[0].startswith("."):
                    continue
                try:
                    if os.path.getmtime(os.path.join(root, fn)) >= cutoff:
                        names.add(rel[0])
                except OSError:
                    continue
    return names


def count_active_skills_30d():
    """Count unique skill names across both journal paths, 30-day window."""
    return len(_active_skill_names())


def count_active_skills_30d_ocas():
    """Count OCAS-only skills across both journal paths, 30-day window."""
    return len({n for n in _active_skill_names() if n.startswith("ocas-")})


def get_last_script_30d():
    """Read the last evidence record's active_skills_30d (what the script reported)."""
    if not os.path.exists(EVIDENCE_LOG):
        return None
    last_line = ""
    with open(EVIDENCE_LOG, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                last_line = line
    if not last_line:
        return None
    try:
        record = json.loads(last_line)
        return record.get("active_skills_30d")
    except (json.JSONDecodeError, ValueError):
        return None


def main():
    now = datetime.now(timezone.utc)
    true_30d = count_active_skills_30d()
    true_30d_ocas = count_active_skills_30d_ocas()
    script_30d = get_last_script_30d()

    evidence = {
        "timestamp": now.isoformat(),
        "heartbeat_type": "light",
        "correction": True,
        "active_skills_30d_script": script_30d,
        "active_skills_30d_true": true_30d,
        "active_skills_30d_true_ocas": true_30d_ocas,
        "note": "Mandatory correction: script uses stdin-based 3-day single-path count, "
               "which always undercounts. True count uses dual-path 30-day window.",
        "outcome": "success",
    }

    with open(EVIDENCE_LOG, "a") as f:
        f.write(json.dumps(evidence) + "\n")

    print(f"active_skills_30d correction: script={script_30d} → true={true_30d} (OCAS: {true_30d_ocas})")
    print(f"Corrected evidence written to {EVIDENCE_LOG}")


if __name__ == "__main__":
    main()