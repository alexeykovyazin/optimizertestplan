"""runner: исполнение, прогрев, повторы; логические счётчики, время,
число строк и checksum (раздел 5 плана).

Счётчики — дельта информационных запросов соединения (isc_info_fetches и
постатоличные record reads через get_table_access_stats), не MON$.
Таймауты (раздел 5): server-side statement timeout (FB 4+) + клиентский
сторож. Сторож обязателен: наблюдение фазы 0 — после отмены клиент мог
блокироваться в сокете, поэтому каждое исполнение идёт в отдельном потоке
с жёстким join-таймаутом; при зависании поток бросается вместе со своим
соединением (серверный таймаут добьёт запрос, поток закроет соединение
в finally), выполняется переподключение.
"""
from __future__ import annotations

import hashlib
import json
import os
import statistics
import sys
import threading
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
import fbenv  # noqa: E402


def rows_checksum(rows) -> str:
    """Хеш отсортированного мультимножества строк результата."""
    canon = "\x1e".join(repr(tuple(r)) for r in sorted(rows, key=repr))
    return "sha1:" + hashlib.sha1(canon.encode("utf-8")).hexdigest()


def execute_one(db, tmap, sql) -> dict:
    """Одно исполнение с дельтой счётчиков. Соединение и карта таблиц
    передаются снаружи; транзакция завершается после выборки."""
    before = fbenv.read_counters(db, tmap)
    t0 = time.perf_counter()
    cur = db.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    after = fbenv.read_counters(db, tmap)
    cur.close()
    try:
        db.commit()
    except Exception:
        pass
    return {"ms": elapsed_ms, "rows": rows,
            "counters": after.delta(before).as_dict()}


class _Worker:
    """Владелец соединения: исполнения идут в рабочих потоках, соединение
    переиспользуется, пока здорово; после сбоя или зависания пересоздаётся."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.holder = {}

    def run(self, sql: str, timeout_s: float) -> dict:
        out = {"res": None, "err": None, "timed_out": False}

        def work():
            conn = self.holder.get("db")
            fresh = conn is None
            if fresh:
                conn = fbenv.connect_fb(self.db_path,
                                        stmt_timeout_s=timeout_s)
                self.holder["db"] = conn
            try:
                tmap = self.holder.get("tmap")
                if tmap is None:
                    tmap = fbenv.table_id_map(conn)
                    self.holder["tmap"] = tmap
                out["res"] = execute_one(conn, tmap, sql)
            except Exception as e:  # noqa: BLE001
                out["err"] = e
                # соединение в подозрительном состоянии — не переиспользуем
                try:
                    conn.close()
                except Exception:
                    pass
                self.holder["db"] = None
                self.holder["tmap"] = None

        th = threading.Thread(target=work, daemon=True)
        th.start()
        th.join(timeout_s + 45)  # запас поверх серверного statement timeout
        if th.is_alive():
            out["timed_out"] = True
            self.holder["db"] = None
            self.holder["tmap"] = None
        return out

    def close(self):
        conn = self.holder.get("db")
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        self.holder = {}


def run_suite(db_path: str, suite: str, warmup: bool = True, repeats: int = 2,
              only_ids: list[str] | None = None,
              per_query_timeout_s: float = 120.0,
              fetch_rows_limit: int = 1000,
              adaptive_reps_over_ms: float = 15000.0,
              progress: bool = True,
              on_result=None) -> list[dict]:
    """runs[0] — прогрев (раздел 10), отбрасывается при повторных прогонах;
    тяжёлый запрос (> adaptive_reps_over_ms) даёт единственный замер, он же
    медиана из 1. Бюджет одного исполнения — per_query_timeout_s; превышение
    (серверный или клиентский сторож) даёт timed_out — цензурированное
    значение (раздел 6)."""
    qdir = os.path.join(ROOT, "bench", "queries", suite)
    ids = sorted(f[:-4] for f in os.listdir(qdir) if f.endswith(".sql"))
    if only_ids:
        ids = [i for i in ids if i in set(only_ids)]
    worker = _Worker(db_path)
    out = []
    try:
        for i, qid in enumerate(ids, 1):
            sql = open(os.path.join(qdir, qid + ".sql"),
                       encoding="utf-8").read()
            rec = {"query_id": qid, "suite": suite, "median_ms": None,
                   "rows_count": None, "checksum": None,
                   "counters": None, "runs_ms": None,
                   "timed_out": False, "error": None}
            if progress:
                print(f"  [{suite} {i}/{len(ids)}] {qid}", flush=True)
            try:
                runs, last = [], None
                for _ in range(repeats):
                    r = worker.run(sql, per_query_timeout_s)
                    if r["timed_out"]:
                        rec["timed_out"] = True
                        break
                    if r["err"]:
                        raise r["err"]
                    last = r["res"]
                    runs.append(last["ms"])
                    if last["ms"] > adaptive_reps_over_ms:
                        break
                if runs:
                    if len(runs) > 1:
                        runs = runs[1:]  # runs[0] — прогрев
                    rec["runs_ms"] = runs
                    rec["median_ms"] = statistics.median(runs)
                    rec["rows_count"] = len(last["rows"])
                    rec["checksum"] = rows_checksum(
                        last["rows"][:fetch_rows_limit]) \
                        if rec["rows_count"] else "empty"
                    rec["counters"] = last["counters"]
                    if rec["rows_count"] == 1:
                        rec["result_value"] = last["rows"][0][0]
            except Exception as e:  # noqa: BLE001
                rec["error"] = f"{type(e).__name__}: {str(e).strip()[:300]}"
            out.append(rec)
            if on_result is not None:
                # построчная персистентность: краш процесса не теряет
                # результаты уже завершённых запросов
                try:
                    on_result(rec)
                except Exception:  # noqa: BLE001
                    pass
    finally:
        worker.close()
    return out
