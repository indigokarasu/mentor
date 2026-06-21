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
import os, json, subprocess
from datetime import datetime, timezone

AGENT_ROOT = "/root/.hermes/profiles/indigo"
MENTOR_DATA = os.path.join(AGENT_ROOT, "commons", "data", "mentor")
EVIDENCE_LOG = os.path.join(MENTOR_DATA, "evidence.jsonl")
JOURNALS_DIRS = [
    "/root/.hermes/commons/journals",
    "/root/.hermes/profiles/indigo/commons/journals",
]


def count_active_skills_30d():
    """Count unique skill names across both journal paths, 30-day window."""
    cmd = (
        "find /root/.hermes/commons/journals/ /root/.hermes/profiles/indigo/commons/journals/ "
        "-name '*.json' -mtime -30 2>/dev/null "
        "| grep -oP 'commons/journals/([a-z][a-z0-9_-]+)' "
        "| sed 's|commons/journals/||' "
        "| sort -u | wc -l"
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return int(result.stdout.strip())


def count_active_skills_30d_ocas():
    """Count OCAS-only skills across both journal paths, 30-day window."""
    cmd = (
        "find /root/.hermes/commons/journals/ /root/.hermes/profiles/indigo/commons/journals/ "
        "-name '*.json' -mtime -30 2>/dev/null "
        "| grep -oP 'ocas-[a-z]+' "
        "| sort -u | wc -l"
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return int(result.stdout.strip())


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
