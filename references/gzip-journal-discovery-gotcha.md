# Gzip Compression Silently Truncates the Journal Corpus (confirmed 2026-10-01)

## The defect

`ocas-genie` compresses journals older than its age threshold in place:

```
<journals-root>/<skill>/<date>/<journal>.json  ->  <journal>.json.gz
```

Every Mentor discovery mechanism matched `*.json` / `.jsonl` and nothing else, so the
moment Genie compressed the archive, those journals became **invisible**:

| Surface | Old matcher | Effect after compression |
|---|---|---|
| `cron-heartbeat-deep-dualpath.py` | `fn.endswith((".jsonl", ".json"))` | corpus collapsed |
| `correct_active_skills_30d.py` | `find … -name '*.json'` | active-skill count collapsed |

## Blast radius, measured 2026-10-01

All 17,792 `.gz` files had a **ctime of 2026-10-01** — one Genie run compressed the
whole >7d archive in a single pass.

- Deep heartbeat `journals_scanned`: **38,452 → 3,400** (a 91% silent drop).
- `active_skills_30d`: **21 → 13**.
- OKRs were still reported PASS. `evaluation_coverage` stayed 1.0 because coverage is
  computed over the *files discovered*, so a truncated corpus scores as perfect coverage.
  **A shrinking corpus is the one failure mode the OKRs cannot see.**

Nothing errored. `rc=0`, gap OK, four OKRs green — on 9% of the data.

## Why nothing caught it

- `gzip` preserves the **original mtime**, so a compressed journal keeps a week-old
  mtime and looks unremarkable to `find -mtime`.
- The deep heartbeat's `not_activity_reason`/`gap_detected` logic compares wall-clock
  gaps, not corpus size. A corpus can fall 91% overnight with no gap signal.
- `skills_active_30d` moving 24 → 15 in one run is the *only* visible tell.

## The fix (applied 2026-10-01)

Discovery must match compressed journals and read them transparently:

```python
JOURNAL_SUFFIXES = (".jsonl", ".json", ".jsonl.gz", ".json.gz")

def is_journal_file(filename):
    return filename.endswith(JOURNAL_SUFFIXES)

# in load_journal_entries
if filepath.endswith(".gz"):
    with gzip.open(filepath, "rt", encoding="utf-8", errors="replace") as f:
        content = f.read().strip()
else:
    with open(filepath) as f:
        content = f.read().strip()
```

Both scripts also needed ownership resolved **per file**, from the first path component
relative to the journals root — not from the walk directory:

```python
rel = os.path.relpath(os.path.join(root, fn), base).split(os.sep)
if len(rel) < 2 or not rel[0] or rel[0].startswith("."):
    continue  # journals root itself — no skill owner
names.add(rel[0])
```

This matters because `ocas-genie/runs.jsonl` sits **directly in the skill dir** with no
date subdirectory. Deriving the owner from the walk directory silently dropped it
(a bug I introduced and caught only by diffing the two scripts' name sets).

## Cross-check the two scripts against each other

The deepest cheap guard against this class of bug:

```bash
python3 scripts/correct_active_skills_30d.py   # prints true=NN
# compare NN against the deep run's skills_active_30d
```

Two independent implementations of "count active skills" agreeing is real evidence;
one of them reporting a plausible number is testimony. Verified post-fix: **20 = 20,
zero set difference.**

## Rules for future work

1. **Any new journal-discovery code must accept `.gz`.** Genie compresses in place with
   no marker other than the extension.
2. **Never shell out to `find | grep -oP | sed` for counting.** `correct_active_skills_30d.py`
   did, and it also *ignored its own `JOURNALS_DIRS` constant* (the paths were baked into
   the shell string), which is why the unit tests could not exercise it at all until the
   pipeline was replaced with an `os.walk`.
3. **Assert corpus size against the filesystem.** Independently walk the journals roots
   and compare the file total to the script's `journals_scanned`. A large unexplained
   delta means discovery is broken, whatever the OKRs say.
4. **`evaluation_coverage` is not a data-completeness check.** It is computed over
   discovered files, so it reads 1.0 on a corpus that lost 91% of itself.

## Not a bug: the `mentor-deep-deep-` filename

`references/gotchas-mentor.md` (gotcha 32a) and the operational recipes prescribe
changing the journal filename from `f"mentor-deep-{run_id}.json"` to `f"{run_id}.json"`.
**Do not apply that fix** — it breaks downstream detection. Verification recipes grep
`ls "$JOURNAL_DIR" | grep "mentor-deep-"` (operational-recipes.md:233,291) and
`ocas-dispatch/scripts/scan_eval_missing_journals.py` matches the `mentor-*` family. A
file named `deep-<ts>.json` matches neither. The double prefix is load-bearing; leave it.