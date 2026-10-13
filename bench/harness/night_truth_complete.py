"""Ночной контур, элемент 2: досчёт недостающих истинных кардиналистов
подпланов (4.6: «недостающие подпланы ночной контур досчитывает и кеширует»).

Считает только true_rows IS NULL с бюджетом на запрос (по умолчанию 60 с)
и мержит в bench/truth/stats-ceb/stats-ceb-subplans.parquet.

Запуск: python bench/harness/night_truth_complete.py [--budget-s 60]
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
import duckdb  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from truth_ceb import register_tables, compute_suite, fb_to_duck  # noqa: E402
TRUTH = os.path.join(ROOT, "bench", "truth", "stats-ceb", "stats-ceb-subplans.parquet")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget-s", type=float, default=60.0)
    args = ap.parse_args()

    table = pq.read_table(TRUTH).to_pylist()
    missing = [r["query_id"] for r in table if r["true_rows"] is None]
    print(f"missing truth: {len(missing)}")
    if not missing:
        return

    con = duckdb.connect()
    con.execute("SET threads TO 4")
    con.execute("SET memory_limit='6GB'")
    register_tables(con)

    qdir = os.path.join(ROOT, "bench", "queries", "stats-ceb-subplans")
    done = {}
    for i, qid in enumerate(missing, 1):
        sql = open(os.path.join(qdir, qid + ".sql"), encoding="utf-8").read()
        import threading
        timer = threading.Timer(args.budget_s, con.interrupt)
        timer.start()
        try:
            done[qid] = con.execute(fb_to_duck(sql)).fetchone()[0]
            print(f"  [{i}/{len(missing)}] {qid} = {done[qid]}", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"  [{i}/{len(missing)}] {qid}: still missing "
                  f"({str(e).strip()[:60]})", flush=True)
        finally:
            timer.cancel()

    merged = [(r["query_id"], done.get(r["query_id"], r["true_rows"]))
              for r in table]
    import pyarrow as pa
    tbl = pa.table({
        "query_id": pa.array([q for q, _ in merged], pa.string()),
        "true_rows": pa.array([v for _, v in merged], pa.int64()),
    })
    pq.write_table(tbl, TRUTH)
    have = sum(1 for _, v in merged if v is not None)
    print(f"coverage now: {have}/{len(merged)} "
          f"({100.0 * have / len(merged):.1f}%)")


if __name__ == "__main__":
    main()
