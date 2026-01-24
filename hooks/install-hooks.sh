#!/usr/bin/env bash
# ============================================================================
# install-hooks.sh
# ============================================================================
# Installs git hooks for the project.
# Run from project root: ./hooks/install-hooks.sh
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
GIT_HOOKS_DIR="$PROJECT_ROOT/.git/hooks"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Installing git hooks...${NC}"

# Check if we're in a git repo
if [ ! -d "$PROJECT_ROOT/.git" ]; then
    echo -e "${RED}Error: Not a git repository${NC}"
    echo "Run 'git init' first"
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p "$GIT_HOOKS_DIR"

# Install pre-commit hook
if [ -f "$SCRIPT_DIR/pre-commit-no-secrets.sh" ]; then
    cp "$SCRIPT_DIR/pre-commit-no-secrets.sh" "$GIT_HOOKS_DIR/pre-commit"
    chmod +x "$GIT_HOOKS_DIR/pre-commit"
    echo -e "${GREEN}✅ Installed pre-commit hook (secret detection)${NC}"
else
    echo -e "${RED}❌ pre-commit-no-secrets.sh not found${NC}"
fi

# Install pre-push hook if it exists
if [ -f "$SCRIPT_DIR/pre-push.sh" ]; then
    cp "$SCRIPT_DIR/pre-push.sh" "$GIT_HOOKS_DIR/pre-push"
    chmod +x "$GIT_HOOKS_DIR/pre-push"
    echo -e "${GREEN}✅ Installed pre-push hook${NC}"
fi

# Note about Claude Code hooks
echo ""
echo -e "${YELLOW}Claude Code Hooks:${NC}"
echo "The pre-compact.sh hook is for Claude Code (not git)."
echo "To install it for Claude Code:"
echo "  1. Copy hooks/pre-compact.sh to .claude/hooks/"
echo "  2. Add to ~/.claude/settings.json:"
echo '     "hooks": { "PreCompact": [".claude/hooks/pre-compact.sh"] }'
echo ""

echo ""
echo -e "${GREEN}Hooks installed successfully!${NC}"
echo ""
echo "To verify, try committing a file with 'password=' in it."
echo "The commit should be blocked."
echo ""
echo "To bypass (NOT RECOMMENDED): git commit --no-verify"
