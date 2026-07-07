# Ingestion Sync Field Trap (2026-06-28)

**Problem:** The documented timestamp-based commons sync pattern uses `d.get('timestamp','')` for
set-difference. This works for `evidence.jsonl` (field: `timestamp`) but NOT for
`ingestion_log.jsonl` (field: `ingested_at`).

**What happened:**
1. Ran sync with `d.get('timestamp','')` on ingestion_log.jsonl
2. All entries returned EMPTY string for the comparison field
3. `'' < '2026-...'` is True for every line, so ALL 33,766 profile lines were "synced" to commons
4. Commons grew from ~62,624 to 84,416 (massive duplication)
5. My "fix" — deduplicating by `(file, ingested_at)` key — was too aggressive: same journal
   file can be ingested multiple times (different `ingested_at`), but the key treated them
   as duplicates. Result: 84,416 → 19,316 (data loss).

**Correct approach:**
- For `evidence.jsonl`: timestamp field is `timestamp` — use documented pattern
- For `ingestion_log.jsonl`: timestamp field is `ingested_at` — MUST use `d.get('ingested_at','')`
- Dedup key for ingestion should NEVER collapse multiple ingestions of the same file:
  use exact-line dedup only if you must dedup at all.
- Prefer EXACT-LINE dedup over field-based dedup for ingestion logs. Each line is a unique
  ingestion event even if the same file appears multiple times.

**Rule:** Before syncing ANY jsonl file, inspect `head -1 <file> | python3 -c "...print(keys)"`
to confirm the timestamp field name before writing sync logic. Never assume it's `timestamp`.
