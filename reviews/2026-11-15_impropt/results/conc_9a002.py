r"""Does CEB 9a_002 lose rows when heavy queries run at the same time?
Run on dellg15:
  set FB_CLIENT_DIR=C:\HQbird\Firebird50
  python E:\fbdata\conc_9a002.py [heavy query ids, default ceb_8a_012 ceb_8a_004]
The heavy queries run in background threads (their own connections); 9a_002 runs REPS times
in fresh connections; then once more with nothing in the background.
"""
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
QDIR = r"E:\bench\queries\ceb-imdb-regen"
HEAVY = sys.argv[1:] or ["ceb_8a_012", "ceb_8a_004"]
TARGET = os.environ.get("TARGET", "ceb_9a_002")
REPS = int(os.environ.get("REPS", "6"))
KEEP = []


def sql_of(qid):
    return open(os.path.join(QDIR, qid + ".sql"), encoding="utf-8").read()


def heavy(qid, ids):
    try:
        db = connect(fbenv.dsn(DB), user="SYSDBA", password="masterkey", charset="UTF8")
        KEEP.append(db)
        cur = db.cursor()
        cur.execute("select current_connection from rdb$database")
        ids.append(cur.fetchone()[0])
        cur.execute(sql_of(qid))
        rows = cur.fetchall()
        print(f"    heavy {qid}: finished, rows={len(rows)}", flush=True)
    except BaseException as e:
        print(f"    heavy {qid}: {repr(e)[:90]}", flush=True)


def run_target(tag):
    db = connect(fbenv.dsn(DB), user="SYSDBA", password="masterkey", charset="UTF8")
    cur = db.cursor()
    t0 = time.perf_counter()
    cur.execute(sql_of(TARGET))
    rows = cur.fetchall()
    ms = (time.perf_counter() - t0) * 1000
    print(f"{tag}: rows={len(rows)} {ms:.0f} ms", flush=True)
    db.close()
    return len(rows)


def main():
    counts = []
    counts.append(run_target("alone-before"))
    ids = []
    for q in HEAVY:
        threading.Thread(target=heavy, args=(q, ids), daemon=True).start()
    time.sleep(8)
    print("heavy attachments:", ids, flush=True)
    for i in range(REPS):
        counts.append(run_target(f"with-heavy-{i + 1}"))
    # stop the heavy queries
    try:
        d = connect(fbenv.dsn(DB), user="SYSDBA", password="masterkey", charset="UTF8")
        c = d.cursor()
        for a in ids:
            c.execute(f"delete from mon$attachments where mon$attachment_id = {a}")
        d.commit()
        KEEP.append(d)
        print("heavy attachments killed", flush=True)
    except Exception as e:
        print("kill:", repr(e)[:90], flush=True)
    time.sleep(5)
    counts.append(run_target("alone-after"))
    print("COUNTS", counts, flush=True)
    os._exit(0)


main()
