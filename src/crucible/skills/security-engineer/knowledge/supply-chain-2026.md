---
name: Supply Chain 2026
description: May 2026 supply-chain threat landscape — Axios, Mini Shai-Hulud, GitHub breach, CVE-2026-3854, and the cross-cutting TTPs to encode in review
triggers: [supply-chain, dependency, npm, pip, postinstall, package-json, lockfile, ci, oidc, github-actions, vscode-extension, claude-settings]
type: principle
---

# Supply Chain 2026

The 2026 supply-chain threat picture is materially worse than 2024-2025.
State actors are spearphishing high-value maintainers. AI is writing the
malicious payloads. Claude Code users — and anyone with a public-facing
developer brand at a crypto company — are explicitly in scope.

Load this knowledge when reviewing **any** of:

- Changes to `package.json`, `package-lock.json`, `requirements*.txt`,
  `pyproject.toml`, `Cargo.toml`, `go.mod`
- CI workflow changes (`.github/workflows/`, `.gitlab-ci.yml`)
- Bash commands that touch `npm install`, `pnpm add`, `pip install`,
  `cargo add`, or write to `~/.npmrc`, `~/.pypirc`, `~/.ssh/`, `~/.claude/`
- Anything that adds, updates, or executes a dependency

## Major incidents (last 90 days, chronological)

### March 30-31, 2026 — Axios npm compromise

- **Package:** `axios` (~100M weekly downloads)
- **Actor:** Sapphire Sleet (North Korean state actor)
- **Initial access:** spearphish of lead maintainer + RAT on their personal device
- **Payload:** phantom dependency `plain-crypto-js@4.2.1` injected; postinstall hook deployed a cross-platform RAT (Windows/macOS/Linux) that self-destructed by overwriting itself with clean decoys
- **Defense bypass:** OIDC trusted publishing was already enabled, but the manual-publish path doesn't go through OIDC. Attacker manually published using stolen npm token.
- **Window:** live for ~3 hours before takedown

### May 11, 2026 — Mini Shai-Hulud wave 1

- **Actor:** TeamPCP
- **Scope:** `@tanstack/react-router` and ~169 npm packages
- **Novel TTP:** stole OIDC tokens **from GitHub Actions runner memory during the job**. The OIDC token, however short-lived, exists in runner memory during execution and can be lifted by any code running in that runner.
- **Implication:** "trusted publishing" is necessary but not sufficient. The build-and-publish split (build job has no publish token in memory) is the actual defense.
- **Detection lag:** affected packages had valid cryptographic provenance attestations — the attestations covered malicious code.

### May 17, 2026 — CSA research note on AI developer targeting

- **Source:** Cloud Security Alliance
- **Finding:** TeamPCP is explicitly targeting the AI developer ecosystem.
- **Specific TTP:** malware modifies `.claude/settings.json` to install
  persistence hooks that **survive a `node_modules` purge**.
- **Implication:** the standard "delete `node_modules`, reinstall" recovery
  step does not clean this category of compromise. Claude Code users are
  an explicit target group.

### May 19, 2026 — Mini Shai-Hulud wave 2

- **Actor:** TeamPCP
- **Scope:** the `@atool` maintainer account (547 packages); 300+ malicious package versions across 323 packages published in a 22-minute automated burst
- **Reach:** ~16M weekly downloads affected; AntV ecosystem, `echarts-for-react`, Microsoft's `durabletask` SDK among the hit packages
- **Novel TTP:** **dead-man's switch** that wipes the developer's machine if the stolen npm token gets revoked. Yanking compromised packages is no longer a clean rollback path.

### May 20, 2026 — GitHub itself breached

- **Actor:** TeamPCP (same group as Mini Shai-Hulud)
- **Claim:** ~3,800-4,000 internal GitHub repositories + proprietary GitHub source code
- **Attack vector:** poisoned VS Code extension on a GitHub employee's device
- **Status:** GitHub confirmed device compromise and exfiltration of internal repos; no confirmed customer impact as of this writing. Secrets being rotated.

### Background — CVE-2026-3854

- **Type:** Critical RCE in GitHub's internal git infrastructure
- **Discovered by:** Wiz Research, using AI-assisted analysis
- **Effect:** any authenticated user with push access could execute arbitrary commands on backend storage nodes, with **cross-tenant repo access**
- **Status:** patched on GitHub.com; self-hosted GHES instances may remain vulnerable

