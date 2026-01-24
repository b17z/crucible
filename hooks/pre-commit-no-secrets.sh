#!/usr/bin/env bash
# ============================================================================
# pre-commit-no-secrets.sh
# ============================================================================
# Scans staged files for potential secrets before allowing commit.
# Install: cp hooks/pre-commit-no-secrets.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
# Or use with pre-commit framework: https://pre-commit.com
# ============================================================================

set -euo pipefail

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔍 Scanning for secrets...${NC}"

# Get list of staged files (excluding deleted files)
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

if [ -z "$STAGED_FILES" ]; then
    echo -e "${GREEN}✅ No files to check${NC}"
    exit 0
fi

FOUND_SECRETS=0

# ============================================================================
# Pattern Definitions
# ============================================================================

# High-confidence patterns (very likely to be secrets)
HIGH_CONFIDENCE_PATTERNS=(
    # AWS
    'AKIA[0-9A-Z]{16}'                          # AWS Access Key ID
    'aws_secret_access_key\s*=\s*["\x27][A-Za-z0-9/+=]{40}["\x27]'
    
    # Generic API Keys
    'api[_-]?key\s*[=:]\s*["\x27][A-Za-z0-9_\-]{20,}["\x27]'
    'apikey\s*[=:]\s*["\x27][A-Za-z0-9_\-]{20,}["\x27]'
    
    # Private Keys
    '-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----'
    '-----BEGIN PGP PRIVATE KEY BLOCK-----'
    
    # Tokens
    'ghp_[A-Za-z0-9]{36}'                       # GitHub Personal Access Token
    'gho_[A-Za-z0-9]{36}'                       # GitHub OAuth Token
    'ghu_[A-Za-z0-9]{36}'                       # GitHub User-to-Server Token
    'ghs_[A-Za-z0-9]{36}'                       # GitHub Server-to-Server Token
    'ghr_[A-Za-z0-9]{36}'                       # GitHub Refresh Token
    'xox[baprs]-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*' # Slack Token
    'sk-[A-Za-z0-9]{48}'                        # OpenAI API Key
    'sk-ant-[A-Za-z0-9\-]{80,}'                 # Anthropic API Key
    
    # Database URLs with passwords
    'postgres://[^:]+:[^@]+@'
    'mysql://[^:]+:[^@]+@'
    'mongodb://[^:]+:[^@]+@'
    'mongodb\+srv://[^:]+:[^@]+@'
    'redis://:[^@]+@'
    
    # Generic secrets in common formats
    'secret[_-]?key\s*[=:]\s*["\x27][A-Za-z0-9_\-]{16,}["\x27]'
    'password\s*[=:]\s*["\x27][^\x27"]{8,}["\x27]'
    'passwd\s*[=:]\s*["\x27][^\x27"]{8,}["\x27]'
)

# Medium-confidence patterns (might be secrets, review needed)
MEDIUM_CONFIDENCE_PATTERNS=(
    # Generic patterns that might have false positives
    'token\s*[=:]\s*["\x27][A-Za-z0-9_\-]{20,}["\x27]'
    'auth[_-]?token\s*[=:]\s*["\x27][A-Za-z0-9_\-]{20,}["\x27]'
    'bearer\s+[A-Za-z0-9_\-\.]{20,}'
    
    # Base64 encoded blobs (might be secrets)
    '["\x27][A-Za-z0-9+/]{40,}={0,2}["\x27]'
)

# Files to always skip
SKIP_PATTERNS=(
    '\.lock$'
    'package-lock\.json$'
    'yarn\.lock$'
    'poetry\.lock$'
    'Cargo\.lock$'
    '\.min\.js$'
    '\.min\.css$'
    'vendor/'
    'node_modules/'
    '__pycache__/'
    '\.pyc$'
)

# ============================================================================
# Scanning Functions
# ============================================================================

should_skip_file() {
    local file="$1"
    for pattern in "${SKIP_PATTERNS[@]}"; do
        if [[ "$file" =~ $pattern ]]; then
            return 0
        fi
    done
    return 1
}

scan_file_for_secrets() {
    local file="$1"
    local found=0
    
    # Skip binary files
    if file "$file" | grep -q "binary"; then
        return 0
    fi
    
    # Check high-confidence patterns
    for pattern in "${HIGH_CONFIDENCE_PATTERNS[@]}"; do
        if grep -qEi "$pattern" "$file" 2>/dev/null; then
            echo -e "${RED}🚨 HIGH: Potential secret in $file${NC}"
            echo -e "   Pattern: $pattern"
            grep -nEi "$pattern" "$file" 2>/dev/null | head -3 | while read -r line; do
                # Truncate long lines and mask potential secrets
                truncated=$(echo "$line" | cut -c1-100)
                echo -e "   ${YELLOW}$truncated...${NC}"
            done
            found=1
        fi
    done
    
    return $found
}

# ============================================================================
# Main Scan
# ============================================================================

for file in $STAGED_FILES; do
    # Skip if file doesn't exist (might be a submodule or special file)
    if [ ! -f "$file" ]; then
        continue
    fi
    
    # Skip files matching skip patterns
    if should_skip_file "$file"; then
        continue
    fi
    
    # Scan file
    if ! scan_file_for_secrets "$file"; then
        FOUND_SECRETS=1
    fi
done

# ============================================================================
# Check for .env files being committed
# ============================================================================

for file in $STAGED_FILES; do
    if [[ "$file" =~ \.env($|\.) ]] || [[ "$file" == ".env" ]]; then
        echo -e "${RED}🚨 CRITICAL: Attempting to commit .env file: $file${NC}"
        echo -e "   .env files should NEVER be committed!"
        FOUND_SECRETS=1
    fi
done

# ============================================================================
# Result
# ============================================================================

if [ $FOUND_SECRETS -eq 1 ]; then
    echo ""
    echo -e "${RED}============================================================${NC}"
    echo -e "${RED}❌ COMMIT BLOCKED: Potential secrets detected!${NC}"
    echo -e "${RED}============================================================${NC}"
    echo ""
    echo "If these are false positives, you can:"
    echo "  1. Add patterns to .gitignore"
    echo "  2. Use 'git commit --no-verify' (NOT RECOMMENDED)"
    echo "  3. Add file to hooks/secrets-allowlist.txt"
    echo ""
    exit 1
else
    echo -e "${GREEN}✅ No secrets detected${NC}"
    exit 0
fi
