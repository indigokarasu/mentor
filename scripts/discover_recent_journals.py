#!/usr/bin/env python3
"""Tight-window journal discovery via CONTENT timestamp (counters mtime lag).

In this environment, journal file-mtimes lag content timestamps by ~7h12m, so
`find -mmin -N` silently misses real recent journals for tight windows
(sub-hour). This script reads a candidate file list (produced by a WIDE find
window, e.g. `-mmin -450`, to counter the lag) from stdin and filters by the
JSON content timestamp, keeping only journals whose content timestamp is within
the last WINDOW_MINUTES of NOW (UTC).

Unlike scripts/verify_ingest_window.py (which REPORTS whether 0 is genuine),
this script EMITS the filtered file list on stdout so it can be fed (via stdin
redirect, never a pipe) into cron-heartbeat-light.py.

Usage (cron-safe -- stdin redirect, NEVER pipe to python; see SKILL.md
tirith:pipe_to_interpreter block):
    find /root/.hermes/commons/journals/ /root/.hermes/profiles/indigo/commons/journals/ \
        -name "*.json" -mmin -450 -not -path "*/.archive/*" -not -path "*/.quarantine/*" \
        > /tmp/candidates.txt
    python3 scripts/discover_recent_journals.py --window-minutes 5 < /tmp/candidates.txt \
        > /tmp/mentor_files_3d.txt

The output file is then fed to cron-heartbeat-light.py via stdin redirect:
    python3 scripts/cron-heartbeat-light.py < /tmp/mentor_files_3d.txt

Do NOT use subprocess.find or os.walk inside this script -- both return 0
results in the cron sandbox (confirmed gotcha). Candidates MUST come from a
shell `find` written to a file.

NOTE (fixed 2026-07-13): journals using a `generated_at` field (e.g.
praxis-cron-*.json) or a non-`mentor-*` run_id prefix (praxis-cron-,
dispatch-wave-, forge-scan-, etc.) were previously SILENTLY SKIPPED because
parse_ts only recognized timestamp/detected_at/ingested_at/created_at/run_id
and only stripped mentor-light-/mentor-deep- prefixes. Now `generated_at` is in
the key list and parse_ts extracts the embedded YYYYMMDDThhmmssZ token from ANY
run_id prefix via regex, so all recent journals are caught.
"""
import json
import re
import sys
from datetime import datetime, timezone, timedelta


def parse_ts(value):
    """Parse an ISO timestamp or a run_id-embedded timestamp."""
    if not value or not isinstance(value, str):
        return None
    s = value.strip()
    # Extract the embedded YYYYMMDDThhmmssZ token from ANY run_id prefix
    # (mentor-light-, mentor-deep-, praxis-cron-, dispatch-wave-, forge-scan-,
    # etc.). Plain ISO timestamps pass through unchanged. Fixes silent skips
    # of journals whose run_id is not mentor-*-prefixed (confirmed 2026-07-13).
    m = re.search(r"\d{8}T\d{6}Z", s)
    if m:
        s = m.group(0)
    s2 = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s2)
    except Exception:
        pass
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%dT%H%M%S%z"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None


def main():
    window = 5
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--window-minutes" and i + 1 < len(args):
            try:
                window = int(args[i + 1])
            except ValueError:
                pass
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=window)

    matched = 0
    total = 0
    for line in sys.stdin:
        path = line.strip()
        if not path:
            continue
        total += 1
        try:
            with open(path) as jf:
                d = json.load(jf)
        except Exception:
            continue
        ts = None
        for key in ("timestamp", "generated_at", "detected_at", "ingested_at", "run_id", "created_at"):
            if ts is None and key in d:
                ts = parse_ts(d.get(key))
        if ts is None:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts >= cutoff:
            sys.stdout.write(path + "\n")
            matched += 1

    sys.stderr.write(
        f"discover_recent_journals: {matched} of {total} candidates in last "
        f"{window} min (cutoff={cutoff.isoformat()})\n"
    )


if __name__ == "__main__":
    main()
