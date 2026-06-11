---
name: Publisher Threat Model
description: Adversary capabilities to assume when reviewing release infrastructure for a published package
triggers: [threat-model, adversary, supply-chain]
type: principle
---

# Publisher Threat Model

Adversary capabilities to assume when reviewing release infrastructure for any project where `[tool.crucible].publishable = true`:

## Targeting

- **Targeted spearphishing** with crypto-themed lures
- **Account takeover** via password-reset / recovery-email chain attacks
- **SIM swap** of the maintainer's cellular phone number
- Whoever has a public-facing developer brand at a crypto/fintech company is in scope

## Endpoint compromise

- **Malicious VS Code / Cursor / browser extension** (May 20 2026 GitHub breach used this exact vector)
- **npm/pip postinstall malware** in a transitively-pulled dependency (March 30 2026 Axios)
- **Drive-by browser exploit**

## CI/CD pipeline compromise

- **OIDC token theft from CI runner memory mid-job** (May 11 2026 Mini Shai-Hulud TTP)
- **Stolen CI/CD token** with credential reuse (the Grafana codebase-exfiltration-via-CI-token extortion case)

## Persistence

- **Modification of `.claude/settings.json`** to install Claude Code hooks that survive `node_modules` purge (TeamPCP-specific TTP, CSA-confirmed May 17 2026)
- **Modification of `~/.npmrc`, `~/.pypirc`, `~/.ssh/`, `~/.gitconfig`** — credential persistence

## Anti-recovery

- **Dead-man's switch** in compromised packages (May 19 2026 wave 2) — wipes the developer's machine if the stolen npm token gets revoked

## State actors

- **Sapphire Sleet (DPRK)** confirmed on Axios. Anyone with a public-facing developer brand at a crypto/fintech company is in scope.
- **TeamPCP** confirmed on Mini Shai-Hulud waves 1+2 + the May 20 GitHub breach. Explicitly targets the AI developer ecosystem.

## What this means for the reviewer

When this threat model is in scope:

1. Don't trust "the build worked, ship it." Trust "the build was produced by a job that has no publish token, and the publish step is a separate job that runs no test code."
2. Don't trust "I checked the source diff." Trust "I checked the source diff *and* the lockfile diff."
3. Don't trust "I have 2FA." Trust "I have hardware-key 2FA across every account in the recovery chain, and the recovery email itself has its own hardware key."
4. Don't trust "the package is signed." Trust "the same artifact appeared in both PyPI and GitHub Releases, and the hashes match."
5. Don't trust "I'd notice if my settings.json changed." Trust "a hash baseline catches it."
