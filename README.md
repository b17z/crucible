# crucible: Claude Code Package

Everything you need to start building crucible with Claude Code.

## Files

| File | Purpose |
|------|---------|
| `SPEC.md` | Full technical specification — architecture, data models, tool interfaces |
| `CLAUDE.md` | Claude Code session context — philosophy, constraints, patterns |
| `KICKOFF_PROMPT.md` | The prompt(s) to paste into Claude Code |
| `SESSION_NOTES.md` | Template for session continuity (used by pre-compact hook) |
| `knowledge/` | Starter principles files to include in the project |
| `.gitignore` | Security-paranoid gitignore (blocks secrets, keys, .env) |
| `.pre-commit-config.yaml` | Pre-commit framework config (gitleaks, detect-secrets) |
| `hooks/pre-commit-no-secrets.sh` | Git hook for secret detection |
| `hooks/pre-compact.sh` | Claude Code hook for session continuity |
| `hooks/install-hooks.sh` | One-liner to install git hooks |

## Usage

### Option 1: Full Kickoff

1. Create a new directory: `mkdir crucible && cd crucible`
2. Copy `CLAUDE.md` and `SPEC.md` into it
3. Copy `knowledge/` directory into it
4. Open Claude Code: `claude`
5. Paste the main prompt from `KICKOFF_PROMPT.md`

### Option 2: Phased Approach

Use the numbered prompts in `KICKOFF_PROMPT.md` one at a time. Better for learning and debugging.

## What Claude Code Will Build

```
crucible/
├── CLAUDE.md                    # ✅ You provide
├── SPEC.md                      # ✅ You provide  
├── pyproject.toml               # Claude Code creates
├── src/
│   └── crucible/
│       ├── __init__.py
│       ├── server.py            # MCP server
│       ├── tools/               # Tool implementations
│       ├── domain/              # Detection + routing
│       ├── personas/            # Persona engine
│       ├── synthesis/           # Output generation
│       └── knowledge/           # Principles loader
├── tests/                       # Tests for each module
└── knowledge/                   # ✅ You provide (starter content)
    └── ENGINEERING_PRINCIPLES.md
```

## Dependencies

The project will need:

```toml
[project]
dependencies = [
    "mcp>=1.0.0",          # MCP SDK
    "pyyaml>=6.0",         # YAML parsing
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "mypy>=1.8",
    "ruff>=0.3",
]
```

## External Tools

crucible composes these (install separately):

- **semgrep**: `pip install semgrep` or `brew install semgrep`
- **slither**: `pip install slither-analyzer` (for smart contracts)
- **eslint**: `npm install -g eslint` (for TypeScript)
- **ruff**: `pip install ruff` (for Python)

For MCP composition (Phase 2+):
- slither-mcp: https://github.com/trailofbits/slither-mcp
- semgrep-mcp: https://github.com/semgrep/mcp

## Security Setup (Do This First)

Secrets in git = career-ending. Set this up before writing any code.

### Option 1: Pre-commit Framework (Recommended)

```bash
pip install pre-commit
pre-commit install
```

This uses `.pre-commit-config.yaml` which runs:
- **gitleaks** — Comprehensive secret scanner
- **detect-secrets** — Second layer of secret detection
- **detect-private-key** — Catches SSH/PGP keys
- **detect-aws-credentials** — Catches AWS keys

### Option 2: Simple Bash Hook

```bash
chmod +x hooks/install-hooks.sh
./hooks/install-hooks.sh
```

This installs `hooks/pre-commit-no-secrets.sh` which catches:
- AWS keys, GitHub tokens, OpenAI/Anthropic keys
- Private keys (RSA, DSA, PGP)
- Database URLs with passwords
- Generic `password=`, `secret_key=`, `api_key=` patterns

### Claude Code Hooks (Optional)

The `hooks/pre-compact.sh` hook logs compaction events to `SESSION_NOTES.md` for session continuity:

```bash
# Copy to Claude Code hooks directory
mkdir -p .claude/hooks
cp hooks/pre-compact.sh .claude/hooks/
chmod +x .claude/hooks/pre-compact.sh

# Add to ~/.claude/settings.json
{
  "hooks": {
    "PreCompact": [".claude/hooks/pre-compact.sh"]
  }
}
```

This ensures you never lose track of when context was compacted during long sessions.

### The .gitignore

The included `.gitignore` is paranoid by design. It blocks:
- All `.env*` files
- Anything with `secret`, `password`, `credential` in the name
- All common key formats (`.pem`, `.key`, etc.)
- Terraform state (often contains secrets)
- IDE configs (sometimes contain tokens)

**Rule: If you're not sure if something should be committed, it shouldn't be.**

## Tips

1. **Start small.** The MVP is: detect domain → run semgrep → format output
2. **Test each step.** Don't chain 5 things that haven't been tested individually
3. **Read SPEC.md section by section.** Don't try to absorb it all at once
4. **Use SESSION_NOTES.md.** If you stop mid-session, write down where you are
5. **Run the hooks.** Don't skip `pre-commit install` — future you will thank present you
