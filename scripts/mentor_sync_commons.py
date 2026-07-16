#!/usr/bin/env python3
"""Timestamp-based set-difference sync: profile -> commons for evidence and ingestion."""
import json
import sys

_HELP_ARGS = {"--help", "-h"}
if set(sys.argv[1:]) & _HELP_ARGS:
    print((__doc__ or "").strip() or "Usage: python3 mentor_sync_commons.py")
    sys.exit(0)

PROFILE_EVIDENCE = "/root/.hermes/profiles/indigo/commons/data/mentor/evidence.jsonl"
COMMONS_EVIDENCE = "/root/.hermes/commons/data/mentor/evidence.jsonl"
PROFILE_INGESTION = "/root/.hermes/profiles/indigo/commons/data/mentor/ingestion_log.jsonl"
COMMONS_INGESTION = "/root/.hermes/commons/data/mentor/ingestion_log.jsonl"

# --- Evidence sync (field: timestamp) ---
last_commons_ts = ""
with open(COMMONS_EVIDENCE) as f:
    for line in f:
        if not line.strip(): continue
        try:
            d = json.loads(line)
            ts = d.get("timestamp", "")
            if ts:
                last_commons_ts = ts
        except: pass

evidence_synced = 0
with open(PROFILE_EVIDENCE) as f:
    for line in f:
        if not line.strip(): continue
        try:
            d = json.loads(line)
            if d.get("timestamp", "") > last_commons_ts:
                with open(COMMONS_EVIDENCE, "a") as out:
                    out.write(line.rstrip() + "\n")
                evidence_synced += 1
        except: pass

print(f"Evidence sync: {evidence_synced} lines (last_commons_ts={last_commons_ts[:25] if last_commons_ts else 'none'})")

# --- Ingestion sync (field: ingested_at) ---
last_commons_ing = ""
with open(COMMONS_INGESTION) as f:
    for line in f:
        if not line.strip(): continue
        try:
            d = json.loads(line)
            ts = d.get("ingested_at", "")
            if ts:
                last_commons_ing = ts
        except: pass

ingestion_synced = 0
with open(PROFILE_INGESTION) as f:
    for line in f:
        if not line.strip(): continue
        try:
            d = json.loads(line)
            if d.get("ingested_at", "") > last_commons_ing:
                with open(COMMONS_INGESTION, "a") as out:
                    out.write(line.rstrip() + "\n")
                ingestion_synced += 1
        except: pass

print(f"Ingestion sync: {ingestion_synced} lines (last_commons_ing={last_commons_ing[:25] if last_commons_ing else 'none'})")