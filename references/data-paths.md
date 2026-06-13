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
| `commons/data/ocas-mentor/` | Legacy alias. Contains stale copies of evidence/ingestion from before the path was corrected. Do not write new data here. |

## Key Rule

**All heartbeat scripts must use `MENTOR_DATA = .../commons/data/mentor/`** (not `ocas-mentor`).
The `ocas-mentor/` data directory is a legacy artifact. Writing to it causes evidence records to be
invisible to downstream processes that read from `mentor/`.

## Coverage Metric

- **Light heartbeat**: `skills_with_new_entries / active_skills_30d` — fraction of active skills that had new journal entries this run.
- **Deep heartbeat**: `skills_with_journals / total_installed_dirs` — fraction of installed skill dirs with any journals.
- Do NOT use total journal directory count as the denominator for light heartbeat coverage — it inflates with stale/one-off dirs and produces misleadingly low values.
- `active_skills_30d` must be computed by scanning **both** journal locations above, deduplicating by skill name.
