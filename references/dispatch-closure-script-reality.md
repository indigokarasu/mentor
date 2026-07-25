# Dispatch Closure Script Reality (2026-07-23)

When a dispatch wave needs closure — reaching `=== gates ALL CLOSED ===` — the SKILL.md
docs (ocas-mentor AND ocas-forge) repeatedly reference four canonical scripts as the
mandatory primitive:

- `scripts/verify_genuine_gap_profile.py` — assert GENUINE GAP=0
- `scripts/closure_convergence_sweep.py` — iterate bridge to 0 additions
- `scripts/closure_closeout_check.py` — assert all gates (named journal in both
  eval stores, both monitor `latest_mtime` copies, dispatch-owned email
  `verified_second_wave`)
- `scripts/advance_gate_state.py` — recompute max mtime + pad, advance both
  monitor copies (requires `--date`)

**REALITY (corrected 2026-07-23, then PARTIALLY REVERSED 2026-07-23T2325Z):** the
`find` above reported these four files absent from `~/.hermes`, but that search
predates the scripts being added. **As of 2026-07-23T2325Z this was PROVEN FALSE for
two of the four:** `ocas-forge/scripts/verify_genuine_gap_profile.py` and
`ocas-forge/scripts/closure_closeout_check.py` BOTH exist and ran successfully in a live
re-detection closure (used `--date` + `--json` on the verifier, `--named` + `--date` on
the closeout — both returned clean, `=== gates ALL CLOSED ===`). The `find` likely missed
them because they live under `skills/ocas-forge/scripts/` (a different subtree than the
`~/.hermes/commons/...` paths the doc's mental model assumed). **`closure_convergence_sweep.py`
and `advance_gate_state.py` were NOT verified this session** — their existence is still
unconfirmed; do not assume them present.

**Two working closure paths now both exist (2026-07-23T2325Z):**
  - Path A (verified this session): `ocas-forge/scripts/verify_genuine_gap_profile.py`
    (loop until gap==0, `--json` for authoritative list) → `ocas-dispatch/scripts/bridge_eval_both_stores.py`
    (`--action cross_skill_noop_mentor_heartbeat`) → `ocas-dispatch/scripts/advance_closure_gates.py --date <DATE>`
    → `ocas-forge/scripts/closure_closeout_check.py --named <rel> --date <DATE>`.
  - Path B (this doc's original replacement): `ocas-mentor/scripts/dispatch_closure_gap_scan.py --date <DATE>` then `--advance`.
Both are viable; the gap-verifier understates churn (see ocas-dispatch
`session-20260723-combined-redetection-closure.md` churn addendum) so prefer looping
until GENUINE GAP == 0 rather than a single pass.

This is the closure-script analogue of `references/dispatch-bridge-script-reality.md`
(which covers the absent eval-bridge helpers).

## What to do instead (verified working closure, 2026-07-23T0226Z re-detection)

Use `scripts/dispatch_closure_gap_scan.py` — a single-file manual replacement that:

1. Bounded per-skill `os.listdir` walk of `commons/journals/<skill>/<DATE>/*.json`
   over BOTH roots (`~/.hermes/commons/journals` symlink → profile tree, and
   `~/.hermes/profiles/indigo/commons/journals`). Never recursive `**` glob
   (the journals tree nests `journals/journals/...` infinitely elsewhere — but the
   two named roots resolve to the SAME physical tree, so no infinite loop here).
2. Loads both eval stores (`ocas-praxis/journals_evaluated.jsonl` keyed by
   `journal_id`; `ocas-dispatch/journals_evaluated.jsonl` keyed by `filename`)
   and reports GENUINE GAP = journals absent from EITHER store. (Confirmed working 2026-07-23.)
3. Idempotently bridges missing entries into the missing store(s) via
   `scripts/bridge_eval_inline.py` if present (it DOES exist — see the bridge
   reality doc), else inline append. Default `action_taken` =
   `cross_skill_noop_mentor_self_reference` for mentor self-reference heartbeats
   (entities_observed=["ocas-mentor"], gap_detected=false) — DO NOT re-run the
   heartbeat; bridging is the whole job.
4. With `--advance`, recomputes `max(os.path.getmtime(...))` over the scanned
   journals (NEVER hand-typed literal — truncation re-fires the wave forever),
   adds +5s pad, and writes:
   - `ocas-praxis/ingest_state.json:last_ingest_run` = max+pad (ISO)
   - BOTH monitor copies' `latest_mtime`:
     `~/.hermes/commons/data/monitor_state/journal_ingest_state.json`
     AND `~/.hermes/profiles/indigo/commons/data/monitor_state/journal_ingest_state.json`
     (the PROFILE copy is load-bearing; the verifier reads both)
5. Prints gate status: GENUINE GAP count, both monitor >= max, praxis
   `last_ingest_run`. You want `ALL CLOSED: True`.

Usage:
```bash
python3 skills/ocas-mentor/scripts/dispatch_closure_gap_scan.py --date 2026-07-23
# inspect output, then:
python3 skills/ocas-mentor/scripts/dispatch_closure_gap_scan.py --date 2026-07-23 --advance
```

## Email second-wave re-affirmation (same closure)

The <operator>/indigo email `verified_second_wave` flag lives on DISPATCH-OWNED copies:
`commons/data/ocas-dispatch/owner/last_email_check.json` and
`commons/data/ocas-dispatch/last_email_check_owner.json`. These are load-bearing.
The two TOP-LEVEL GWS snapshots (`last_email_check.json`,
`last_email_check_<account-identity>_gmail_com.json`) get CLOBBERED by the scheduled
dispatcher re-firing mid-closure (known monitor re-fire bug) — re-flag them too but
treat as WARN-only. Never recursive-glob `**/last_email_check*.json` (it
over-pertains `indigo/last_email_check.json` and corrupts indigo's genuine state).
Target owner's files by EXPLICIT path only.

## Decision rule this closure used (re-detection, NOT fresh)

If the dispatcher's `new_files` journals ALREADY ran successfully (outcome:success in
the file) and are merely missing from an eval store → **bridge-only** (this doc).
Re-running Forge/Mentor/Praxis here is the prior-wave-misclassification trap the
SKILL.md warns about. Only run genuine pipelines if a journal is absent from BOTH
stores AND has no pre-existing successful run (genuinely new work).
