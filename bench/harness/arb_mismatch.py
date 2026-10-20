r"""Арбитраж MISMATCH-запросов: исполнение на 3056 (+3055 при --both),
выгрузка полных результатов в JSON для локальной сверки с PG-эталоном.

Запуск: python E:/fbdata/arb_mismatch.py qid1 qid2 ... [--both]
"""
import hashlib
import json
import os
import sys
import threading

sys.path.insert(0, r"E:\bench\harness")
import fbenv

args = [a for a in sys.argv[1:] if not a.startswith("--")]
both = "--both" in sys.argv
exp = json.load(open(r"E:\fbdata\expected_imdb.json", encoding="utf-8"))

TARGETS = [("3056", "localhost:3056",
            r"E:/fbdata/impropt_work/imdb_fb5.fdb")]
if both:
    TARGETS.insert(0, ("3055", "localhost:3055",
                       r"E:/fbdata/work/imdb_work_suite.fdb"))

WATCHDOG = 660.0


def run_rows(port, db_path, sql):
    box = {}

    def work():
        db = None
        try:
            fbenv.HOST_PORT = port
            db = fbenv.connect_fb(db_path)
            cur = db.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
            box["rows"] = rows
        except BaseException as e:
            box["err"] = repr(e)[:200]
        finally:
            if db is not None:
                ZOMB.append(db)

    ZOMB.append(box)  # noqa: держим ссылки стабильными
    th = threading.Thread(target=work, daemon=True)
    th.start()
    th.join(WATCHDOG)
    if th.is_alive():
        return None
    return box.get("rows")


ZOMB = []

for qid in args:
    suite = exp[qid]["suite"]
    sql = open(rf"E:\bench\queries\{suite}\{qid}.sql",
               encoding="utf-8").read()
    for label, port, db_path in TARGETS:
        rows = run_rows(port, db_path, sql)
        if rows is None:
            print(f"{qid} {label}: TIMEOUT/ERROR>{WATCHDOG:.0f}s", flush=True)
            continue
        canon = "\x1e".join(repr(tuple(r)) for r in sorted(rows, key=repr))
        sha = "sha1:" + hashlib.sha1(canon.encode("utf-8")).hexdigest()
        out = {"rows": [[("" if v is None else v) for v in r]
                        for r in rows],
               "checksum": sha, "n": len(rows)}
        path = rf"E:\results\arb_{qid}_{label}.json"
        json.dump(out, open(path, "w", encoding="utf-8"))
        print(f"{qid} {label}: {len(rows)} rows {sha[:20]}", flush=True)
print("ARB DONE", flush=True)
sys.stdout.flush()
os._exit(0)
