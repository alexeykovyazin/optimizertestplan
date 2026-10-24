"""Локальный smoke новой сборки (v5.0-impr-opt): поднять, проверить ключевые
нововведения. Запуск: python bench/harness/smoke_impropt.py --root <dir>
--port 3056

Проверки: connect SYSDBA/masterkey; DDL+DML; в detailed_plan есть оценки
кардинальности (rows=...); ALTER DATABASE ADD/DROP EXTENDED STATISTICS и
REFRESH (новый SQL ветки); простая проверка статистики в STAT$TABLES.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import time
import uuid


def safe_commit(db):
    try:
        db.commit()
    except AttributeError:
        pass  # DDL в firebird-driver автокоммитится (main_transaction None)


def wait_port(port: int, timeout: float = 30) -> bool:
    import socket
    end = time.time() + timeout
    while time.time() < end:
        try:
            with socket.create_connection(("127.0.0.1", port), 2):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="каталог инстанса (output)")
    ap.add_argument("--port", type=int, default=3056)
    ap.add_argument("--db", default=None)
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    db = a.db or os.path.join(root, "smoke_%s.fdb" % uuid.uuid4().hex[:8])
    conf = os.path.join(root, "firebird.conf")

    lines = open(conf, encoding="utf-8", errors="replace").read().splitlines()
    changed = False
    for want in (f"RemoteServicePort = {a.port}", "ServerMode = Super",
                 "ShowExplainCardinality = true"):
        key = want.split(" = ")[0]
        if not any(re.match(rf"^\s*{key}\s*=", ln) for ln in lines):
            lines.append(want)
            changed = True
    if changed:
        open(conf, "w", newline="\r\n", encoding="utf-8").write(
            "\n".join(lines) + "\n")

    proc = subprocess.Popen([os.path.join(root, "firebird.exe"), "-a"],
                            cwd=root,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    try:
        assert wait_port(a.port), "server did not open port"
        # fbenv рядом со скриптом (HONOR2025) или в bench на dellg15
        for cand in (os.path.dirname(os.path.abspath(__file__)),
                     r"E:\bench\harness"):
            if os.path.exists(os.path.join(cand, "fbenv.py")):
                sys.path.insert(0, cand)
                break
        import fbenv
        fbenv.ensure_client()
        import firebird.driver as d
        from firebird.driver import create_database

        dsn = (f"inet://localhost:{a.port}/" + db.replace(os.sep, "/"))
        try:
            os.remove(db)
        except OSError:
            pass
        db1 = create_database(dsn, user="SYSDBA", password="masterkey",
                              charset="UTF8")
        db1.close()  # транзакция создания уже завершена — подключаемся заново
        from firebird.driver import connect
        db1 = connect(dsn, user="SYSDBA", password="masterkey",
                      charset="UTF8")
        cur = db1.cursor()
        db1.begin()
        cur.execute("create table t_smoke (id integer primary key, "
                    "v varchar(20))")
        db1.commit()
        db1.begin()
        for sql in ("insert into t_smoke values (1,'a')",
                    "insert into t_smoke values (2,'b')",
                    "insert into t_smoke values (3,'a')"):
            cur.execute(sql)
        db1.commit()

        ps = cur.prepare("select count(*) from t_smoke where v = 'a'")
        dp = ps.detailed_plan or ""
        print("DETAILED:", " | ".join(dp.splitlines()[:6]))
        assert "rows=" in dp, "нет оценок кардинальности в detailed_plan"
        assert cur.execute("select count(*) from t_smoke where v='a'"
                           ).fetchone()[0] == 2

        db1.begin()
        cur.execute("ALTER DATABASE ADD EXTENDED STATISTICS")
        db1.commit()
        db1.begin()
        cur.execute("ALTER DATABASE REFRESH STATISTICS "
                    "FOR TABLE T_SMOKE")
        db1.commit()
        db1.begin()
        cur.execute("select STAT$RELATION_NAME, STAT$CARDINALITY "
                    "from STAT$TABLES")
        rows = cur.fetchall()
        print("STAT$TABLES:", rows)
        assert rows and rows[0][1] == 3
        db1.commit()
        db1.begin()
        cur.execute("ALTER DATABASE DROP EXTENDED STATISTICS")
        db1.commit()
        cur.close()
        db1.close()
        print("SMOKE OK: rows= estimates + EXTENDED STATISTICS DDL work")
    finally:
        proc.kill()
        try:
            os.remove(db)
        except OSError:
            pass


if __name__ == "__main__":
    main()
