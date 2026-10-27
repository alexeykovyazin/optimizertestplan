r"""Применение DDL многоколоночных статистик (candidates.sql) на рабочей БД.

Запуск на dellg15:
  set FB_CLIENT_DIR=C:\HQbird\Firebird50
  python E:\fbdata\ext_stats_apply.py E:\fbdata\candidates_job.sql

Каждая CREATE — в отдельной транзакции; затем один ALTER DATABASE
REFRESH STATISTICS (включает именованные структуры). Хранилище STAT$
уже создано (26.10), шесть словарей CEB уже есть.
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, r"E:\bench\harness")
import fbenv

fbenv.HOST_PORT = "localhost:3056"
fbenv.ensure_client()
from firebird.driver import connect

DB = r"E:/fbdata/impropt_work/imdb_fb5.fdb"

stmts = []
for ln in open(sys.argv[1], encoding="utf-8"):
    ln = re.sub(r"--.*", "", ln).strip()
    if ln:
        stmts.append(ln.rstrip(";"))
print(f"{len(stmts)} DDL statements", flush=True)

db = connect(fbenv.dsn(DB), user="SYSDBA", password="masterkey",
             charset="UTF8")
cur = db.cursor()
for ddl in stmts:
    db.begin()
    try:
        cur.execute(ddl)
        db.commit()
        print("OK  " + ddl[:80], flush=True)
    except Exception as e:
        db.rollback()
        print("FAIL " + ddl[:80] + "\n  " + repr(e)[:300], flush=True)

t0 = time.perf_counter()
db.begin()
cur.execute("ALTER DATABASE REFRESH STATISTICS")
db.commit()
print(f"REFRESH STATISTICS: {time.perf_counter() - t0:.0f}s", flush=True)

cur.execute("select STAT$NAME, STAT$RELATION_NAME, STAT$FIELDS, "
            "STAT$ENTRIES from STAT$MULTI_COLUMNS order by STAT$NAME")
for nm, rel, fld, ent in cur.fetchall():
    print(f"  {nm.strip():35s} {rel.strip():18s} {fld.strip():25s} "
          f"entries={ent}", flush=True)
db.close()
print("APPLY DONE", flush=True)
sys.stdout.flush()
os._exit(0)
