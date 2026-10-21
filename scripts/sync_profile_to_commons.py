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
import os
import shutil
import sys

_HELP_ARGS = {"--help", "-h"}
if set(sys.argv[1:]) & _HELP_ARGS:
    print((__doc__ or "Usage: python3 sync_profile_to_commons.py").strip())
    sys.exit(0)

PROFILE_DIR = '~/.hermes/profiles/indigo/commons/data/mentor'
COMMONS_DIR = '~/.hermes/commons/data/mentor'

JSONL_FILES = ['evidence.jsonl', 'ingestion_log.jsonl']
STATE_FILES = ['okr_state.json', 'anomalies.jsonl', 'decisions.jsonl']

DRY_RUN = '--dry-run' in sys.argv


def _read_lines(path):
    """Read a text file's lines; raises OSError on failure."""
    with open(path) as f:
        return f.readlines()


def _append_lines(path, lines):
    """Append lines to a file; raises OSError on failure."""
    with open(path, 'a') as f:
        for line in lines:
            f.write(line)


def sync_jsonl(filename):
    """Sync a JSONL file: append profile lines not already in commons."""
    pe = os.path.join(PROFILE_DIR, filename)
    ce = os.path.join(COMMONS_DIR, filename)

    if not os.path.exists(pe):
        print('  SKIP %s: profile file not found' % filename)
        return

    try:
        profile_lines = _read_lines(pe)
        commons_lines = _read_lines(ce)
    except OSError as exc:
        print('  ERROR %s: cannot read %s (%s)' % (filename, pe, exc))
        sys.exit(1)

    commons_set = set(commons_lines)
    new_lines = [l for l in profile_lines if l not in commons_set]

    if not new_lines:
        print('  OK %s: %d lines, no new lines' % (filename, len(profile_lines)))
        return

    if DRY_RUN:
        print('  DRY-RUN %s: would append %d lines' % (filename, len(new_lines)))
        return

    try:
        _append_lines(ce, new_lines)
    except OSError as exc:
        print('  ERROR %s: cannot append to %s (%s)' % (filename, ce, exc))
        sys.exit(1)

    print('  SYNCED %s: +%d lines (%d profile -> %d commons)' % (
        filename, len(new_lines), len(profile_lines), len(commons_lines) + len(new_lines)))


def sync_state(filename):
    """Sync a state file: cp -f overwrite."""
    pe = os.path.join(PROFILE_DIR, filename)
    ce = os.path.join(COMMONS_DIR, filename)

    if not os.path.exists(pe):
        print('  SKIP %s: profile file not found' % filename)
        return

    if DRY_RUN:
        print('  DRY-RUN %s: would copy' % filename)
        return

    try:
        shutil.copy2(pe, ce)
    except OSError as exc:
        print('  ERROR %s: cannot copy %s -> %s (%s)' % (filename, pe, ce, exc))
        sys.exit(1)

    print('  SYNCED %s: copied' % filename)


def main():
    print('Syncing %s -> %s' % (PROFILE_DIR, COMMONS_DIR))
    if DRY_RUN:
        print('(DRY RUN - no writes)')

    try:
        for f in JSONL_FILES:
            sync_jsonl(f)
        for f in STATE_FILES:
            sync_state(f)
    except Exception as exc:
        print('  FATAL: %s' % exc)
        sys.exit(1)

    print('Done.')


if __name__ == '__main__':
    main()
