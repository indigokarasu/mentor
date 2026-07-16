#!/usr/bin/env python3
"""
Sync mentor data from profile-scoped dir to commons (one-directional, append-only).

Usage: python3 sync_profile_to_commons.py [--dry-run]

This script is run after every heartbeat (light and deep) to keep the commons
data directory in sync with the authoritative profile-scoped data.

- JSONL files (evidence.jsonl, ingestion_log.jsonl): line-level set-difference
  (append profile lines not already in commons)
- State files (okr_state.json, anomalies.jsonl, decisions.jsonl): cp -f overwrite

Exit codes: 0 = success, 1 = error
"""
import json
import os
import sys

_HELP_ARGS = {"--help", "-h"}
if set(sys.argv[1:]) & _HELP_ARGS:
    print((__doc__ or "").strip() or "Usage: python3 sync_profile_to_commons.py")
    sys.exit(0)

PROFILE_DIR = '/root/.hermes/profiles/indigo/commons/data/mentor'
COMMONS_DIR = '/root/.hermes/commons/data/mentor'

JSONL_FILES = ['evidence.jsonl', 'ingestion_log.jsonl']
STATE_FILES = ['okr_state.json', 'anomalies.jsonl', 'decisions.jsonl']

DRY_RUN = '--dry-run' in sys.argv


def sync_jsonl(filename):
    """Sync a JSONL file: append profile lines not in commons."""
    pe = os.path.join(PROFILE_DIR, filename)
    ce = os.path.join(COMMONS_DIR, filename)

    if not os.path.exists(pe):
        print(f'  SKIP {filename}: profile file not found')
        return

    with open(pe) as f:
        profile_lines = f.readlines()
    with open(ce) as f:
        commons_lines = f.readlines()

    commons_set = set(commons_lines)
    new_lines = [l for l in profile_lines if l not in commons_set]

    if not new_lines:
        print(f'  OK {filename}: {len(profile_lines)} lines, no new lines')
        return

    if DRY_RUN:
        print(f'  DRY-RUN {filename}: would append {len(new_lines)} lines')
        return

    with open(ce, 'a') as f:
        for line in new_lines:
            f.write(line)
    print(f'  SYNCED {filename}: +{len(new_lines)} lines ({len(profile_lines)} profile → {len(commons_lines) + len(new_lines)} commons)')


def sync_state(filename):
    """Sync a state file: cp -f overwrite."""
    pe = os.path.join(PROFILE_DIR, filename)
    ce = os.path.join(COMMONS_DIR, filename)

    if not os.path.exists(pe):
        print(f'  SKIP {filename}: profile file not found')
        return

    if DRY_RUN:
        print(f'  DRY-RUN {filename}: would copy')
        return

    import shutil
    shutil.copy2(pe, ce)
    print(f'  SYNCED {filename}: copied')


def main():
    print(f'Syncing {PROFILE_DIR} → {COMMONS_DIR}')
    if DRY_RUN:
        print('(DRY RUN — no writes)')

    for f in JSONL_FILES:
        sync_jsonl(f)

    for f in STATE_FILES:
        sync_state(f)

    print('Done.')


if __name__ == '__main__':
    main()
