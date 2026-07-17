#!/usr/bin/env python3
"""Bidirectional Mentor data sync: profile <-> commons, line-level set-difference.

Captured 2026-07-16 from a verified deep-heartbeat run. The deep/light heartbeat
scripts write to BOTH the profile-scoped and commons mentor data dirs, but cron
mode write races and the correct_active_skills_30d.py correction (profile-only)
can leave the two stores divergent. Run this after every heartbeat to reconcile
evidence.jsonl and ingestion_log.jsonl in BOTH directions.

Usage:
    write_file this body to /tmp/mentor_deep_sync.py, then:
    python3 /tmp/mentor_deep_sync.py
(Do NOT use a heredoc in cron terminal() calls — exit_code=-1.)
"""
import os
import sys

_HELP_ARGS = {"--help", "-h"}
if set(sys.argv[1:]) & _HELP_ARGS:
    print((__doc__ or "").strip() or "Usage: python3 mentor_deep_sync.py")
    sys.exit(0)


PROFILE = "/root/.hermes/profiles/indigo/commons/data/mentor"
COMMONS = "/root/.hermes/commons/data/mentor"


def sync(src, dst, label):
    try:
        with open(src) as f:
            s = {l.rstrip("\n") for l in f if l.strip()}
    except FileNotFoundError:
        s = set()
    try:
        with open(dst) as f:
            c = {l.rstrip("\n") for l in f if l.strip()}
    except FileNotFoundError:
        c = set()
    new = s - c
    if new:
        with open(dst, "a") as f:
            for l in sorted(new):
                f.write(l + "\n")
        print(f"Synced {len(new)} lines {label}")
    else:
        print(f"No new lines {label}")


if __name__ == "__main__":
    # profile -> commons (heartbeat writes + correction record)
    sync(os.path.join(PROFILE, "evidence.jsonl"),
         os.path.join(COMMONS, "evidence.jsonl"), "evidence profile->commons")
    sync(os.path.join(PROFILE, "ingestion_log.jsonl"),
         os.path.join(COMMONS, "ingestion_log.jsonl"), "ingestion profile->commons")
    # commons -> profile (any lines the script wrote to commons only)
    sync(os.path.join(COMMONS, "ingestion_log.jsonl"),
         os.path.join(PROFILE, "ingestion_log.jsonl"), "ingestion commons->profile")
