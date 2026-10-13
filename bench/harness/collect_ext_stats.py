r"""Сбор расширенной статистики оптимизатора (ветка v5.0-impr-opt).

Запуск (на dellg15):
  set FB_CLIENT_DIR=C:\HQbird\Firebird50
  python E:/bench/harness/collect_ext_stats.py ^
      E:/fbdata/impropt_work/stats_pk_fk.fdb E:/fbdata/impropt_work/imdb_fb5.fdb

На каждой базе: ALTER DATABASE ADD EXTENDED STATISTICS (если хранилища ещё
нет) и полный ALTER DATABASE REFRESH EXTENDED STATISTICS (все таблицы, все
пригодные столбцы, BINS 100 по умолчанию). Хранилище — обычные таблицы
STAT$* внутри базы, переживают рестарт.
"""
import sys
import time

sys.path.insert(0, r"E:\bench\harness")
import fbenv

fbenv.HOST_PORT = "localhost:3056"
fbenv.ensure_client()
from firebird.driver import connect


def has_storage(db) -> bool:
    cur = db.cursor()
    cur.execute("select count(*) from RDB$RELATIONS "
                "where RDB$RELATION_NAME = 'STAT$SETTINGS'")
    return cur.fetchone()[0] > 0


def process(path: str):
    print(f"=== {path} ===", flush=True)
    db = connect(fbenv.dsn(path), user="SYSDBA", password="masterkey",
                 charset="UTF8")
    cur = db.cursor()
    if has_storage(db):
        print("  хранилище STAT$ уже есть", flush=True)
    else:
        db.begin()
        cur.execute("ALTER DATABASE ADD EXTENDED STATISTICS")
        db.commit()
        print("  хранилище создано", flush=True)
    t0 = time.perf_counter()
    db.begin()
    cur.execute("ALTER DATABASE REFRESH EXTENDED STATISTICS")
    db.commit()
    dt = time.perf_counter() - t0
    cur.execute("select count(*) from STAT$TABLES")
    nt = cur.fetchone()[0]
    cur.execute("select count(*) from STAT$COLUMNS")
    nc = cur.fetchone()[0]
    print(f"  REFRESH: {dt:.0f} c, таблиц: {nt}, столбцов: {nc}", flush=True)
    cur.close()
    db.close()


if __name__ == "__main__":
    for p in sys.argv[1:]:
        process(p)
    print("COLLECT DONE")
