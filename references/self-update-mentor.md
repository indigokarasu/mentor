# Mentor — Self-Update Procedure

`mentor.update` pulls the latest package from GitHub. Preserves journals and data.

1. Read `source:` from frontmatter → extract `{owner}/{repo}` from URL
2. Read local version from SKILL.md frontmatter `metadata.version`
3. Fetch remote version: `gh api "repos/{owner}/{repo}/contents/SKILL.md" --jq '.content' | base64 -d | grep 'version:' | head -1`
4. If remote equals local → stop silently
5. `cd {agent_root}/skills/ocas-mentor && bash scripts/update.sh`
6. On failure → retry once, then report error
7. Output exactly: `I updated Mentor from version {old} to {new}`
