# Gotcha: Error Grep False Positives in Heartbeat Scans

**Discovered:** 2026-06-16T12:22Z (light heartbeat)

## Problem

When scanning recent journals for urgent issues using `grep -q '"error"'`, journals from ocas-finch and ocas-custodian matched despite being successful runs. These journals contain the word "error" in their content (e.g., reporting on errors detected in other skills, or containing field names like `"error_count"`), but the journals themselves have `outcome: "success"`.

## Impact

- False positive error reports in heartbeat output
- Wasted diagnostic time investigating non-issues
- Potential for unnecessary escalation

## Safe Pattern

Instead of grepping for `"error"` in journal content, parse the JSON and check the `outcome` field:

```bash
# WRONG — matches content containing "error" anywhere
grep -q '"error"' "$file"

# RIGHT — checks actual outcome
python3 -c "
import json
with open('$file') as f:
    d = json.load(f)
outcome = d.get('outcome', 'unknown')
if outcome in ('failure', 'error', 'failed'):
    print(f'ACTUAL ERROR: {outcome}')
" 2>/dev/null
```

Or for a quick shell check that's safer than grep:
```bash
# Check for explicit failure outcomes only
grep -q '"outcome"[[:space:]]*:[[:space:]]*"\(failure\|error\|failed\)"' "$file"
```

## Affected Skills

Skills whose journals are likely to contain "error" in content without being error journals:
- **ocas-finch**: Reports on errors detected in other skills
- **ocas-custodian**: Contains error field names in structured output
- **ocas-mentor**: May reference error counts in metrics

## Recommendation

In heartbeat urgent-issue scans, always parse JSON and check `outcome` field rather than grepping for "error" in raw content. Reserve content-level error grepping for post-mortem analysis where false positives are acceptable.
