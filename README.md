# 🎓 Mentor

Orchestration, evaluation, and skill improvement engine.

**Skill name:** `ocas-mentor`
**Version:** 2.2.0
**Type:** system
**Layer:** System Evolution
**Author:** Indigo Karasu

---

## Files

| File | Purpose |
|---|---|
| `skill.json` | Package metadata and routing description |
| `SKILL.md` | Operational instructions for the agent |
| `references/` | Support files referenced by SKILL.md |

---

## Changelog

### 2.2.0 (2026-03-22)

- Added short-name routing aliases to skill.json description and SKILL.md frontmatter for natural invocation ('Scout', 'Sift', etc.)
- Added trigger phrases to descriptions for improved routing accuracy
- Cross-skill references in descriptions now use 'use X' format for routing clarity

### 2.1.0 (2026-03-22)

- Added Run completion section with explicit Forge intake emission and journal write
- Added Initialization section with cron/heartbeat registration
- Added Background tasks section: mentor:deep (daily 5am cron), mentor:light (heartbeat)
- Removed non-conformant OCAS_ROOT environment variable reference

### 2.0.0 (2026-03-18)

- Initial build of all OCAS skills as a unified suite
