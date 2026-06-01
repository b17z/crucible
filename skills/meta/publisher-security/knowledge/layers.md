---
name: Publisher Security Layers
description: Seven-layer defense playbook for maintainers of published packages on PyPI / npm. Reviewer's checklist when publisher-security skill activates.
triggers: [publish, release, layer, hardware-key, branch-protection, provenance, oidc, yank]
type: principle
---

# Publisher Security — Seven Defense Layers

Adversary capabilities to assume:

- Targeted spearphishing with crypto-themed lures
- Account takeover via password-reset / recovery-email chain attacks
- SIM swap of the maintainer's cellular phone number
- Compromise of personal development laptop via:
  - Malicious VS Code / Cursor / browser extension
  - npm/pip postinstall malware in a transitively-pulled dependency
  - Drive-by browser exploit
- OIDC token theft from CI runner memory mid-job
- Modification of `.claude/settings.json` for persistence

The bar is higher than "normal good hygiene."

---

## Layer 1 — Identity (do these this week)

Hardware-key second factor on every account in the recovery chain. The chain is only as strong as its weakest link, and the weakest link is usually the email account used for password resets on the package registries.

- [ ] Hardware key (YubiKey or equivalent) as second factor on:
  - [ ] npm (`npm profile enable-2fa auth-and-writes` with webauthn)
  - [ ] PyPI (webauthn enrolled, all other 2FA disabled)
  - [ ] GitHub (webauthn primary, no SMS, minimal TOTP fallback)
  - [ ] Namecheap / DNS registrar (webauthn)
  - [ ] Cloudflare / CDN (webauthn)
  - [ ] Email provider (webauthn — **this is the recovery chain**)
  - [ ] Password manager (webauthn)
  - [ ] Apple ID (security keys, iOS 16.3+)
- [ ] Two physical hardware keys minimum. One on person, one in a safe.
- [ ] Cell carrier: port-out PIN set, port freeze enabled, verbal auth password set
- [ ] Email separation: dedicated recovery email account, never given out, on a different provider, with its own hardware key
- [ ] Active sessions audit on each service (do this quarterly)

---

## Layer 2 — Workstation (do this month)

Separate the publishing environment from the daily-driver workstation. The publishing environment must have zero IDE extensions. The May 20 2026 GitHub breach used a poisoned VS Code extension on an employee device as initial access.

- [ ] Publishing environment separation:
  - **Option A:** Dedicated Docker container for releases. 1Password CLI for token injection. Rebuilt fresh per release. No web access from inside the container.
  - **Option B:** Dedicated VM or physical Mac for publishing only. Snapshotted before each release.
- [ ] VS Code / Cursor extension audit on the daily-driver machine
  - [ ] `code --list-extensions` review
  - [ ] Pin to specific versions in `.vscode/extensions.json` per project
  - [ ] Disable auto-update globally
- [ ] Publishing environment has **zero IDE extensions**; use a plain editor
- [ ] Filesystem monitoring (osquery + FIM packs) on sensitive paths:
  - `~/.npmrc`, `~/.pypirc`, `~/.gitconfig`, `~/.ssh/`, `~/.claude/`, `~/.config/`
- [ ] Network egress monitoring (Little Snitch on Mac)
- [ ] Persistence monitoring (BlockBlock on Mac)
- [ ] Never paste shell commands without reading; never `curl | sh`

---

## Layer 3 — CI / build (do before next release)

This layer specifically addresses the May 11 2026 Mini Shai-Hulud TTP — OIDC token theft from runner memory mid-job. Trusted publishing is necessary but not sufficient. The defense is workload separation: a build job that has tests in scope but no publish token, and a publish job that has the token but no test code.

- [ ] Pin all GitHub Actions to commit SHA, never tag/branch
  - Use a comment with the human-readable tag for clarity
  - Dependabot will keep SHAs updated with tag context
- [ ] Separate build job from publish job:
  - **Build job:** runs tests, produces artifact, has **no** publish tokens (not even short-lived OIDC)
  - **Publish job:** consumes the artifact only, has the token, runs **no** test code
