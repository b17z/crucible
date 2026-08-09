#!/bin/bash
# assemble.sh — Build-Along Course assembler.
#
# Concatenates base.html + modules/*.html (lexicographic order, which
# the two-digit module ids make chronological) + footer.html into
# index.html, all in the directory this script is run from (course/).
#
# /bin/bash 3.2-safe: no mapfile, no globstar, no associative arrays,
# every expansion guarded. Never edits module files — read-only on
# modules/, base.html, footer.html; only index.html is written.
#
# Usage: run from inside course/ (or pass a course dir as $1).
#   ./assemble.sh
#   ./assemble.sh /path/to/course

set -uo pipefail

COURSE_DIR="${1:-.}"

BASE="$COURSE_DIR/base.html"
FOOTER="$COURSE_DIR/footer.html"
MODULES_DIR="$COURSE_DIR/modules"
OUT="$COURSE_DIR/index.html"

if [ ! -f "$BASE" ]; then
  echo "assemble.sh: missing $BASE — cannot assemble" >&2
  exit 1
fi

if [ ! -f "$FOOTER" ]; then
  echo "assemble.sh: missing $FOOTER — cannot assemble" >&2
  exit 1
fi

if [ ! -d "$MODULES_DIR" ]; then
  echo "assemble.sh: missing $MODULES_DIR — cannot assemble" >&2
  exit 1
fi

# Collect module files without mapfile/globstar (bash 3.2 has neither).
# A glob that matches nothing expands to the literal pattern unless
# nullglob is set, so guard explicitly.
module_files=""
module_count=0
for f in "$MODULES_DIR"/*.html; do
  if [ -f "$f" ]; then
    module_files="$module_files $f"
    module_count=$((module_count + 1))
  fi
done

if [ "$module_count" -eq 0 ]; then
  echo "assemble.sh: no module files in $MODULES_DIR — cannot assemble" >&2
  exit 1
fi

# Lexicographic order: the for-loop glob expansion above is already
# sorted lexicographically by bash; sort explicitly anyway so behavior
# doesn't depend on locale/glob quirks.
sorted_modules=$(printf '%s\n' $module_files | sort)

tmp_out="$OUT.tmp.$$"
cat "$BASE" > "$tmp_out"
for f in $sorted_modules; do
  cat "$f" >> "$tmp_out"
done
cat "$FOOTER" >> "$tmp_out"

mv "$tmp_out" "$OUT"
echo "assemble.sh: wrote $OUT ($module_count module(s))"
exit 0
