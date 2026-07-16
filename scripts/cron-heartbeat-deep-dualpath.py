#!/usr/bin/env python3
"""Mentor Deep Heartbeat — Dual-Path Wrapper. Fixes gotcha #32."""
import json, os, hashlib, sys
from datetime import datetime, timezone, timedelta
from collections import defaultdict

_HELP_ARGS = {"--help", "-h"}
if set(sys.argv[1:]) & _HELP_ARGS:
    print((__doc__ or "").strip() or "Usage: python3 cron-heartbeat-deep-dualpath.py")
    sys.exit(0)

def parse_dt(ts_str):
    if ts_str is None: return None
    s = str(ts_str).strip()
    if not s or s in ("0", "null", "None"): return None
    try:
        if isinstance(ts_str, (int, float)):
            ts = float(ts_str)
            return datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts, tz=timezone.utc)
        dt = datetime.fromisoformat(s.replace("Z", "+00:00").replace("z", "+00:00"))
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError, OSError): return None

def normalize_outcome(entry):
    if not isinstance(entry, dict): return "unknown"
    outcome = None
    for key in ("outcome", "status", "result"):
        val = entry.get(key)
        if val is not None: outcome = val; break
    if outcome is not None:
        if isinstance(outcome, dict):
            for k, v in outcome.items():
                if v and str(k).lower() in ("error", "failed", "failure"): return "error"
                if v and str(k).lower() in ("success", "completed", "done"): return "success"
            return "unknown"
        val = str(outcome).lower().strip()
        if val in ("success", "ok", "pass", "passed", "completed", "done"): return "success"
        if val in ("error", "fail", "failed", "failure"): return "error"
        return "unknown"
    if entry.get("error") or entry.get("errors"): return "error"
    return "success"

def load_journal_entries(filepath):
    try:
        with open(filepath) as f: content = f.read().strip()
    except Exception: return []
    if not content: return []
    lines = content.splitlines()
    parsed_lines = []
    all_valid = True
    for line in lines:
        line = line.strip()
        if not line: continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict): parsed_lines.append(obj)
            else: all_valid = False; break
        except json.JSONDecodeError: all_valid = False; break
    if all_valid and parsed_lines: return parsed_lines
    try:
        data = json.loads(content)
        if isinstance(data, list): return [item for item in data if isinstance(item, dict)]
        elif isinstance(data, dict): return [data]
    except json.JSONDecodeError: pass
    return []

JOURNALS_PATHS = ["/root/.hermes/commons/journals/", "/root/.hermes/profiles/indigo/commons/journals/"]
MENTOR_DATA = "/root/.hermes/commons/data/mentor/"
PROFILE_MENTOR_DATA = "/root/.hermes/profiles/indigo/commons/data/mentor/"

def resolve_skill_name(filepath):
    for base in JOURNALS_PATHS:
        if filepath.startswith(base):
            rel = os.path.relpath(filepath, base)
            parts = rel.split(os.sep)
            if parts[0] and not parts[0].startswith("."): return parts[0]
    parts = filepath.split("/")
    for i, part in enumerate(parts):
        if part == "journals" and i + 1 < len(parts):
            skill = parts[i + 1]
            if skill and not skill.startswith("."): return skill
    return "unknown"

