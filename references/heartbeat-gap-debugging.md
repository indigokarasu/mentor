# Mentor Heartbeat Gap Debugging Reference

## Gap Detection in Evidence Log

When Mentor's light heartbeat detects a gap >15 minutes, it should log `gap_detected: true` and run a remedial pass. However, large gaps (e.g., 779 minutes / ~13 hours) indicate either:

1. **The heartbeat cron job was disabled or misconfigured** — check `jobs.json` for `mentor:light` status
2. **The gateway was down** — check gateway process and logs for the gap window
3. **The evidence log write failed silently** — the heartbeat ran but failed to write evidence (check for crashes or timeouts)

## Pattern from 2026-05-29

A 779-minute gap was observed in the evidence log:
- Last entry before gap: `2026-05-29T11:27:33Z`
- Next entry after gap: `2026-05-30T00:29:46Z`

**Diagnostic steps:**
1. Check gateway uptime: `terminal(command="ps aux | grep hermes")`
2. Check if mentor:light job ran: `terminal(command="cat /root/.hermes/cron/jobs.json | python3 -c \"import json,sys; d=json.load(sys.stdin); jobs=d.get('jobs',d.get('tasks',[])); [print(j.get('name'), j.get('last_status'), j.get('last_run_at')) for j in jobs if 'mentor' in j.get('name','')]\"")`
3. Check cron_jobs.log for the gap window: `terminal(command="grep mentor /root/.hermes/logs/cron_jobs.log | tail -20")`
4. If gateway was down, no remedial action needed — heartbeats resume automatically on restart
5. If gateway was up but heartbeat didn't fire, check for `cron: skipping disabled job` or errors in gateway log

## Large Gaps (>2 hours)

For gaps exceeding 2 hours:
- The system was likely in a low-activity period overnight
- Light heartbeats run every 5 minutes during active periods, but may be suppressed during quiet hours
- Check if the gap corresponds to a known quiet window (22:00-08:00 PT)
- If the gap is during active hours, this is a potential heartbeat failure — monitor next few cycles
