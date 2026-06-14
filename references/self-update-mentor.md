# Mentor — Self-Update Procedure

`mentor.update` pulls the latest package from GitHub. Preserves journals and data.

## Quick Path (when working tree is clean)

1. `cd {agent_root}/skills/ocas-mentor`
2. `git fetch origin`
3. Check if local == remote: `git log --oneline -1` vs `git log --oneline origin/main -1`
4. If equal → stop silently
5. `git pull origin main`
6. Write journal, report result

## Full Path (when working tree has local changes)

1. `cd {agent_root}/skills/ocas-mentor`
2. `git fetch origin`
3. Check if local == remote (step 3 above). If equal → stop silently.
4. **Back up local changes** before reset:
   ```bash
   cp -r references /tmp/mentor-refs-backup
   cp -r scripts /tmp/mentor-scripts-backup
   ```
5. **Reset dirty state** (discard uncommitted changes and untracked files):
   ```bash
   git checkout -- .
   git clean -fd
   ```
   NOTE: `git stash` + `git pull` does NOT work when untracked files conflict with incoming files. The stash entry will fail to apply. Use `git checkout -- . && git clean -fd` instead.
6. `git pull origin main`
7. **Compare backups against pulled state** — diff the backup dirs against the pulled dirs. Re-apply any local improvements that were lost:
   ```bash
   diff /tmp/mentor-refs-backup/gotchas-mentor.md references/gotchas-mentor.md
   diff /tmp/mentor-scripts-backup/cron-heartbeat-light.py scripts/cron-heartbeat-light.py
   ```
8. Apply local fixes via `patch()` tool, then `git commit` them.
9. Write journal with `from`, `to`, `merge_commit`, and `local_fix_commit` fields.
10. Report result including which local fixes were re-applied.

## Update Script

`scripts/update.sh` does `git reset --hard HEAD && git clean -fd && git pull` — equivalent to steps 5-6 above but without the backup/re-apply cycle. Use the script only when you know there are no local improvements to preserve. Otherwise use the Full Path.

## Version Check

The `gh api` version check (old step 3) is optional — `git fetch` + comparing `git log` local vs remote is sufficient and doesn't require `gh` CLI.
