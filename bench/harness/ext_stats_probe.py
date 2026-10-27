r"""Зонд эффекта многоколоночных статистик: время + планы (rows=) до/после.

Запуск на dellg15:
  set FB_CLIENT_DIR=C:\HQbird\Firebird50
  python E:\fbdata\ext_stats_probe.py E:\results\extstats_before.json
  python E:\fbdata\ext_stats_probe.py E:\results\extstats_after.json

По каждому qid: соединение с SHOW_EXPLAIN_CARDINALITY=1, prepare (план +
детальный план с rows=), warmup, замеры. Результат — JSON.
"""
import json
import os
import sys
import threading
import time

sys.path.insert(0, r"E:\bench\harness")
import fbenv

fbenv.HOST_PORT = "localhost:3056"
fbenv.ensure_client()
from firebird.driver import connect

DB = r"E:/fbdata/impropt_work/imdb_fb5.fdb"
QDIR = r"E:\bench\queries\job-light"
QIDS = ["job_light_038", "job_light_001", "job_light_041", "job_light_027"]
WARMUP, REPS, WATCHDOG = 1, 3, 180.0

SET_CARD = ("SELECT RDB$SET_CONTEXT('USER_SESSION', "
            "'SHOW_EXPLAIN_CARDINALITY', '1') FROM RDB$DATABASE")


def timed_exec(sql, box):
    """Свежее соединение на каждое исполнение: брошенный после сторожа
    поток держит лок драйвера на своём соединении и блокирует остальных."""
    def work():
        db = None
        try:
            db = connect(fbenv.dsn(DB), user="SYSDBA", password="masterkey",
                         charset="UTF8")
            cur = db.cursor()
            cur.execute(SET_CARD)
            cur.fetchall()
            t0 = time.perf_counter()
            cur.execute(sql)
            rows = cur.fetchall()
            box["ms"] = round((time.perf_counter() - t0) * 1000.0, 1)
            box["rows"] = len(rows)
        except BaseException as e:
            box["err"] = repr(e)[:200]
        finally:
            if db is not None:
                ZOMB.append(db)  # после сторожа соединение не закрываем
    th = threading.Thread(target=work, daemon=True)
    th.start()
    th.join(WATCHDOG)
    if th.is_alive():
        return {"ms": None, "rows": None, "err": f"watchdog {WATCHDOG:.0f}s"}
    return box


def main():
    out = sys.argv[1]
    res = {}
    db = connect(fbenv.dsn(DB), user="SYSDBA", password="masterkey",
                 charset="UTF8")
    cur = db.cursor()
    cur.execute(SET_CARD)
    cur.fetchall()
    for qid in QIDS:
        sql = open(os.path.join(QDIR, qid + ".sql"), encoding="utf-8").read()
        ps = cur.prepare(sql)
        rec = {"plan": " ".join(ps.plan.split()),
               "dplan": " ".join((ps.detailed_plan or "").split())}
        ps.free()
        times = []
        for i in range(WARMUP):
            r = timed_exec(sql, {})
            print(f"[{qid}] warmup{i+1}: {r}", flush=True)
        for i in range(REPS):
            r = timed_exec(sql, {})
            print(f"[{qid}] rep{i+1}: {r}", flush=True)
            times.append(r)
        rec["reps"] = times
        rec["min_ms"] = min((t["ms"] for t in times if t["ms"] is not None),
                            default=None)
        res[qid] = rec
    cur.close()
    db.close()
    # чистим брошенные после сторожа присоединения, чтобы не грели машину
    try:
        db2 = connect(fbenv.dsn(DB), user="SYSDBA", password="masterkey",
                      charset="UTF8")
        c2 = db2.cursor()
        c2.execute("delete from MON$ATTACHMENTS "
                   "where MON$ATTACHMENT_ID <> CURRENT_CONNECTION")
        db2.commit()
        ZOMB.append(db2)
    except Exception as e:
        print("cleanup:", repr(e)[:200], flush=True)
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("PROBE DONE ->", out, flush=True)
    sys.stdout.flush()
    os._exit(0)


ZOMB = []

if __name__ == "__main__":
    main()
