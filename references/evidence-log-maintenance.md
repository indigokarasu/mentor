# Evidence Log Maintenance

## When to Use

- `json.loads()` fails on evidence.jsonl or ingestion_log.jsonl
- Heartbeat crashes on gap detection due to unparseable last line
- Evidence scanner reports "Extra data" or "Expecting value" errors
- `wc -l` doesn't match parseable-line count

## Corruption Patterns

### Pattern 1: Concatenated JSON Objects (most common)

Two JSON objects on the same line, missing the newline separator between `}{`.

**Root cause:** Python `with open()` write race in cron mode — two writes happened without an intervening newline.

**Detection with `tail -1 | python3 -c "import sys,json; json.loads(sys.stdin.read())"`** — raises `Extra data` error.

**Fix — brace-depth scan (safe, reliable):**
```python
def split_concatenated_json(line):
    """Split a line containing two JSON objects at the } boundary."""
    depth = 0
    for j, ch in enumerate(line):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and j < len(line) - 1:
                first = line[:j+1]
                second = line[j+1:]
                try:
                    json.loads(first)
                    json.loads(second)
                    return [first, second]
                except json.JSONDecodeError:
                    pass
    return [line]
```

### Pattern 2: Null-Byte Corruption

A line consisting entirely of `\0` (null) bytes.

**Detection:** `'\0' in line` or `all(ord(c) == 0 for c in line)`

**Fix:** Remove the line entirely.

### Pattern 3: Multi-Line JSON (accidental indent)

Single JSON object split across multiple lines due to `json.dump(record, f, indent=2)` being appended to a JSONL file.

**Detection:** `wc -l` expected is 1 but actual is N > 1.

**Fix:** Remove the multi-line block and rewrite as single-line JSON (`json.dumps(record)` without indent).

## Full Scan-and-Repair Procedure

```python
import json

path = "/root/.hermes/profiles/indigo/commons/data/mentor/evidence.jsonl"

with open(path) as f:
    lines = [l.rstrip('\n') for l in f]

fixed = []
for i, line in enumerate(lines):
    if not line.strip():
        continue
    if '\0' in line:
        print(f"Line {i}: NULL BYTE — removed")
        continue
    try:
        json.loads(line)
        fixed.append(line)
    except json.JSONDecodeError as e:
        if "Extra data" in str(e):
            depth = 0
            split_point = None
            for j, ch in enumerate(line):
                if ch == '{': depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0 and j < len(line) - 1:
                        split_point = j + 1
                        break
            if split_point:
                first = line[:split_point]
                second = line[split_point:]
                try:
                    json.loads(first)
                    json.loads(second)
                    fixed.append(first)
                    fixed.append(second)
                    print(f"Line {i}: SPLIT at {split_point}")
                    continue
                except:
                    pass
            print(f"Line {i}: UNREPAIRABLE — {e}")
        else:
            print(f"Line {i}: UNREPAIRABLE — {e}")

new_content = "\n".join(fixed)
with open(path, "w") as f:
    f.write(new_content)

print(f"Repaired: {len(lines)} → {len(fixed)} lines")
```

## Dual-Repair Requirement

Both profile and commons evidence must be repaired independently:

| Path | Purpose |
|------|---------|
| `profiles/indigo/commons/data/mentor/evidence.jsonl` | Authoritative (profile) |
| `commons/data/mentor/evidence.jsonl` | Lagging copy (commons) |

Repairing one does NOT fix the other. The sync is append-only and does not overwrite existing corrupt lines.

**Confirmed 2026-07-01:** Same concatenation appeared in both files; required independent repair.

## Verification

```bash
python3 -c "
import json
errors = 0
with open('/path/to/evidence.jsonl') as f:
    for i, line in enumerate(f):
        if not line.strip(): continue
        try: json.loads(line)
        except json.JSONDecodeError: errors += 1
print(f'{errors} errors remaining')
"
```

Expected: `0 errors remaining`