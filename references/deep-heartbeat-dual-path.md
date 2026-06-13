# Mentor — Deep Heartbeat Dual-Path Script (2026-06-08)

## Purpose
Documents the custom deep heartbeat approach that properly handles dual-path journal scanning, replacing the stock `cron-heartbeat-deep.py` which only scans the commons path (gotcha #32).

## Stock Script Limitations
1. **Single-path scan** — only walks `/root/.hermes/commons/journals/`, missing ~50% of journals under `/root/.hermes/profiles/indigo/commons/journals/`
2. **`os.walk` unreliable in cron** — silently returns 0 results in cron `terminal()` heredocs (gotcha #17)

## Dual-Path Dedup Pattern
```python
COMMONS_JOURNALS = "/root/.hermes/commons/journals/"
PROFILE_JOURNALS = "/root/.hermes/profiles/indigo/commons/journals/"

def compute_dedup_key(fp):
    for root in [COMMONS_JOURNALS, PROFILE_JOURNALS]:
        if fp.startswith(root):
            rel = os.path.relpath(fp, root)
            mtime = os.path.getmtime(fp)
            file_hash = hashlib.md5(rel.encode()).hexdigest()[:12]
            return f"{file_hash}_{int(mtime)}"
    return None

def get_skill_name(fp):
    for root in [COMMONS_JOURNALS, PROFILE_JOURNALS]:
        if fp.startswith(root):
            rel = os.path.relpath(fp, root)
            parts = rel.split(os.sep)
            if parts and not parts[0].startswith('.'):
                return parts[0]
    return "unknown"
```

## Shell-Level Dual-Path Discovery (MUST use parentheses for -o)
```bash
find /root/.hermes/commons/journals/ \
    \( -name "*.json" -o -name "*.jsonl" \) \
    -not -path "*/.archive/*" -not -path "*/.quarantine/*" \
  > /tmp/deep_files_commons.txt

find /root/.hermes/profiles/indigo/commons/journals/ \
    \( -name "*.json" -o -name "*.jsonl" \) \
    -not -path "*/.archive/*" -not -path "*/.quarantine/*" \
  > /tmp/deep_files_profile.txt

cat /tmp/deep_files_commons.txt /tmp/deep_files_profile.txt | sort -u > /tmp/deep_files_all.txt
```

## Results (2026-06-08 Run)
- Total files: 11,988 (commons: 6,046 + profile: 5,942)
- New entries ingested: 472 across 16 skills
- Parse errors/quarantined: 15
- OKRs: All passing (orchestration_success_rate=0.9979, error_rate=0.0021)
- Anomalies: 0 new, 3 stale from prior runs

## New Gotchas Discovered This Session

### Gotcha #47: `find -o` Precedence
`find ... -name "*.json" -o -name "*.jsonl" -not -path "*/.archive/*"` does NOT filter `.archive` from `.json` files. `-not -path` only applies to the `-name "*.jsonl"` branch. **Always use parentheses:** `\( -name "*.json" -o -name "*.jsonl" \) -not -path "*/.archive/*"`.

### Gotcha #48: Dedup Key Must Try Both Roots
Using only `COMMONS_JOURNALS` as root makes profile paths resolve to `..` (skipped). Files appear "new" every heartbeat. **Fix:** Try both roots, skip if relpath starts with `..`.

### Gotcha #49: Null-Key Anomaly Accumulation
Anomaly entries with `key: null` are never cleaned up. **Fix:** Filter them during each deep heartbeat pass:
```bash
python3 -c "import json; lines=[l for l in open('anomalies.jsonl') if json.loads(l.strip()).get('key')]; open('anomalies.jsonl','w').writelines(lines)"
```

## Recommendation
The stock `scripts/cron-heartbeat-deep.py` single-path `os.walk` has been confirmed broken across 5+ runs. Replace with this dual-path approach.
