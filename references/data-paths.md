# Mentor Data Paths Reference

## Canonical Paths

| Purpose | Path |
|---------|------|
| Mentor data (evidence, ingestion, anomalies, OKR, decisions, proposals) | `/root/.hermes/profiles/indigo/commons/data/mentor/` |
| Mentor journals | `/root/.hermes/profiles/indigo/commons/journals/ocas-mentor/` |
| Skill directory | `/root/.hermes/profiles/indigo/skills/ocas-mentor/` |

## Journal Locations (DUAL — scan BOTH)

Skill journals are written to **two** different locations depending on the skill and how it was invoked. Heartbeat scans **must** cover both:

| Location | Path | Notes |
|----------|------|-------|
| Shared commons | `/root/.hermes/commons/journals/` | Most OCAS skills write here (custodian, elephas, spot, dispatch, bones, etc.) |
| Profile-scoped commons | `/root/.hermes/profiles/indigo/commons/journals/` | Some skills write here (elephas cron runs, bones monitor, forge, mentor self, etc.) |

**Critical:** Scanning only one path will miss active skills and produce incorrect `active_skills_30d` counts. The `find` commands in heartbeat scripts must scan both paths and merge results (e.g., `cat list1 list2 | sort -u`).

## Legacy/Alias Paths (DO NOT WRITE TO)

| Path | Status |
|------|--------|
| `commons/data/mentor/` | Legacy alias. Contains stale copies of evidence/ingestion from before the path was corrected. Do not write new data here. **Sync after heartbeat:** copy from profile path to keep consistent. |

## Key Rule

**All heartbeat scripts must use `MENTOR_DATA = .../commons/data/mentor/`** (not `ocas-mentor`).
The `ocas-mentor/` data directory is a legacy artifact. Writing to it causes evidence records to
be invisible to downstream processes that read from `mentor/`.

## Post-Heartbeat Sync

After every heartbeat, sync key files from profile to commons:
```bash
PROFILE_DATA="/root/.hermes/profiles/indigo/commons/data/mentor"
COMMONS_DATA="/root/.hermes/commons/data/mentor"
for f in evidence.jsonl ingestion_log.jsonl anomalies.jsonl okr_state.json decisions.jsonl; do
    cp "$PROFILE_DATA/$f" "$COMMONS_DATA/$f" 2>/dev/null
done
```

## Journal Date Directory

**Always use UTC for journal directory names.** The `run_id` is composed from UTC time (`datetime.now(timezone.utc)`), so the directory must match:
```bash
# CORRECT — UTC date matches UTC run_id
JOURNAL_DIR="/root/.hermes/profiles/indigo/commons/journals/ocas-mentor/$(date -u +%Y-%m-%d)"

# WRONG — local date can be a day behind, putting journal in wrong directory
JOURNAL_DIR="/root/.hermes/profiles/indigo/commons/journals/ocas-mentor/$(date +%Y-%m-%d)"
```
If the server timezone is not UTC, using `date +%Y-%m-%d` puts the journal file in yesterday's directory while the filename contains today's UTC timestamp — creating a mismatch that confuses cross-reference and manual inspection.

- **Light heartbeat**: `skills_with_new_entries / active_skills_30d` — fraction of active skills that had new journal entries this run.
- **Deep heartbeat**: `skills_with_journals / total_installed_dirs` — fraction of installed skill dirs with any journals.
- Do NOT use total journal directory count as the denominator for light heartbeat coverage — it inflates with stale/one-off dirs and produces misleadingly low values.
- `active_skills_30d` must be computed by scanning **both** journal locations above, deduplicating by skill name.
