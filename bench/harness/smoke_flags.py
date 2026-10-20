r"""Смоук после включения флагов: prepare+exec быстрых запросов на 3056.

Проверяем: (1) соединение/компиляция под флагами работают; (2) в
detailed_plan есть оценки rows= (SHOW_EXPLAIN_CARDINALITY); (3) оценки
кардинальности таблиц совпадают с точными собранными (ExtendedStatistics
реально читает STAT$) — для TITLE это 2 528 312 строк.
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

exp = json.load(open(r"E:\fbdata\expected_imdb.json", encoding="utf-8"))
picks = {}
for q, e in exp.items():
    if e["timed_out"] or not e["median_ms"]:
        continue
    s = e["suite"]
    if s not in picks or e["median_ms"] < picks[s][1]:
        picks[s] = (q, e["median_ms"])

db = fbenv.connect_fb(r"E:/fbdata/impropt_work/imdb_fb5.fdb")
cur = db.cursor()
cur.execute("SELECT RDB$SET_CONTEXT('USER_SESSION', "
            "'SHOW_EXPLAIN_CARDINALITY', '1') FROM RDB$DATABASE")
cur.fetchall()

for s, (q, ms) in sorted(picks.items()):
    sql = open(rf"E:\bench\queries\{s}\{q}.sql", encoding="utf-8").read()
    ps = cur.prepare(sql)
    print(f"=== {q} ({s}, baseline median {ms:.0f}ms)", flush=True)
    print("PLAN:", " ".join((ps.plan or "").split()), flush=True)
    dp = ps.detailed_plan or ""
    tables = re.findall(r'Table "([^"]+)"[^\\n]*\(rows=([\d.]+)\)', dp)
    print("TABLE rows=:", tables[:8], flush=True)
    ps.free()
    t0 = time.perf_counter()
    cur.execute(sql)
    rows = cur.fetchall()
    print(f"exec: {len(rows)} rows, {(time.perf_counter() - t0) * 1000:.0f}ms",
          flush=True)

db.close()
print("SMOKE DONE", flush=True)
sys.stdout.flush()
os._exit(0)
