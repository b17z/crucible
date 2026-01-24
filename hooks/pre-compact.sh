#!/bin/bash
# Pre-compact hook: Log timestamp to SESSION_NOTES.md before context compaction
# This runs right before Claude Code compacts the conversation
#
# Installation:
# 1. Copy this file to your project: .claude/hooks/pre-compact.sh
# 2. Make executable: chmod +x .claude/hooks/pre-compact.sh
# 3. Add hook config to ~/.claude/settings.json (see README.md)
# 4. Create SESSION_NOTES.md in your project root

NOTES_FILE="SESSION_NOTES.md"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S %Z")

# Only append if SESSION_NOTES.md exists
if [ -f "$NOTES_FILE" ]; then
  echo "" >> "$NOTES_FILE"
  echo "---" >> "$NOTES_FILE"
  echo "" >> "$NOTES_FILE"
  echo "## $TIMESTAMP (Auto-compacted)" >> "$NOTES_FILE"
  echo "" >> "$NOTES_FILE"
  echo "*Context was auto-compacted. Review conversation summary above for continuity.*" >> "$NOTES_FILE"
  echo "" >> "$NOTES_FILE"
fi
