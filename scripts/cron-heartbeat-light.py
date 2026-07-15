#!/usr/bin/env python3
"""Mentor Light Heartbeat — cron-safe implementation.

Reads journal file paths from stdin (piped from shell `find`).
Ingest new entries, compute anomaly/evidence metrics, write journal.

Usage:
    find JOURNALS_DIR -name "*.json" -mtime -3 \
        -not -path "*/.archive/*" -not -path "*/.quarantine/*" \
        | python3 cron-heartbeat-light.py
"""
import os, json, sys
from datetime import datetime, timezone

AGENT_ROOT = "/root/.hermes/profiles/indigo"
JOURNALS_DIR = "/root/.hermes/commons/journals"
# Canonical Mentor data lives under commons/data/mentor/ (not ocas-mentor/).
# The ocas-mentor/ directory is a legacy alias; all heartbeats must write
# evidence, ingestion_log, anomalies, and okr_state to the canonical path.
MENTOR_DATA = os.path.join(AGENT_ROOT, "commons", "data", "mentor")
INGESTION_LOG = os.path.join(MENTOR_DATA, "ingestion_log.jsonl")
EVIDENCE_LOG = os.path.join(MENTOR_DATA, "evidence.jsonl")
ANOMALIES_FILE = os.path.join(MENTOR_DATA, "anomalies.jsonl")
JOURNAL_DIR = os.path.join(AGENT_ROOT, "commons", "journals", "ocas-mentor")

now = datetime.now(timezone.utc)


