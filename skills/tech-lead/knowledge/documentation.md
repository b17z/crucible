---
name: Documentation
description: Code comments, READMEs, API docs, architecture docs
triggers: [docs, documentation, readme, comments]
type: preference
---

# Documentation Principles

What to document, where to put it, and how to keep it useful.

---

## The Docs Folder

```
docs/
├── FEATURES.md      # What the project does (capabilities)
├── ROADMAP.md       # What's planned (timeline + status)
├── ARCHITECTURE.md  # How it works (diagrams + data flow)
└── design-*.md      # Decision docs for specific features
```

---

## FEATURES.md

Complete reference for all capabilities.

```markdown
# Project Features

## Overview
[ASCII diagram showing the system]

## Feature Category 1

### Feature A
- What it does
- How to use it
- Configuration options

### Feature B
...

## CLI Commands
| Command | Purpose |
|---------|---------|
| `cmd list` | List items |
| `cmd add` | Add item |
```

---

## ROADMAP.md

Version timeline and planned features.

```markdown
# Roadmap

## Current: vX.Y (Month Year)

### What's Shipped
| Feature | Status | Notes |
|---------|--------|-------|
| Feature A | Done | Details |
| Feature B | Done | Details |

## vX.Z (Planned)

### Focus: Theme
| Feature | Description |
|---------|-------------|
| Feature C | What it will do |

## Version History
| Version | Date | Highlights |
|---------|------|------------|
| v1.0 | Jan 2026 | Initial release |
```

---

## ARCHITECTURE.md

System design and data flow.

```markdown
# Architecture

## Overview
[ASCII or Mermaid diagram]

## Components
| Component | Purpose |
|-----------|---------|
| api/ | HTTP handlers |
| core/ | Business logic |

## Data Flow
[Sequence diagram]

## File Structure
```
src/
├── api/      # HTTP layer
├── core/     # Business logic
└── db/       # Database access
```
```

---

## Design Docs

For significant decisions:

```markdown
# Design: Feature Name

## Context
What problem are we solving?

## Options Considered
1. **Option A**: Pros/cons
2. **Option B**: Pros/cons

## Decision
We chose Option A because...

## Consequences
- Positive: X
- Negative: Y
- Neutral: Z
```

---

## README.md

Quick start only:

```markdown
# Project Name

One-line description.

## Quick Start
\`\`\`bash
pip install project
project init
\`\`\`

## Documentation
- [Features](docs/FEATURES.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)
```

---

## CLAUDE.md

Project context for AI assistants:

```markdown
# Project Name

Brief description.

## Quick Reference
\`\`\`bash
command1  # What it does
command2  # What it does
\`\`\`

## Project Structure
[Concise overview]

## Patterns
[Code conventions used]

## Development
[How to run/test]
```

---

## Keep Docs Current

```
- Update FEATURES.md when shipping
- Update ROADMAP.md when planning
- Update ARCHITECTURE.md on major changes
- Review quarterly for staleness
```

---

*Template. Adapt structure to your project size.*
