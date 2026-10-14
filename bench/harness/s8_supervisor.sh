#!/bin/bash
# Супервайзер S8: рестартует suite_baseline до завершения каждой сюиты.
# Причины рестартов: AV-краш firebird-driver без traceback, зависание recv
# после гибели соединения, сетевые блыпы LAN. Прогресс не теряется:
# suite_baseline пишет результаты построчно в <suite>.executed.jsonl и
# при рестарте досчитывает только недостающее.
cd "$(dirname "$0")/../.." || exit 1
KEY=8e23f5f87eea
BDIR="results/baselines/$KEY"
mkdir -p "$BDIR"

python -u bench/harness/attachment_reaper.py \
    --db E:/fbdata/work/imdb_work_suite.fdb --hostport 192.168.1.57:3055 \
    >> "$BDIR/reaper.log" 2>&1 &
REAPER=$!
trap 'kill $REAPER 2>/dev/null' EXIT

for suite in job-light scale ceb-imdb-regen; do
  for attempt in 1 2 3 4 5 6 7 8 9 10 11 12; do
    if [ -f "$BDIR/$suite.executed.parquet" ]; then
      echo "=== $suite: parquet готов ==="
      break
    fi
    echo "=== $suite попытка $attempt старт $(date +%H:%M:%S) ==="
    timeout 2700 python -u bench/harness/suite_baseline.py --suites "$suite" \
        --host 192.168.1.57:3055 --skip-copy >> "$BDIR/supervisor.log" 2>&1
    echo "=== $suite попытка $attempt код=$? финиш $(date +%H:%M:%S) ==="
    sleep 15
  done
done

# S8 tpch: отдельный golden, первая попытка копирует work (1.6 GB)
for attempt in 1 2 3 4; do
  if [ -f "$BDIR/tpch.executed.parquet" ]; then
    echo "=== tpch: parquet готов ==="
    break
  fi
  skip=""
  [ "$attempt" -gt 1 ] && skip="--skip-copy"
  echo "=== tpch попытка $attempt старт $(date +%H:%M:%S) ==="
  timeout 2700 python -u bench/harness/suite_baseline.py --suites tpch \
      --host 192.168.1.57:3055 --golden E:/fbdata/golden/tpch_sf1_fb5.fdb \
      --work-name tpch_work_suite.fdb $skip >> "$BDIR/supervisor.log" 2>&1
  echo "=== tpch попытка $attempt код=$? финиш $(date +%H:%M:%S) ==="
  sleep 15
done

# synthetic: только компиляция (ночной контур, B4)
for attempt in 1 2 3; do
  if [ -f "$BDIR/synthetic.collected.parquet" ]; then
    echo "=== synthetic: collect готов ==="
    break
  fi
  echo "=== synthetic попытка $attempt старт $(date +%H:%M:%S) ==="
  timeout 2700 python -u bench/harness/suite_baseline.py --suites synthetic \
      --host 192.168.1.57:3055 --skip-copy --only-collect \
      >> "$BDIR/supervisor.log" 2>&1
  echo "=== synthetic попытка $attempt код=$? финиш $(date +%H:%M:%S) ==="
  sleep 15
done

echo "ALL_SUITES_DONE $(date +%H:%M:%S)"
