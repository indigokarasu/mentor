# Dispatch #98 — Multi-Skill + Email (2026-06-25T12:39Z)

**Trigger:** Dispatcher wave (new_journals + new_emails)

## What Happened

### Forge
- Clean scan, 0 unprocessed proposals (12 total)
- No-op journal written: `forge-scan-20260625T123928Z.json`

### Mentor
- 1208 files scanned via dual-path
- 3 new journals ingested
- `active_skills_30d` script reported 9 (stdin-based, expected wrong)
- **Mandatory correction applied: 9→22** (OCAS: 18)
- Evidence delta: +1 (script) +1 (correction) = +2 total
- Ingestion delta: +3
- Sync to commons: 3 evidence + 4 ingestion lines

### Praxis
- 2 new journals found via mtime, 1 event recorded
- Third-wave mitigation: forge-scan journal + concurrent heartbeat journals (mentor-light-T123533Z, praxis-dispatch-T123608Z) added to eval file
- Eval file: 38,630 lines
- Sync to commons: 12,579 lines (large — accumulated from prior syncs)

### Email Triage
- **Jared**: 0 actionable. All pending follow-ups have `from_me=True` (Jared already responded). 77 messages scanned by triage script.
- **Indigo**: 0 actionable. PR #12 approved (LGTM, merge-blocked by review policy). PR #13 fix for double HTML escaping already pushed (commit `8d874389`). Wikipedia code = security notification.

## Key Learnings

### GitHub API: Review reply ID mismatch

Attempted to reply to a PR #13 review comment via `gh api repos/.../pulls/comments/{review_id}/replies`. The review ID from `pulls/reviews` endpoint (e.g., `4569263999`) returned HTTP 404 "Parent comment not found".

**Root cause:** GitHub's `pulls/reviews` endpoint returns "review" IDs (the overall review submission), not individual "comment" IDs (inline file comments or reply threads). The review's top-level comment has a DIFFERENT ID accessible via `issues/{pr_number}/comments` or `pulls/{pr_number}/comments`.

**Fix:** To reply to a review comment:
1. Get review comments: `gh api repos/.../pulls/{pr_number}/comments` (NOT `/pulls/{pr_number}/reviews`)
2. Find the specific comment by `user.login` and `body` snippet
3. Reply using that comment's ID: `gh api repos/.../pulls/comments/{comment_id}/replies -X POST -f body="..."`

**For top-level review replies:** Use `gh api repos/.../pulls/{pr_number}/reviews/{review_id}/reviews -X POST -body "..."` or simply add a new review.

**Lesson:** Don't assume review IDs work as comment IDs. Always check which endpoint produced the ID before attempting replies.

### Triage script auth issue

`python3 scripts/triage.py --account mx.indigo.karasu@gmail.com` reported "Auth OK: jared.zimmerman@gmail.com" — it used Jared's auth even when targeting Indigo's account. The script likely has a hardcoded credential path or the `--account` flag only affects the search query, not authentication.

**Workaround:** For Indigo's account, check state files directly (`last_email_check_mx_indigo_karasu_gmail_com.json`) and use `gmail_scan.py` with explicit auth.

### Dispatcher `new_files` timestamp mismatch (recurring)

The dispatcher listed `forge-scan-20260625T123928Z.json` in `new_files`, but when Praxis checked the eval file, it was already present (written by a concurrent heartbeat minutes before). The actual file on disk matched the dispatcher's listing, but it had been evaluated before this dispatch ran.

This is the same pattern as dispatch #60, #70, #78 — the dispatcher's `new_files` is a snapshot from its last scan, and concurrent heartbeats can process those journals before the dispatch runs. The correct behavior (already established) is to grep the eval file and skip already-evaluated journals silently.

## Verification

- Forge: journal written ✅
- Mentor: evidence 5119 (+2 from 5117), ingestion 29143 (+3 from 29140), correction 9→22 ✅
- Praxis: eval 38,630 (+3 from 38,627), 1 event, third-wave mitigation ✅
- Email: 0 escalations, state files updated ✅
- Commons sync: 3 evidence + 4 ingestion lines ✅
