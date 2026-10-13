"""Профилирование JOB на выделенном инстансе через RDB$PROFILER (§7).

FB5-профайлер даёт построчный (statement-level) серверный профиль: число
исполнений, время, строки. Сессия стартуется на конкретном аттаче, запросы
исполняются в нём же, затем сессия закрывается и таблицы RDB$PROFILER_*
выгружаются в results/dedicated_dellg15/profiler/.

Запуск (на машине замеров или с указанием --host):
  python bench/harness/job_profile.py --fdb E:/fbdata/work/imdb_work.fdb \
      --only 1a 10a 13a 17b 19a 22c --host localhost:3055
"""
from __future__ import annotations

import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
import fbenv  # noqa: E402
from runner import _Worker  # noqa: E402

OUT = os.path.join(ROOT, "results", "dedicated_dellg15", "profiler")
QDIR = os.path.join(ROOT, "bench", "queries", "job")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--fdb", default="E:/fbdata/work/imdb_work.fdb")
    ap.add_argument("--host", default="localhost:3055")
    ap.add_argument("--timeout-s", type=float, default=600.0)
    ap.add_argument("--only", nargs="*",
                    default=["1a", "10a", "13a", "17b", "19a", "22c"])
    a = ap.parse_args()
    fbenv.HOST_PORT = a.host
    os.makedirs(OUT, exist_ok=True)

    worker = _Worker(a.fdb)
    try:
        conn = worker.holder.get("db")
        if conn is None:
            conn = fbenv.connect_fb(a.fdb, stmt_timeout_s=a.timeout_s)
            worker.holder["db"] = conn
            worker.holder["tmap"] = fbenv.table_id_map(conn)
        cur = conn.cursor()
        cur.execute("SELECT RDB$PROFILER.START_SESSION() FROM RDB$DATABASE")
        session_id = cur.fetchone()[0]
        cur.close()
        print(f"profiler session {session_id}", flush=True)

        times = {}
        for qid in a.only:
            sql = open(os.path.join(QDIR, f"{qid}.sql"),
                       encoding="utf-8").read()
            t0 = time.perf_counter()
            r = worker.run(sql, a.timeout_s)
            wall = time.perf_counter() - t0
            times[qid] = {
                "wall_s": round(wall, 3),
                "status": ("ok" if r["res"] else
                           ("timeout" if r["timed_out"] else
                            f"error:{type(r['err']).__name__}")),
                "rows": len(r["res"]["rows"]) if r["res"] else None,
            }
            print(f"  {qid}: {times[qid]['status']} {wall:.1f}s", flush=True)

        cur = conn.cursor()
        cur.execute("SELECT RDB$PROFILER.FINISH_SESSION() FROM RDB$DATABASE")
        cur.fetchone()
        cur.close()

        cur = conn.cursor()
        for table, fname in [
            ("RDB$PROFILER_STATEMENTS", "statements.json"),
            ("RDB$PROFILER_REQUESTS", "requests.json"),
            ("RDB$PROFILER_RECORDS_SOURCES", "record_sources.json"),
        ]:
            try:
                cur.execute(f"SELECT * FROM {table}")
                cols = [d[0].strip() for d in cur.description]
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]
                json.dump({"session_id": session_id, "rows": rows},
                          open(os.path.join(OUT, fname), "w",
                               encoding="utf-8"), default=str,
                          ensure_ascii=False)
                print(f"  {table}: {len(rows)} rows -> {fname}", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"  {table}: {e}", flush=True)
        cur.close()
        json.dump({"session_id": session_id, "queries": times},
                  open(os.path.join(OUT, "session_meta.json"), "w",
                       encoding="utf-8"), indent=1)
    finally:
        worker.close()


if __name__ == "__main__":
    main()