def parse_dt(ts_str):
    if ts_str is None:
        return None
    s = str(ts_str).strip()
    if not s or s in ("0", "null", "None"):
        return None
    try:
        if isinstance(ts_str, (int, float)):
            ts = float(ts_str)
            return datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts, tz=timezone.utc)
        dt = datetime.fromisoformat(s.replace("Z", "+00:00").replace("z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError, OSError):
        return None


def normalize_outcome(entry):
    outcome = entry.get("outcome", entry.get("status"))
    if outcome is None:
        return "error" if "error" in entry else "success"
    if isinstance(outcome, dict):
        return outcome.get("state", "unknown")
    if isinstance(outcome, str):
        return outcome.lower().strip()
    return str(outcome)


def load_journal_file(path):
    """Multi-format journal parser: JSONL, single JSON object, JSON array."""
    entries = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            return entries
        try:
            for line in content.split("\n"):
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if isinstance(obj, dict):
                    entries.append(obj)
            if entries:
                return entries
        except (json.JSONDecodeError, ValueError):
            pass
        try:
            obj = json.loads(content)
            if isinstance(obj, dict):
                return [obj]
            if isinstance(obj, list):
                return [i for i in obj if isinstance(i, dict)]
        except (json.JSONDecodeError, ValueError):
            pass
        for line in content.split("\n"):
            line = line.strip().rstrip(",")
            if not line or line in ("[", "]"):
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    entries.append(obj)
            except (json.JSONDecodeError, ValueError):
                pass
    except (OSError, IOError):
        pass
    return entries


def extract_skill_from_journal_path(fpath):
    """Return skill directory name from either shared or profile-scoped journal paths."""
    parts = os.path.abspath(fpath).split(os.sep)
    for i, part in enumerate(parts):
        if part == "journals" and i + 1 < len(parts):
            return parts[i + 1]
    rel = os.path.relpath(fpath, JOURNALS_DIR)
    return rel.split(os.sep)[0]


def main():
    # Ensure data directory exists (including after fresh state / data loss)
    os.makedirs(MENTOR_DATA, exist_ok=True)

    ingested_files = set()
    if os.path.exists(INGESTION_LOG):
        with open(INGESTION_LOG, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    fp = rec.get("file", "")
                    # Normalize to absolute path for reliable dedup
                    if fp.startswith("/"):
                        canonical = fp
                    elif fp.startswith("commons/"):
                        canonical = os.path.join("/root/.hermes/profiles/indigo", fp)
                    else:
                        canonical = os.path.abspath(fp) if fp else fp
                    ingested_files.add(canonical)
                except json.JSONDecodeError:
                    pass

    all_files = [line.strip() for line in sys.stdin if line.strip()]

    new_files = []
    for fpath in all_files:
        canonical = fpath if fpath.startswith("/") else os.path.abspath(fpath)
        if canonical not in ingested_files:
            new_files.append(fpath)

    new_entries = []
    error_entries = []
    skills_with_new = set()
    parse_failures = 0

    for fpath in new_files:
        skill = extract_skill_from_journal_path(fpath)
        if skill in (".archive", ".quarantine"):
            continue

        entries = load_journal_file(fpath)

        if not entries:
            try:
                if os.path.getsize(fpath) > 0:
                    parse_failures += 1
            except OSError:
                pass

        with open(INGESTION_LOG, "a") as f:
            f.write(json.dumps({
                "file": os.path.abspath(fpath),
                "skill_name": skill,
                "ingested_at": now.isoformat(),
                "entries": len(entries),
            }) + "\n")

        if not entries:
            continue

        skills_with_new.add(skill)
        for entry in entries:
            oc = normalize_outcome(entry)
            new_entries.append({"skill": skill, "outcome": oc, "entry": entry})
            if oc in ("error", "failed"):
                error_entries.append({
                    "skill": skill,
                    "error": str(entry.get("error", ""))[:200],
                    "ts": entry.get("timestamp", ""),
                })

    outcome_counts = {}
    for e in new_entries:
        outcome_counts[e["outcome"]] = outcome_counts.get(e["outcome"], 0) + 1

    gap_detected = False
    gap_minutes = 0.0
    last_hb_ts = None
    if os.path.exists(EVIDENCE_LOG):
        with open(EVIDENCE_LOG, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    ts = parse_dt(rec.get("timestamp"))
                    if ts and (last_hb_ts is None or ts > last_hb_ts):
                        last_hb_ts = ts
                except json.JSONDecodeError:
                    pass
    if last_hb_ts:
        gap_minutes = (now - last_hb_ts).total_seconds() / 60
        gap_detected = gap_minutes > 15

    active_skills_30d = set()
    for fpath in all_files:
        rel = os.path.relpath(fpath, JOURNALS_DIR)
        skill = rel.split(os.sep)[0]
        if skill not in (".archive", ".quarantine"):
            active_skills_30d.add(skill)

    # Coverage: fraction of active skills that had new entries this run.
    # "Active" = any skill with a journal directory (has produced output at some point).
    # This avoids inflating the denominator with stale/one-off directories.
    evaluation_coverage = round(len(skills_with_new) / max(len(active_skills_30d), 1), 4)

    active_anomalies = 0
    if os.path.exists(ANOMALIES_FILE):
        with open(ANOMALIES_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    a = json.loads(line)
                    a_ts = parse_dt(a.get("timestamp") or a.get("detected_at"))
                    if a_ts and (now - a_ts).total_seconds() < 7 * 86400:
                        active_anomalies += 1
                except json.JSONDecodeError:
                    pass

    evidence = {
        "timestamp": now.isoformat(),
        "heartbeat_type": "light",
        "total_files_scanned": len(all_files),
        "new_files_ingested": len(new_files),
        "new_entries": len(new_entries),
        "outcome_counts": outcome_counts,
        "errors": len(error_entries),
        "error_skills": sorted(set(e["skill"] for e in error_entries)),
        "skills_with_new_entries": len(skills_with_new),
        "active_skills_30d": len(active_skills_30d),
        "evaluation_coverage": evaluation_coverage,
        "gap_detected": gap_detected,
        "gap_minutes": round(gap_minutes, 1),
        "active_anomalies": active_anomalies,
        "parse_failures": parse_failures,
    }
    with open(EVIDENCE_LOG, "a") as f:
        f.write(json.dumps(evidence) + "\n")

    date_dir = os.path.join(JOURNAL_DIR, now.strftime("%Y-%m-%d"))
    os.makedirs(date_dir, exist_ok=True)
    run_id = now.strftime("%Y%m%dT%H%M%SZ")
    journal = {
        "schema": "mentor-journal-v2",
        "run_id": f"mentor-light-{run_id}",
        "timestamp": now.isoformat(),
        "heartbeat_type": "light",
        "entities_observed": sorted(skills_with_new),
        "metrics": {
            "new_files_ingested": len(new_files),
            "new_entries": len(new_entries),
            "errors": len(error_entries),
            "skills_with_new": len(skills_with_new),
            "active_skills_30d": len(active_skills_30d),
            "coverage": evaluation_coverage,
            "gap_detected": gap_detected,
        },
        "outcome": "success" if not error_entries else "partial",
    }
    jpath = os.path.join(date_dir, f"mentor-light-{run_id}.json")
    with open(jpath, "w") as f:
        json.dump(journal, f, indent=2, default=str)

    print("=== Mentor Light Heartbeat Complete ===")
    print(f"Timestamp: {now.isoformat()}")
    print(f"Recent journal files scanned: {len(all_files)}")
    print(f"New files ingested: {len(new_files)}")
    print(f"New entries: {len(new_entries)}")
    print(f"Outcome counts: {json.dumps(outcome_counts)}")
    print(f"Errors: {len(error_entries)}")
    if error_entries:
        for e in error_entries[:10]:
            print(f"  - [{e['skill']}] {e['error'][:120]}")
    print(f"Skills with new entries: {len(skills_with_new)}")
    print(f"Active skills (30d): {len(active_skills_30d)}")
    print(f"Evaluation coverage: {evaluation_coverage}")
    print(f"Gap detected: {gap_detected}" + (f" ({gap_minutes:.1f} min)" if gap_detected else ""))
    print(f"Active anomalies: {active_anomalies}")
    print(f"Parse failures: {parse_failures}")


if __name__ == "__main__":
    main()
