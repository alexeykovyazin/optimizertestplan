r"""Прогон отобранной десятки (топ-10 по времени среди запросов с Hash Join)
на новой сборке FB_impropt. Протокол полного прогона: warmup 1 + замер 1,
сторож 300 с, свежее соединение на каждое исполнение.

Запуск на dellg15:
  set FB_CLIENT_DIR=C:\HQbird\Firebird50
  python E:\fbdata\top10_hash_run.py E:\results\top10_<метка>.json
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
QS = [
    ("job-light", "job_light_043"),
    ("job-light", "job_light_070"),
    ("job-light", "job_light_041"),
    ("ceb-imdb-regen", "ceb_8a_011"),
    ("ceb-imdb-regen", "ceb_8a_010"),
    ("ceb-imdb-regen", "ceb_9a_010"),
    ("ceb-imdb-regen", "ceb_8a_015"),
    ("ceb-imdb-regen", "ceb_8a_003"),
    ("ceb-imdb-regen", "ceb_10a_015"),
    ("ceb-imdb-regen", "ceb_3b_005"),
]
WARMUP, REPS, WATCHDOG = 1, 1, 300.0

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
        reap("after watchdog")
        return {"ms": None, "rows": None, "err": f"watchdog {WATCHDOG:.0f}s"}
    return box


def reap(when):
    """Прибить чужие присоединения: брошенный после сторожа запрос
    продолжает крутиться на сервере и отравляет следующие замеры."""
    try:
        d = connect(fbenv.dsn(DB), user="SYSDBA", password="masterkey",
                    charset="UTF8")
        c = d.cursor()
        c.execute("delete from MON$ATTACHMENTS "
                  "where MON$ATTACHMENT_ID <> CURRENT_CONNECTION "
                  f"and MON$ATTACHMENT_ID <> {CONTROL_ID}")
        d.commit()
        ZOMB.append(d)
        print(f"    reap({when}): ok", flush=True)
    except Exception as e:
        print(f"    reap({when}): {e!r:.120}", flush=True)


def main():
    out = sys.argv[1]
    res = {}
    db = connect(fbenv.dsn(DB), user="SYSDBA", password="masterkey",
                 charset="UTF8")
    cur = db.cursor()
    cur.execute(SET_CARD)
    cur.fetchall()
    cur.execute("select CURRENT_CONNECTION from RDB$DATABASE")
    global CONTROL_ID
    CONTROL_ID = cur.fetchone()[0]
    print("control attachment:", CONTROL_ID, flush=True)
    for suite, qid in QS:
        sql = open(os.path.join(r"E:\bench\queries", suite, qid + ".sql"),
                   encoding="utf-8").read()
        ps = cur.prepare(sql)
        rec = {"suite": suite,
               "plan": " ".join(ps.plan.split()),
               "dplan": " ".join((ps.detailed_plan or "").split())}
        ps.free()
        print(f"[{qid}] prepared", flush=True)
        for i in range(WARMUP):
            r = timed_exec(sql, {})
            print(f"[{qid}] warmup{i+1}: {r}", flush=True)
            reap("post-warmup")
        times = []
        for i in range(REPS):
            r = timed_exec(sql, {})
            print(f"[{qid}] rep{i+1}: {r}", flush=True)
            times.append(r)
            reap("post-rep")
        rec["reps"] = times
        rec["ms"] = times[0]["ms"]
        res[qid] = rec
        json.dump(res, open(out, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)  # инкрементально на диск
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
    print("RUN DONE ->", out, flush=True)
    sys.stdout.flush()
    os._exit(0)


ZOMB = []
CONTROL_ID = None

if __name__ == "__main__":
    main()
