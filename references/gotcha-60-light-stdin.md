# Gotcha #60: Light Heartbeat Script Only Accepts Stdin Pipe — No CLI Args

## Problem

Invoking `cron-heartbeat-light.py` with `--files-from` (or any CLI argument) for the file list:

    python3 cron-heartbeat-light.py --files-from /tmp/mentor_files_3d.txt

Output: "Recent journal files scanned: 0" — the script ignores the argument, reads stdin (empty), processes 0 files.

## Root Cause

The script's `main()` reads from `sys.stdin` — it has no CLI argument parsing. File paths MUST come through the pipe.

## Correct Pattern

    # Step 1: Write file list to /tmp
    find /root/.hermes/commons/journals/ /root/.hermes/profiles/indigo/commons/journals/ \
      -name "*.json" -mtime -3 2>/dev/null | sort -u > /tmp/mentor_files_3d.txt

    # Step 2: Pipe into script
    cat /tmp/mentor_files_3d.txt | python3 /path/to/cron-heartbeat-light.py

Confirmed 2026-06-15: `--files-from`, `--input`, and positional args all silently ignored. Only stdin pipe works.
