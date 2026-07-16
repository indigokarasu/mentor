#!/usr/bin/env python3
"""
Deep Heartbeat Ingestion Backup Writer
Confirmed 2026-06-29 — cron mode silently fails to write ingestion_log.jsonl
despite script reporting "New ingested: N > 0".

Usage: python3 /tmp/mentor_deep_backup.py
(Write this file to /tmp/ via write_file first, then invoke)
"""
import json
import os
from datetime import datetime, timezone
import sys

_HELP_ARGS = {"--help", "-h"}
if set(sys.argv[1:]) & _HELP_ARGS:
    print((__doc__ or "").strip() or "Usage: python3 deep_ingest_backup.py")
    sys.exit(0)

DATA_DIR = "/root/.hermes/profiles/indigo/commons/data/mentor"
INGESTION_LOG = os.path.join(DATA_DIR, "ingestion_log.jsonl")
DEEP_FILES = "/tmp/mentor_deep_files.txt"

def main():
    # Read already-ingested paths
    already_ingested = set()
    try:
        with open(INGESTION_LOG) as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    d = json.loads(line)
                    path = d.get("file", d.get("source", ""))
                    if path:
                        already_ingested.add(path)
                except Exception:
                    pass
    except FileNotFoundError:
        pass

    print(f"Already ingested: {len(already_ingested)} records")

    # Read the file list that was fed to the deep heartbeat
    with open(DEEP_FILES) as f:
        all_files = [line.strip() for line in f if line.strip()]

    # Write ingestion records for new files
    now_iso = datetime.now(timezone.utc).isoformat()
    written = 0

    with open(INGESTION_LOG, "a") as f:
        for filepath in all_files:
            if filepath not in already_ingested:
                # Extract skill name from path
                parts = filepath.split("/")
                skill_name = ""
                for i, part in enumerate(parts):
                    if part == "journals" and i + 1 < len(parts):
                        skill_name = parts[i + 1]
                        break

                record = {
                    "file": filepath,
                    "skill_name": skill_name,
                    "ingested_at": now_iso,
                    "entries": 1,
                    "heartbeat_type": "deep",
                    "run_id": "deep-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                }
                f.write(json.dumps(record) + "\n")
                written += 1

    print(f"Ingestion backup: {written} records written")

    # Verify
    total = 0
    with open(INGESTION_LOG) as f:
        for line in f:
            if line.strip():
                total += 1
    print(f"Ingestion log total: {total}")


if __name__ == "__main__":
    main()
