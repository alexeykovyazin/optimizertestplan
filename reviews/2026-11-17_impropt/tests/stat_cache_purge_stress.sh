#!/bin/bash
# stat_cache_purge_stress.sh <isql> <database alias> [seconds]
# Two processes on one database, embedded engine with ServerMode = Classic and ExtendedStatistics = true:
#   the reader opens 400 attachments and runs three queries in each (every attachment reads the statistics),
#   the writer commits ALTER PROCEDURE P_STRESS SET CARDINALITY 3000 times.
# The database needs the statistics storage (ALTER DATABASE ADD EXTENDED STATISTICS, REFRESH STATISTICS), a table T
# with the columns I and S, and a selectable procedure P_STRESS.
# Before the review fix (hqbird cc2b15181b) both processes hung after a few queries: the purge AST of the reader
# waited for the mutex of the statistics cache, the reader waited to enter the engine again. A timeout (rc 124)
# is the hang. With the fix the writer ends in about 3 s and the reader in about 30 s.
isql=$1; db=$2; tmo=${3:-240}
d=$(mktemp -d)
for k in $(seq 1 400); do printf "connect '%s';\nselect count(*) from t where i = 1 and s = 'a';\nselect count(*) from t where i = 2;\nselect count(*) from p_stress;\ncommit;\n" "$db"; done > $d/reader.sql
for k in $(seq 1 3000); do printf "alter procedure p_stress set cardinality %d;\ncommit;\n" $((k % 50 + 1)); done > $d/writer.sql
s=$(date +%s)
( timeout $tmo "$isql" -q -i $d/reader.sql > $d/reader.txt 2>&1; echo "reader rc=$? $(( $(date +%s) - s )) s, result sets $(grep -c COUNT $d/reader.txt) of 1200" ) &
( timeout $tmo "$isql" -q "$db" -i $d/writer.sql > $d/writer.txt 2>&1; echo "writer rc=$? $(( $(date +%s) - s )) s, failed statements $(grep -c 'Statement failed' $d/writer.txt)" ) &
wait
rm -rf $d