### Background — Grafana CI/CD token extortion

- Grafana's internal codebase was exfiltrated via a stolen CI/CD token.
- A threat group attempted extortion off the stolen source.
- Takeaway: a single leaked CI/CD token is enough to exfiltrate a whole
  internal codebase. Anyone with a public-facing developer brand —
  especially in crypto/fintech, where threat-actor interest is highest —
  should treat themselves as in scope. Scope and rotate CI tokens
  aggressively; a build token should never be able to read the whole repo
  history if it only needs to publish.

## Cross-cutting attack patterns

### 1. Postinstall hooks are the universal vector

Any npm/pip package can run arbitrary code on install. The defense is `--ignore-scripts` for unknown deps, then explicit re-enable after audit. When reviewing a new dependency, ask: does it have a postinstall script? Has the postinstall been read and understood?

### 2. Phantom dependency injection

Attackers add a *new* dep to a compromised package, where the new dep is the actual malware carrier. The original package looks normal at the code-diff-review level — only the lockfile diff shows the new dependency.

**Mitigation:** review `package.json` AND lockfile diffs together, not just source code diffs. The lockfile is the ground truth.

### 3. OIDC token theft from CI runner memory

Trusted publishing is necessary but not sufficient. The token exists in runner memory during the job; any code running in that runner can lift it.

**Mitigation:** separate build job (runs tests, produces artifact, no publish tokens) from publish job (consumes artifact, has token, runs no test code). The build job cannot leak the publish token because it never has one.

### 4. VS Code / IDE extensions as initial access

Marketplace vetting is minimal. Extensions run with full filesystem access. The GitHub breach (May 20) used a poisoned extension on an employee device as initial access.

**Mitigation:** extension audit (`code --list-extensions`), pin to specific versions in `.vscode/extensions.json`, disable auto-update. **Publishing environment must have zero IDE extensions.**

### 5. `.claude/settings.json` modification as persistence

TeamPCP-specific TTP. The malware modifies `.claude/settings.json` to install persistence hooks that survive `node_modules` purge.

**Mitigation:** file integrity monitoring with cryptographic hash + alert on unexpected modification. Crucible v2 ships `interfaces/claude_code/file_changed/settings_integrity.sh` for exactly this. The baselines live at `.crucible/baselines/` (initialized via `crucible baselines init`).

### 6. AI-generated attack code

Unit 42 has moderate-confidence attribution that LLMs are writing the malicious payloads. The arms race is now AI vs AI.

**Implication for detection:** rules need to evolve as fast as attack patterns. Static knowledge files (like this one) age. v2.x roadmap includes a versioned threat-feed mechanism where bundled `supply-chain-2026.md` ages out and prompts an update. v2.0 ships a static snapshot; treat any incident >90 days old in this file as historical, not current.

### 7. State actors are in scope

Sapphire Sleet (DPRK) on Axios. This shifts the threat model from "opportunistic" to "**targeted spearphishing of high-value maintainers**." Anyone with:

- A public-facing developer brand
- A presence at a crypto/fintech company
- Maintainer or publish rights on a high-download package

...is in scope. Personal-device compromise via spearphish is the entry. Don't assume "I'm too small to target." The Axios maintainer was operating at normal-good-hygiene security level when he was compromised.

## What this means for a code review

When you see a change that touches any of the surfaces listed at the top of this file, ask:

1. **Where does this dependency come from?** Is the publisher who they say they are? When did the current version land? Is the package's GitHub repo activity consistent with the published version?
2. **What postinstall script does this dependency run?** Has it been read?
3. **What lockfile changes accompany this change?** Are any new transitive dependencies appearing that the source-code diff doesn't justify?
4. **What CI permissions does this code path execute under?** Does a test-running job have access to a publish token that should be isolated?
5. **What persistence surfaces does this touch?** Anything writing to `~/.claude/`, `~/.npmrc`, `~/.pypirc`, `~/.ssh/`, `.mcp.json`, `.vscode/extensions.json` is suspect.

Findings here are HIGH severity by default. The cost of a false negative in this category is account takeover or machine compromise. The cost of a false positive is a five-minute discussion. The asymmetry favors flagging.
