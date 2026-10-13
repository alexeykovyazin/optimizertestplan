"""collector: prepare + план каждого запроса, запросы не исполняются (раздел 5).

Снимает: нормализованный план и его хеш, простой план, время подготовки
(медиана из N прогонов prepare). Оценки кардинальности по узлам на FB5
недоступны (RDB$SQL.EXPLAIN — FB 6); колонка `estimates` зарезервирована.
"""
from __future__ import annotations

import os
import statistics
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
import fbenv  # noqa: E402
from normalize import plan_features, plan_hash, simple_plan_hash  # noqa: E402


def collect_suite(db_path: str, suite: str, prepare_reps: int = 3,
                  prepare_timeout_s: float = 60.0,
                  only_ids: list[str] | None = None) -> list[dict]:
    qdir = os.path.join(ROOT, "bench", "queries", suite)
    ids = sorted(f[:-4] for f in os.listdir(qdir) if f.endswith(".sql"))
    if only_ids:
        ids = [i for i in ids if i in set(only_ids)]
    rows = []
    conn = fbenv.connect_fb(db_path)
    cur = conn.cursor()
    for qid in ids:
        sql = open(os.path.join(qdir, qid + ".sql"), encoding="utf-8").read()
        rec = {"query_id": qid, "suite": suite, "prepare_ms": None,
               "plan": None, "detailed_plan": None,
               "plan_hash": None, "detailed_plan_hash": None,
               "prepare_timed_out": False, "error": None}
        try:
            t_ms = []
            for k in range(prepare_reps):
                t0 = time.perf_counter()
                ps = cur.prepare(sql)
                t_ms.append((time.perf_counter() - t0) * 1000.0)
                if k == 0:
                    rec["plan"] = ps.plan
                    rec["detailed_plan"] = ps.detailed_plan
                    rec["plan_hash"] = simple_plan_hash(ps.plan)
                    rec["detailed_plan_hash"] = plan_hash(ps.detailed_plan)
                ps.free()
            rec["prepare_ms"] = statistics.median(t_ms)
            rec["features"] = str(plan_features(rec["detailed_plan"]))
        except Exception as e:  # noqa: BLE001
            msg = str(e).strip()
            if "timed out" in msg.lower() or "time-out" in msg.lower():
                rec["prepare_timed_out"] = True
            rec["error"] = f"{type(e).__name__}: {msg[:300]}"
        rows.append(rec)
    cur.close()
    conn.close()
    return rows
