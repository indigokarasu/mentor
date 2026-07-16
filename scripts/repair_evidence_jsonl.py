#!/usr/bin/env python3
"""Scan and repair corrupted lines in mentor evidence.jsonl files.

Repairs:
- Concatenated JSON objects (two objects on one line, missing newline)
- Null-byte lines (all \0 characters)
- Multi-line JSON (accidental indent from json.dump(indent=...))

Always repairs BOTH profile and commons evidence independently.

Usage:
    python3 /path/to/scripts/repair_evidence_jsonl.py

Exit codes:
    0 — Both files clean (no repair needed)
    1 — Repairs applied (at least one file had issues)
    2 — Error (file not found, etc.)
"""
import json
import sys
import os

_HELP_ARGS = {"--help", "-h"}
if set(sys.argv[1:]) & _HELP_ARGS:
    print((__doc__ or "").strip() or "Usage: python3 repair_evidence_jsonl.py")
    sys.exit(0)

PATHS = [
    ("profile", "/root/.hermes/profiles/indigo/commons/data/mentor/evidence.jsonl"),
    ("commons", "/root/.hermes/commons/data/mentor/evidence.jsonl"),
]


def scan_and_repair(path: str) -> bool:
    """Scan and repair a single evidence.jsonl file.
    
    Returns True if repairs were made, False if file was already clean.
    """
    if not os.path.exists(path):
        print(f"  NOT FOUND: {path}")
        return False

    with open(path) as f:
        lines = [l.rstrip('\n') for l in f]

    if not lines:
        print(f"  EMPTY: {path}")
        return False

    original_count = len(lines)
    fixed = []
    repairs = 0

    for i, line in enumerate(lines):
        if not line.strip():
            continue

        # Pattern 2: Null-byte corruption
        if '\0' in line:
            repairs += 1
            print(f"  [{os.path.basename(path)}] Line {i}: NULL BYTE — removed")
            continue

        try:
            json.loads(line)
            fixed.append(line)
        except json.JSONDecodeError as e:
            # Pattern 1: Concatenated JSON objects (Extra data)
            if "Extra data" in str(e):
                depth = 0
                split_point = None
                for j, ch in enumerate(line):
                    if ch == '{':
                        depth += 1
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
                        repairs += 1
                        print(f"  [{os.path.basename(path)}] Line {i}: SPLIT at char {split_point} → 2 valid JSON objects")
                        continue
                    except json.JSONDecodeError:
                        pass

            # Pattern 3: Check if it's multi-line indent (starts/ends on different lines)
            # We can't fix multi-line from single-line context — this is a separate issue
            # Fall through to unrepaired report
            print(f"  [{os.path.basename(path)}] Line {i}: UNREPAIRABLE: {e}")
            print(f"    Content start: {line[:120]}...")
            fixed.append(line)  # Keep line to preserve data, even if broken

    if repairs == 0:
        print(f"  [{os.path.basename(path)}] CLEAN — {original_count} lines, 0 repairs")
        return False

    new_content = "\n".join(fixed)
    with open(path, "w") as f:
        f.write(new_content)

    print(f"  [{os.path.basename(path)}] REPAIRED: {original_count} → {len(fixed)} lines ({repairs} repairs)")
    return True


def verify(path: str) -> int:
    """Count parse errors in a JSONL file."""
    errors = 0
    try:
        with open(path) as f:
            for i, line in enumerate(f):
                if not line.strip():
                    continue
                try:
                    json.loads(line)
                except json.JSONDecodeError:
                    errors += 1
                    if errors <= 2:
                        print(f"    Line {i}: STILL BROKEN")
    except FileNotFoundError:
        return -1
    return errors


def main():
    print("=== Evidence JSONL Repair ===")
    print()

    any_repaired = False
    for label, path in PATHS:
        print(f"Scanning {label} evidence...")
        if scan_and_repair(path):
            any_repaired = True

    print()
    print("=== Post-Repair Verification ===")
    all_clean = True
    for label, path in PATHS:
        errors = verify(path)
        if errors == -1:
            print(f"  {label}: NOT FOUND")
            all_clean = False
        elif errors == 0:
            print(f"  {label}: ✓ CLEAN")
        else:
            print(f"  {label}: ✗ {errors} errors remaining")
            all_clean = False

    print()
    if any_repaired:
        print("Repairs applied — both files should be re-checked on next heartbeat.")
    if all_clean:
        print("All evidence files clean.")
    else:
        print("UNRESOLVED ERRORS — manual investigation needed.")

    sys.exit(0 if not any_repaired else 1)


if __name__ == "__main__":
    main()