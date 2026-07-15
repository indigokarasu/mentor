#!/usr/bin/env python3
"""Verify a heartbeat ingest window via CONTENT timestamps, not file mtimes.

WHY: in some environments journal files carry file-mtimes that lag the system
clock by hours, so `find -mmin -N` silently misses real recent journals. This
probe scans files whose FILE mtime is within an offset-covering window, then
checks each file's CONTENT timestamp (timestamp/run_id/created_at/ingested_at)
against the real-time window. Confirms whether a 0-file heartbeat result is
genuine or a mtime-offset artifact.

Usage:
    python3 verify_ingest_window.py [window_minutes] [mtime_coverage_minutes]
Defaults: window=5, mtime_coverage=450 (covers ~7.5h lag).

Invoke WITHOUT a pipe (cron `tirith:pipe_to_interpreter` blocks `cmd | python3`).
"""
import os, json, sys
from datetime import datetime, timezone

WINDOW = int(sys.argv[1]) if len(sys.argv) > 1 else 5
MTIME_COVER = int(sys.argv[2]) if len(sys.argv) > 2 else 450

NOW = datetime.now(timezone.utc)
WIN_START = NOW.timestamp() - WINDOW * 60
MTIME_CUTOFF = NOW.timestamp() - MTIME_COVER * 60

ROOTS = [
    "/root/.hermes/commons/journals",
    "/root/.hermes/profiles/indigo/commons/journals",
]


def extract_ts(obj):
    if not isinstance(obj, dict):
        return None
    for key in ("timestamp", "run_id", "created_at", "ingested_at", "date"):
        v = obj.get(key)
        if isinstance(v, str) and ("T" in v or "-" in v):
            s = v.replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(s)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass
    return None


candidates = 0
in_window = 0
newest_ts = None
newest_path = None

for root in ROOTS:
    for dp, _, files in os.walk(root):
        if ".archive" in dp or ".quarantine" in dp:
            continue
        for fn in files:
            if not fn.endswith(".json"):
                continue
            fp = os.path.join(dp, fn)
            try:
                mtime = os.path.getmtime(fp)
            except OSError:
                continue
            if mtime < MTIME_CUTOFF:
                continue
            candidates += 1
            ts = None
            try:
                with open(fp) as f:
                    content = f.read().strip()
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict):
                        ts = extract_ts(parsed)
                    elif isinstance(parsed, list):
                        for item in parsed:
                            ts = extract_ts(item)
                            if ts:
                                break
                except Exception:
                    pass
                if ts is None:
                    for line in content.split("\n"):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                        except Exception:
                            continue
                        ts = extract_ts(obj)
                        if ts:
                            break
            except Exception:
                continue
            if ts is None:
                continue
            if newest_ts is None or ts > newest_ts:
                newest_ts = ts
                newest_path = fp
            if WIN_START <= ts.timestamp() <= NOW.timestamp():
                in_window += 1

print(f"NOW (system UTC): {NOW.isoformat()}")
print(f"Real {WINDOW}-min window start: {datetime.fromtimestamp(WIN_START, tz=timezone.utc).isoformat()}")
print(f"Files with file-mtime in last {MTIME_COVER} min (covers lag): {candidates}")
print(f"Journals with CONTENT ts inside last {WINDOW} real min: {in_window}")
if newest_ts:
    print(f"Newest journal content ts: {newest_ts.isoformat()}  ({newest_path})")
    print(f"Gap since newest journal (content): {(NOW - newest_ts).total_seconds() / 60:.1f} min")
print("RESULT:", "0 NEW JOURNALS CONFIRMED" if in_window == 0 else f"{in_window} JOURNALS IN WINDOW (check if heartbeat missed them)")
