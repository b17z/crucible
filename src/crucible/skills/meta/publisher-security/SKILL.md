---
name: publisher-security
description: Self-applied review for projects that publish to PyPI / npm — hardware keys, CI hardening, release runbook, IR pre-staging. Use when working on release-adjacent files (release/publish workflows, pyproject.toml, package.json, CHANGELOG) or a prompt about publishing/releasing/tagging/version-bumping, AND the project has opted in via [tool.crucible].publishable. Do NOT use for internal/closed projects (it stays dormant without the flag) or for reviewing application code — it reviews the release supply chain, not features.
version: "2.0"
---

# Publisher Security

You are reviewing this repo from the perspective of a maintainer who has to assume:

- Targeted spearphishing with crypto-themed lures will be attempted
- Account takeover via password-reset / recovery-email chain attacks will be attempted
- SIM swap of the maintainer's cell number is plausible
- Personal-laptop compromise via malicious IDE extension or postinstall malware is in scope
- OIDC token theft from CI runner memory has been demonstrated by TeamPCP

The bar is higher than "normal good hygiene." The Axios maintainer (March 2026) was operating at good-hygiene level when he was compromised by Sapphire Sleet. State actors are spearphishing maintainers in this exact profile.

## Activation gate

This skill activates **only when the project explicitly declares itself as publishable.** Either:

```toml
# pyproject.toml
[tool.crucible]
publishable = true
publishers = ["pypi", "npm"]  # optional; targets the layer 3/5 knowledge
```

```json
// package.json
{
  "crucible": {
    "publishable": true,
    "publishers": ["npm"]
  }
}
```

If the flag isn't set but the project has a `version` field plus a `[project.entry-points]` / `bin` / `publishConfig`, Crucible **suggests** enabling the flag at session start but does not auto-enable. Random users on internal/closed projects shouldn't be nagged about npm provenance attestations.

## What this skill reviews

When activated, walk the layered defense in `knowledge/layers.md` and check:

1. Are GitHub Actions pinned to commit SHA (not tag/branch)?
2. Is the publish job separated from the build job? Does the build job have any publish tokens in scope?
3. Are provenance attestations enabled (`npm publish --provenance --access public`; `pypa/gh-action-pypi-publish` with `attestations: true`)?
4. Is the version bump a signed commit?
5. Has the release-day checksum verification step been added to the release runbook?
6. Is branch protection on `main` set to require signed commits + PR review + status checks + no force-push + no direct commits?
7. Is the workstation separation pattern in place — dedicated publish container/VM with zero IDE extensions?

Items 1-3 and 6 are reviewable from the repo state. Items 4-5 and 7 require the maintainer to confirm; flag them as "verify before next release" rather than as code findings.

## Knowledge

- `knowledge/layers.md` — the seven defense layers (identity, workstation, CI, source-control + namespace, release runbook, IR pre-staging, meta hygiene). The actionable checklist.
- `knowledge/threat-model.md` — adversary capabilities to assume.

## Output Format

When reviewing a publisher project:

### Critical gaps
Anything that, if it were true today, would allow a published-package compromise. Branch protection missing, build/publish jobs not separated, version commits unsigned.

### High-priority gaps
Items that don't directly enable compromise but materially reduce defense in depth. Missing IR runbook, no quarterly drill cadence, IDE extensions on the publish environment.

### Acknowledged-only items
Things the maintainer has to confirm by hand. Hardware key 2FA across all services, port-out PINs at the cell carrier, etc. List them; don't mark them as findings.

### Approval status
- APPROVE: layers 1-7 are in place and recently verified.
- REQUEST CHANGES: any critical gap.
- COMMENT: high-priority gaps only.
