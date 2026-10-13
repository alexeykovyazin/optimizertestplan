"""Пробник возможностей драйвера firebird.driver на FB5 (порт 3055).

Проверяет: подключение, план Statement.plan, счётчики isc_database_info
(fetches, read_seq_count, read_idx_count), профайлер PLG$PROFILING, SET OPTIMIZE.
"""
import os, sys, time

for p in (r"C:\Firebird5", r"C:\HQbird\Firebird50"):
    if os.path.isdir(p):
        os.add_dll_directory(p)
        os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")

from firebird.driver import connect, create_database, driver_config

DSN_TMPL = "inet://localhost:3055/{path}"
PROBE = r"E:\Projects_Big\optimizertestplan\db\work\probe.fdb"

def main():
    if os.path.exists(PROBE):
        os.remove(PROBE)
    drv_cfg = driver_config.get_config()
    print("driver config: fbclient ==", getattr(drv_cfg, "fbclient_library", "?"))

    db = create_database(DSN_TMPL.format(path=PROBE), user="SYSDBA", password="masterkey")
    cur = db.cursor()
    cur.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v VARCHAR(100))")
    cur.execute("INSERT INTO t (id, v) SELECT x, 'v' FROM (SELECT 1 x FROM RDB$DATABASE UNION ALL SELECT 2 FROM RDB$DATABASE UNION ALL SELECT 3 FROM RDB$DATABASE)")
    db.commit()

    # --- план через Statement.plan
    cur2 = db.cursor()
    ps = db.prepare("SELECT * FROM t WHERE id > 1")
    print("PLAN:", repr(ps.plan))

    # --- счётчики isc_database_info
    info = db.info
    names = [a for a in dir(info) if not a.startswith("_")]
    print("info attrs:", [a for a in names if any(k in a.lower() for k in ("fetch", "read", "seq", "idx", "insert", "update", "delete", "page"))])

    before_f = info.fetch_sequence if hasattr(info, "fetch_sequence") else None
    print("before fetches:", before_f)
    ps2 = db.prepare("SELECT count(*) FROM t a CROSS JOIN t b CROSS JOIN t c")
    rows = list(ps2.exec())
    print("rows:", rows)
    print("after fetches:", info.fetch_sequence if hasattr(info, "fetch_sequence") else "?")

    # --- SET OPTIMIZE
    try:
        cur2.execute("SET OPTIMIZE ALL ROWS")
        print("SET OPTIMIZE ALL ROWS: OK")
    except Exception as e:
        print("SET OPTIMIZE failed:", e)

    # --- statement timeout
    ps3 = db.prepare("SELECT * FROM t")
    print("has timeout attr:", hasattr(ps3, "timeout"))
    print("cancel_operation:", hasattr(db, "cancel_operation"))

    # --- профайлер
    try:
        cur2.execute("SELECT COUNT(*) FROM PLG$PROFILING.PLG$PROF_SESSIONS")
        print("profiler tables: OK (plugin enabled)")
    except Exception as e:
        print("profiler: NOT AVAILABLE:", str(e).strip()[:200])

    db.close()
    print("PROBE OK")

if __name__ == "__main__":
    main()