- [ ] Enable provenance attestations:
  - npm: `npm publish --provenance --access public`
  - PyPI: `pypa/gh-action-pypi-publish` with `attestations: true`
- [ ] Quarterly audit of GitHub Actions secrets; revoke unused

---

## Layer 4 — Source control + namespace reservation (do this week)

Budget realistically: **1-2 hours per repo × 5+ repos ≈ 10 hours of focused work**. This is not an evening task.

For each published repo (crucible, sage, ethereum-mcp, solana-mcp, mcp-hot, others):

- [ ] Branch protection on `main`:
  - [ ] Require PR review (yes, even self-PR — solo maintainer goes through PR)
  - [ ] Require signed commits (hardware key signs)
  - [ ] Require status checks (Crucible's own CI)
  - [ ] Disallow force push
  - [ ] Disallow direct commit to main
- [ ] Secret scanning + push protection enabled
- [ ] Dependabot enabled
- [ ] Code scanning (CodeQL) enabled if applicable

### Namespace reservation (10-minute task, asymmetric payoff)

TeamPCP-style attackers explicitly hunt for naming-window gaps — packages that will be needed but aren't yet claimed.

- [ ] Reserve `crucible-skills-core` on PyPI now with a `0.0.0` placeholder (v2.x extraction will need the name)
- [ ] Audit `crucible` on npm; reserve as a placeholder if unclaimed (typo-squat defense)
- [ ] Audit `@crucible` org on npm; claim if available
- [ ] Verify your own existing names on both registries (crucible-mcp, sage, ethereum-mcp, solana-mcp, mcp-hot) all point to you and aren't shadowed by squatters with similar names

---

## Layer 5 — Release process (codify as runbook)

Per release:

1. Run Crucible on yourself first (this skill activated; review all gaps).
2. Tag release in a signed commit.
3. CI publishes via the separated build/publish jobs with provenance. Uploads the **same artifact** to both PyPI and GitHub Releases.
4. **Post-publish verification:** compare the PyPI artifact to the GitHub Release artifact (NOT to local `dist/` — that would require reproducible builds, which are v2.x roadmap, not v2.0):
   ```bash
   pip download crucible-mcp==$VERSION --no-deps -d /tmp/pypi-verify
   gh release download v$VERSION --pattern "*.whl" --dir /tmp/gh-verify
   sha256sum /tmp/pypi-verify/*.whl /tmp/gh-verify/*.whl
   # Mismatch = compromise between CI build and PyPI publish. Yank immediately.
   ```
5. Update CHANGELOG with the checksum.
6. Monitor package watch for any unexpected subsequent releases (compromised tokens can publish again).

---

## Layer 6 — Incident response (pre-stage now)

Have written runbooks accessible from a phone (not just the laptop the attacker may have compromised) for:

- [ ] npm package yank: `npm deprecate <pkg>@<version> "compromised"`, then email `security@npmjs.com`
- [ ] PyPI yank: via web UI or `pypi-cli`, then email `security@pypi.org`
- [ ] GitHub token revocation order: personal access tokens → SSH keys → OAuth apps → installations
- [ ] User communication template prepared, fill-in-the-blanks: *"If you installed X@Y between A and B UTC, here's what to do"*
- [ ] Contact info for: GitHub security, npm security, PyPI security
- [ ] Practice the runbook quarterly with a simulated compromise

---

## Layer 7 — Meta hygiene (ongoing)

- Quarterly fake-compromise drill — run through Layer 6 end-to-end against a pretend incident
- Monthly read of npm / PyPI / GitHub security advisories
- A trusted second person who can verify a "GitHub security email" before you click — out-of-band check
- **One-month observation period** on new MCP servers / Cursor extensions / VS Code plugins before adoption

---

## Activation reminder

This knowledge file is large by design. Don't load it speculatively. Load it when:

- The session activates `publisher-security` (the project has `[tool.crucible].publishable`)
- The user is touching a release-adjacent file
- The user mentions publish / release / tag / version bump
- The pre-commit hook fires on a `CHANGELOG.md` or `pyproject.toml` change

Otherwise, the layer summaries in the parent `SKILL.md` are sufficient.
