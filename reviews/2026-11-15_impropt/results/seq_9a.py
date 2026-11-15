r"""Runs the CEB sequence around 9a_002 as the harness does: fresh connection per execution,
SHOW_EXPLAIN_CARDINALITY context, prepare + two executions. Prints the row counts."""
import os, sys, time
sys.path.insert(0, r"E:\bench\harness")
import fbenv
fbenv.HOST_PORT = "localhost:3056"
fbenv.ensure_client()
from firebird.driver import connect
DB = r"E:/fbdata/impropt_work/imdb_fb5.fdb"
QDIR = r"E:\bench\queries\ceb-imdb-regen"
SET_CARD = "SELECT RDB$SET_CONTEXT('USER_SESSION', 'SHOW_EXPLAIN_CARDINALITY', '1') FROM RDB$DATABASE"
seq = sys.argv[1:] or ["ceb_8a_015", "ceb_8a_016", "ceb_9a_001", "ceb_9a_002", "ceb_9a_003", "ceb_9a_002"]
for rnd in range(int(os.environ.get("ROUNDS", "2"))):
    for q in seq:
        sql = open(os.path.join(QDIR, q + ".sql"), encoding="utf-8").read()
        for rep in ("warmup", "rep1"):
            db = connect(fbenv.dsn(DB), user="SYSDBA", password="masterkey", charset="UTF8")
            cur = db.cursor(); cur.execute(SET_CARD); cur.fetchall()
            t0 = time.perf_counter(); cur.execute(sql); rows = cur.fetchall()
            print(f"round {rnd} {q} {rep}: rows={len(rows)} {(time.perf_counter() - t0) * 1000:.0f} ms", flush=True)
            db.close()
os._exit(0)
