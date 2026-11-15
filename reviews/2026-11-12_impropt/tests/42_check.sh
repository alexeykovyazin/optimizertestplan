#!/bin/bash
# 42_check.sh - checks the isql output of 42_hash_outer_join_matrix.sql
# usage: 42_check.sh <output file> [expected file] [-v]
#   Results: every case must print PASS (the query equals its nested loop reference).
#   Plans:   the number of "Hash Join (outer)" and of outer join nodes in the plan of the
#            "<tag> H" statement is compared with 42_expected.txt ("-" = any).
#            A plan difference is not a wrong result; it shows that the optimizer chose
#            another join method than the test expects (the stock server never hashes).
#   -v prints every case, otherwise only the problems and the summary.
out="$1"; exp="${2:-$(dirname "$0")/42_expected.txt}"; verbose="$3"
[ "$2" = "-v" ] && { verbose="-v"; exp="$(dirname "$0")/42_expected.txt"; }
awk -v verbose="$verbose" -F'|' '
function trim(x) { gsub(/^[ \t]+|[ \t\r]+$/, "", x); return x }
NR == FNR {
  if ($0 ~ /^#/) next
  t = trim($1); ehj[t] = trim($2); eou[t] = trim($3); title[t] = trim($4); order[++n] = t
  next
}
{
  line = $0
  if (line ~ /Hash Join \(outer\)/) hj++
  if (line ~ /Join \(outer\)/) ou++
  if (line ~ /^Statement failed/) { err++; errs++ }
  if (match(line, /^[A-H][0-9][0-9] H /)) {
    t = substr(line, 1, 3); hjH[t] = hj; ouH[t] = ou; errT[t] += err; seenH[t] = 1
    hj = 0; ou = 0; err = 0
  }
  else if (match(line, /^[A-H][0-9][0-9] +(PASS|FAIL)/)) {
    t = substr(line, 1, 3); split(line, f, /[ \t]+/); res[t] = f[2]; hjC[t] = hj; planC[t] = (hj + ou > 0)
    errT[t] += err
    hj = 0; ou = 0; err = 0
  }
  else if (line ~ /^END /) ended = 1
}
END {
  for (i = 1; i <= n; i++) {
    t = order[i]
    r = (t in res) ? res[t] : "MISSING"
    plan = "ok"
    if (!(t in seenH)) plan = "no-plan"
    else {
      if (ehj[t] != "-" && ehj[t] != hjH[t]) plan = "DIFF"
      if (eou[t] != "-" && eou[t] != ouH[t]) plan = "DIFF"
      # the reference half must add no hash join: the compared statement shows the same count
      if (planC[t] && hjC[t] != hjH[t]) plan = plan "+REF"
    }
    if (r == "PASS") pass++; else if (r == "FAIL") fail++; else miss++
    if (plan != "ok") pdiff++
    if (verbose != "" || r != "PASS" || plan != "ok" || errT[t] > 0)
      printf "%-4s %-7s hj=%s (exp %s) outer=%s (exp %s) plan=%-8s err=%d  %s\n",
        t, r, (t in hjH) ? hjH[t] : "?", ehj[t], (t in ouH) ? ouH[t] : "?", eou[t], plan, errT[t], title[t]
  }
  printf "SUMMARY: cases=%d PASS=%d FAIL=%d MISSING=%d plan_diff=%d statement_errors=%d finished=%s\n",
    n, pass, fail, miss, pdiff, errs, ended ? "yes" : "NO (the output is cut: server crash?)"
}' "$exp" "$out"
