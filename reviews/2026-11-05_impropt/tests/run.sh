#!/bin/bash
# run each test script with embedded isql; report exit code
S="$(cd "$(dirname "$0")" && pwd)"
ISQL="$S/../fbroot/isql.exe"
for f in "$@"; do
  echo "##### $f"
  timeout ${TMO:-120} "$ISQL" -q -i "$S/$f" 2>&1
  echo "##### rc=$?"
done