def main():
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    run_id = f"deep-{today_str}T{now.strftime('%H%M%S')}Z"
    INGESTION_LOG = os.path.join(MENTOR_DATA, "ingestion_log.jsonl")
    EVIDENCE_LOG = os.path.join(MENTOR_DATA, "evidence.jsonl")
    DECISIONS_LOG = os.path.join(MENTOR_DATA, "decisions.jsonl")
    ANOMALY_LOG = os.path.join(MENTOR_DATA, "anomalies.jsonl")
    OKR_STATE = os.path.join(MENTOR_DATA, "okr_state.json")
    os.makedirs(MENTOR_DATA, exist_ok=True)
    os.makedirs(PROFILE_MENTOR_DATA, exist_ok=True)

    ingested_run_ids = set()
    if os.path.exists(INGESTION_LOG):
        with open(INGESTION_LOG) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    rid = r.get("run_id", "")
                    if rid: ingested_run_ids.add(rid)
                except Exception: pass

    anomalies = []
    if os.path.exists(ANOMALY_LOG):
        with open(ANOMALY_LOG) as f:
            for line in f:
                try: anomalies.append(json.loads(line))
                except Exception: pass

    all_journal_files = []
    seen = set()
    for base_path in JOURNALS_PATHS:
        if not os.path.isdir(base_path): continue
        for root, dirs, files in os.walk(base_path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fn in files:
                if fn.endswith((".jsonl", ".json")):
                    fp = os.path.join(root, fn)
                    if fp not in seen: seen.add(fp); all_journal_files.append(fp)

    total_files = len(all_journal_files)
    skill_files = defaultdict(list)
    for fp in all_journal_files: skill_files[resolve_skill_name(fp)].append(fp)
    installed_skill_dirs = sorted(set(skill_files.keys()))
    total_installed = len(installed_skill_dirs) if installed_skill_dirs else 1

    thirty_days_ago = now - timedelta(days=30)
    skills_active_30d = set()
    for skill_name, files in skill_files.items():
        for fp in files:
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(fp), tz=timezone.utc)
                if mtime >= thirty_days_ago: skills_active_30d.add(skill_name); break
            except Exception: pass

    new_ingested = 0; quarantined = 0; parse_errors = 0; skills_with_new = set()
    batch_outcomes = defaultdict(lambda: {"success": 0, "error": 0, "unknown": 0})
    skill_error_details = defaultdict(list); ingestion_batch = []

    for fp in all_journal_files:
        skill_name = resolve_skill_name(fp)
        mtime = os.path.getmtime(fp)
        file_hash = hashlib.md5(fp.encode()).hexdigest()[:12]
        file_run_id = f"{file_hash}_{int(mtime)}"
        if file_run_id in ingested_run_ids: continue
        entries = load_journal_entries(fp)
        if not entries:
            try:
                sz = os.path.getsize(fp)
                if sz > 10: parse_errors += 1; quarantined += 1
            except Exception: pass
            continue
        valid_entries = 0
        for entry in entries:
            if not isinstance(entry, dict): continue
            valid_entries += 1
            outcome = normalize_outcome(entry)
            batch_outcomes[skill_name][outcome] += 1
            ts_val = entry.get("timestamp") or entry.get("ts") or entry.get("created_at")
            if isinstance(ts_val, (int, float)):
                ts = datetime.fromtimestamp(ts_val / 1000 if ts_val > 1e12 else ts_val, tz=timezone.utc)
            else: ts = parse_dt(ts_val)
            if outcome == "error":
                detail = entry.get("description", entry.get("detail", str(entry.get("error", ""))))
                if not detail: detail = str(entry)[:200]
                skill_error_details[skill_name].append({"timestamp": ts.isoformat() if ts else None, "detail": str(detail)[:300], "source": fp})
        if valid_entries > 0:
            new_ingested += valid_entries; skills_with_new.add(skill_name)
            ingested_run_ids.add(file_run_id)
            ingestion_batch.append({"run_id": file_run_id, "ingested_at": now.isoformat(), "source": fp, "skill": skill_name, "entries": valid_entries})

    total_success = sum(s["success"] for s in batch_outcomes.values())
    total_error = sum(s["error"] for s in batch_outcomes.values())
    total_unknown = sum(s["unknown"] for s in batch_outcomes.values())
    total_outcomes = total_success + total_error + total_unknown
    orchestration_success_rate = (total_success + total_unknown) / total_outcomes if total_outcomes > 0 else 0.0
    error_rate = (total_error / total_outcomes) if total_outcomes > 0 else 0.0
    explicit_outcome_rate = (total_success + total_error) / total_outcomes if total_outcomes > 0 else 0.0
    skills_with_journals = len([s for s in installed_skill_dirs if skill_files.get(s)])
    evaluation_coverage = skills_with_journals / total_installed if total_installed > 0 else 0.0
    active_coverage = len(skills_with_new) / len(skills_active_30d) if skills_active_30d else 0.0
    active_coverage_reported = min(active_coverage, 1.0)

    okr_scores = {}
    okr_scores["orchestration_success_rate"] = {"value": round(orchestration_success_rate, 4), "target": 0.95, "status": "PASS" if orchestration_success_rate >= 0.95 else "FAIL"}
    okr_scores["evaluation_coverage"] = {"value": round(evaluation_coverage, 4), "target": 0.90, "status": "PASS" if evaluation_coverage >= 0.90 else "WARN" if evaluation_coverage >= 0.50 else "FAIL"}
    okr_scores["promotion_accuracy"] = {"value": None, "target": 0.80, "status": "NO_DATA"}
    okr_scores["error_rate"] = {"value": round(error_rate, 4), "target_max": 0.05, "status": "PASS" if error_rate <= 0.05 else "FAIL"}
    okr_scores["escalation_rate"] = {"value": round(error_rate, 4), "target_max": 0.10, "status": "PASS" if error_rate <= 0.10 else "FAIL"}

    new_anomalies = []
    known_keys = {a.get("key", "") for a in anomalies if a.get("key")}
    for skill_name, errs in skill_error_details.items():
        if len(errs) >= 3:
            key = f"high_errors_{skill_name}"
            if key not in known_keys:
                new_anomalies.append({"key": key, "type": "high_error_rate", "skill": skill_name, "error_count": len(errs), "severity": "tier2", "detected_at": now.isoformat(), "heartbeat_count": 1, "stale": False, "details": [e["detail"][:100] for e in errs[:3]]})
    if parse_errors > 5:
        key = "schema_drift_batch"
        if key not in known_keys:
            new_anomalies.append({"key": key, "type": "schema_drift", "parse_error_count": parse_errors, "severity": "tier1", "detected_at": now.isoformat(), "heartbeat_count": 1, "stale": False})
    for a in anomalies:
        if not a.get("stale"):
            hb = a.get("heartbeat_count", 0); a["heartbeat_count"] = hb + 1
            if hb + 1 >= 5: a["stale"] = True
    anomalies.extend(new_anomalies)

    skill_health = []
    for skill_name in sorted(skills_with_new):
        o = batch_outcomes.get(skill_name, {"success": 0, "error": 0, "unknown": 0})
        t = o["success"] + o["error"] + o["unknown"]
        if t == 0: continue
        sr = o["success"] / t
        skill_health.append({"skill": skill_name, "new": t, "success": o["success"], "error": o["error"], "unknown": o["unknown"], "success_rate": round(sr, 4), "health": "healthy" if sr >= 0.95 else "degraded" if sr >= 0.80 else "failing"})

    proposals = []
    if evaluation_coverage < 0.90:
        proposals.append({"proposal_id": f"prop-eval_cov-{now.strftime('%Y%m%d%H%M%S')}", "type": "metric_redefinition", "target_skill": "ocas-mentor", "issue": "evaluation_coverage_structural", "description": f"Coverage {evaluation_coverage:.2f} < 0.90.", "auto_approvable": True, "priority": "medium"})
    for skill_name, errs in skill_error_details.items():
        if len(errs) >= 3:
            proposals.append({"proposal_id": f"prop-err-{skill_name[:20]}-{now.strftime('%Y%m%d%H%M%S')}", "type": "skill_improvement", "target_skill": skill_name, "issue": "repeated_errors", "description": f"{skill_name}: {len(errs)} errors.", "auto_approvable": False, "priority": "high" if len(errs) >= 5 else "medium"})

    last_evidence_time = None
    if os.path.exists(EVIDENCE_LOG):
        with open(EVIDENCE_LOG) as f:
            for line in f:
                try:
                    r = json.loads(line); ts = parse_dt(r.get("timestamp"))
                    if ts and (last_evidence_time is None or ts > last_evidence_time): last_evidence_time = ts
                except Exception: pass
    gap_minutes = round((now - last_evidence_time).total_seconds() / 60, 1) if last_evidence_time else 0
    gap_detected = gap_minutes > 1440

    with open(INGESTION_LOG, "a") as f:
        for e in ingestion_batch: f.write(json.dumps(e) + "\n")

    evidence_record = {"timestamp": now.isoformat(), "timestamp_end": now.isoformat(), "command": "mentor.heartbeat.deep", "run_id": run_id, "journals_scanned": total_files, "journals_ingested": new_ingested, "skills_evaluated": len(skills_with_new), "skills_total": total_installed, "skills_with_journals": skills_with_journals, "skills_active_30d": len(skills_active_30d), "evaluation_coverage": round(evaluation_coverage, 4), "active_coverage": round(active_coverage_reported, 4), "active_coverage_raw": round(active_coverage, 4), "anomalies_detected": len(new_anomalies), "anomalies_total_active": len([a for a in anomalies if not a.get("stale")]), "quarantined": quarantined, "parse_errors": parse_errors, "proposals_generated": len(proposals), "gap_detected": gap_detected, "gap_minutes": gap_minutes, "not_activity_reason": None, "dual_path": True}
    with open(EVIDENCE_LOG, "a") as f: f.write(json.dumps(evidence_record) + "\n")

    decision_record = {"decision_id": f"dec-{run_id}", "decision_type": "heartbeat.deep", "timestamp": now.isoformat(), "run_id": run_id, "summary": f"Deep HB: {new_ingested} journals, {len(skills_with_new)} skills.", "payload": {"journals_scanned": total_files, "journals_ingested": new_ingested, "skills_evaluated": len(skills_with_new), "evaluation_coverage": round(evaluation_coverage, 4), "orchestration_success_rate": round(orchestration_success_rate, 4), "error_rate": round(error_rate, 4), "explicit_outcome_rate": round(explicit_outcome_rate, 4), "proposals_generated": len(proposals), "okr_status": {k: v["status"] for k, v in okr_scores.items()}, "entities_observed": [{"type": "Entity/AI", "name": s, "user_relevance": "agent_only"} for s in sorted(skills_with_new)[:15]], "relationships_observed": [{"subject": "ocas-mentor", "predicate": "evaluates", "object": s, "user_relevance": "agent_only"} for s in sorted(skills_with_new)[:15]]}}
    with open(DECISIONS_LOG, "a") as f: f.write(json.dumps(decision_record) + "\n")
    with open(ANOMALY_LOG, "w") as f:
        for a in anomalies: f.write(json.dumps(a) + "\n")

    okr_save = {"last_run": now.isoformat(), "orchestration_success_rate": {"value": round(orchestration_success_rate, 4), "target": 0.95}, "evaluation_coverage": {"value": round(evaluation_coverage, 4), "target": 0.90}, "promotion_accuracy": {"value": None, "target": 0.80}, "error_rate": {"value": round(error_rate, 4), "target_max": 0.05}, "escalation_rate": {"value": round(error_rate, 4), "target_max": 0.10}}
    with open(OKR_STATE, "w") as f: json.dump(okr_save, f, indent=2)

    if proposals:
        ppath = os.path.join(MENTOR_DATA, f"proposals-{now.strftime('%Y%m%d')}.json")
        existing = []
        if os.path.exists(ppath):
            with open(ppath) as f: existing = json.load(f)
        existing.extend(proposals)
        with open(ppath, "w") as f: json.dump(existing, f, indent=2)

    # Profile-scoped writes
    profile_evidence = os.path.join(PROFILE_MENTOR_DATA, "evidence.jsonl")
    with open(profile_evidence, "a") as f: f.write(json.dumps(evidence_record) + "\n")
    profile_okr = os.path.join(PROFILE_MENTOR_DATA, "okr_state.json")
    with open(profile_okr, "w") as f: json.dump(okr_save, f, indent=2)

    jdir = os.path.join("/root/.hermes/profiles/indigo/commons/journals/ocas-mentor", today_str)
    os.makedirs(jdir, exist_ok=True)
    jfile = os.path.join(jdir, f"mentor-deep-{run_id}.json")
    jrecord = {"timestamp": now.isoformat(), "run_id": run_id, "command": "mentor.heartbeat.deep", "outcome": "success", "metrics": evidence_record, "okr_scores": okr_scores, "proposals": [{"id": p["proposal_id"], "skill": p["target_skill"], "priority": p["priority"]} for p in proposals], "anomalies_new": [a["key"] for a in new_anomalies], "skill_health": sorted(skill_health, key=lambda x: x["success_rate"]), "gap_detected": gap_detected, "gap_minutes": gap_minutes}
    with open(jfile, "w") as f: json.dump(jrecord, f, indent=2)

    print("=" * 70)
    print(f"  MENTOR DEEP HEARTBEAT (DUAL-PATH) — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)
    print(f"  Journals scanned:     {total_files}")
    print(f"  New ingested:         {new_ingested}")
    print(f"  Parse errors:         {parse_errors}")
    print(f"  Skills with new:      {len(skills_with_new)}")
    print(f"  Active (30d):         {len(skills_active_30d)}")
    print(f"  Installed dirs:       {total_installed}")
    okr_str = ", ".join(f"{k}={v['status']}" for k, v in okr_scores.items())
    print(f"  OKRs:                 {okr_str}")
    print(f"  Coverage:             {evaluation_coverage:.2%}")
    print(f"  Active coverage:      {active_coverage_reported:.2%}" + (f" (raw: {active_coverage:.2%})" if active_coverage > 1.0 else ""))
    print(f"  Success rate:         {orchestration_success_rate:.4f}")
    print(f"  Error rate:           {error_rate:.4f}")
    print(f"  Explicit outcomes:    {explicit_outcome_rate:.2%}")
    print(f"  New anomalies:        {len(new_anomalies)}")
    print(f"  Proposals:            {len(proposals)}")
    print(f"  Gap:                  {gap_minutes} min {'DETECTED' if gap_detected else 'OK'}")
    print("  SKILL HEALTH:")
    for sh in sorted(skill_health, key=lambda x: x["success_rate"]):
        icon = "🟢" if sh["health"] == "healthy" else "🟡" if sh["health"] == "degraded" else "🔴"
        print(f"    {icon} {sh['skill']}: {sh['success_rate']:.1%} ({sh['new']} entries)")
    print("=" * 70)

if __name__ == "__main__":
    main()
