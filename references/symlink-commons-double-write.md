# `~/.hermes/commons` Is A Symlink — Dual-Write Heartbeats Append Twice

## The fact

```
/root/.hermes/commons -> /root/.hermes/profiles/indigo/commons
```

Created 2026-07-13. So `MENTOR_DATA` and `PROFILE_MENTOR_DATA` are **the same
directory**, and `evidence.jsonl` / `ingestion_log.jsonl` / `okr_state.json` resolve to
**the same inode**. Verify any time:

```bash
ls -ldi /root/.hermes/commons/data/mentor /root/.hermes/profiles/indigo/commons/data/mentor
# identical inode -> symlinked
```

## The defect it caused

`cron-heartbeat-deep-dualpath.py` appended the same `evidence_record` twice — once to
`EVIDENCE_LOG` (commons) and once to `profile_evidence` (profile). With the symlink,
that is one file appended twice per run:

- **29 duplicated evidence records**, 2026-09-23 through 2026-10-03.
- Every duplicate was **byte-identical**, so every OKR still scored PASS, `rc=0`,
  no gap, no error rate. Nothing surfaced it.
- Blast radius is bounded: `decisions.jsonl`, `anomalies.jsonl` and `okr_state.json`
  are overwritten (`"w"`), not appended, so only `evidence.jsonl` duplicated.
  `ingestion_log.jsonl` is written to commons only — not affected.

## Detection rule

OKRs cannot see this class of bug, because a duplicated record is self-consistent.
The only cheap tell is **run_id multiplicity**:

```python
from collections import Counter
c = Counter(d.get("run_id") for d in records if d.get("run_id"))
dupes = [r for r, n in c.items() if n > 1]
```

Assert **exactly one evidence line per `run_id`** as part of the deep-heartbeat
verification checklist — the same discipline as the corpus-size assertion in the
gzip gotcha. A duplicate `run_id` means a double write, always.

## The fix (applied 2026-10-03)

`cron-heartbeat-deep-dualpath.py` now compares inodes before the second write:

```python
profile_evidence = os.path.join(PROFILE_MENTOR_DATA, "evidence.jsonl")
same_evidence = os.path.exists(profile_evidence) and os.path.samefile(EVIDENCE_LOG, profile_evidence)
if not same_evidence:
    with open(profile_evidence, "a") as f: f.write(json.dumps(evidence_record) + "\n")
```

The OKR write gets the same `os.path.samefile` guard. Verified by re-running the
deep heartbeat: evidence delta went 2 -> 1.

`cron-heartbeat-light.py` needs no fix — it only ever writes to
`AGENT_ROOT/commons/data/mentor`, one path.

## Repairing historical duplicates

Dedupe on `(run_id, json.dumps(record, sort_keys=True))` — the identity must be
run_id **plus** exact payload, or a legitimate second record for the same run (the
`correct_active_skills_30d.py` correction line) gets deleted. Write to a temp file,
`os.replace` atomically, and keep a `.dupbak-<date>` copy first.

## Rules for future work

1. **Never write the same record to two paths without an `os.path.samefile` guard.**
   Two paths that are "canonical" and "profile-scoped" can be one file.
2. **Any two-path write scheme needs a run_id-multiplicity assertion** in its
   verification step. Append-count deltas are ambiguous: delta 2 looks like "script
   + correction," delta 1 looks like "one line," and neither tells you whether a
   duplicate exists.
3. **Symlinks break `ls -ld` comparisons, not `ls -ldi`.** Comparing the two mentor
   data directories always looked fine — two lines, same permissions — because it is
   literally the same directory. Only the inode and `readlink -f` reveal it.