# Mentor Light Heartbeat — Quick Reference Card

## Dispatch-Mode Caller Workflow (canonical)

1. **Build dual-path 3-day list:**
   ```bash
   find /root/.hermes/commons/journals/ /root/.hermes/profiles/indigo/commons/journals/ \
     -name "*.json" -mtime -3 | sort -u > /tmp/mentor_files_3d.txt
   ```

2. **Record pre-run counts (PROFILE path):**
   ```bash
   EVIDENCE_BEFORE=$(wc -l < /root/.hermes/profiles/indigo/commons/data/mentor/evidence.jsonl)
   ```

3. **Run script:**
   ```bash
   cat /tmp/mentor_files_3d.txt | python3 scripts/cron-heartbeat-light.py
   ```

4. **Verify evidence grew** (delta should be ≥1):
   ```bash
   EVIDENCE_AFTER=$(wc -l < .../evidence.jsonl)
   # If delta=0: write backup evidence
   ```

5. **MANDATORY correction** (always, even when script succeeds):
   ```bash
   python3 scripts/correct_active_skills_30d.py
   ```
   Script's count (9–14) is WRONG. True count is 18–22. Confirmed 41+ times.

6. **Cross-reference ingestion** (trust `new_files_ingested` unless `wc -l` shows 0 delta).

7. **DO NOT write a separate journal** — the script's journal is canonical.

## Anti-Reflex Checkpoint
After steps 1–6, you WILL feel an urge to compose a "proper" journal. RESIST. Record additional context in the evidence record, NOT as a journal file.
