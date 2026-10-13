"""Проба API старого firebird-driver на FB_PARSCAN: no-arg execute vs execute(sql)."""
import os
import threading
import time

os.add_dll_directory(r"E:\fbdata\parscan")
from firebird.driver import connect  # noqa: E402

DSN = r"inet://localhost:44830/E:/db/imdb/IMDB_FB5.FDB"


def cap(seconds, fn):
    box = {}

    def work():
        try:
            box["r"] = fn()
        except BaseException as e:
            box["err"] = repr(e)[:200]

    th = threading.Thread(target=work, daemon=True)
    th.start()
    th.join(seconds)
    if th.is_alive():
        return f"HANG>{seconds}s"
    return box.get("r") or box.get("err")


def t_noarg():
    db = connect(DSN, user="SYSDBA", password="masterkey", charset="UTF8")
    cur = db.cursor()
    cur.prepare("SELECT COUNT(*) FROM TITLE")

    def go():
        cur.execute()
        return cur.fetchone()[0]

    r = cap(15, go)
    print("A prepare+execute() no-arg:", r, flush=True)
    db.close()


def t_execsql():
    db = connect(DSN, user="SYSDBA", password="masterkey", charset="UTF8")
    cur = db.cursor()

    def go():
        cur.execute("SELECT COUNT(*) FROM TITLE")
        return cur.fetchone()[0]

    r = cap(15, go)
    print("B execute(sql):", r, flush=True)
    db.close()


t_execsql()
t_noarg()
os._exit(0)
