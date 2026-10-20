r"""Прогон HASH-корпуса IMDb на FB_impropt 3056 (v5.0-impr-opt, ext stats).

Корпус: ceb-imdb-regen (121, все HASH) + job-light HASH (21) + scale HASH (97),
эталонные чексуммы/время — из бейслина HQbird 5.0.5 3055
(results/baselines/8e23f5f87eea). Протокол как в бейслайне: prepare (планы,
как в collect-фазе бейслина), warmup 1 (кроме бейслин-таймаутов), 1 замер,
сторож 300 с. По строке в CSV с fsync, резюм по CSV, os._exit(0) в конце
(зомби-потоки сторожа). Встроенный жнец убирает зомби-стэйтменты старше
330 c (> сторожа 300 c).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import threading
import time

sys.path.insert(0, r"E:\bench\harness")
import fbenv

fbenv.HOST_PORT = "localhost:3056"

FIELDS = ["qid", "suite", "kind", "status", "exec_ms", "rows", "check",
          "checksum", "prepare_ms", "plan_hash", "plan", "dplan", "error"]

SET_CARD = ("SELECT RDB$SET_CONTEXT('USER_SESSION', "
            "'SHOW_EXPLAIN_CARDINALITY', '1') FROM RDB$DATABASE")

FIND_SQL = ("SELECT DISTINCT a.mon$attachment_id "
            "FROM mon$attachments a "
            "JOIN mon$statements s ON s.mon$attachment_id = a.mon$attachment_id "
            "WHERE s.mon$state = 1 "
            "AND DATEDIFF(SECOND FROM s.mon$timestamp TO CURRENT_TIMESTAMP) "
            "> {age}")
KILL_SQL = "DELETE FROM MON$ATTACHMENTS WHERE MON$ATTACHMENT_ID = {att}"
REAPER_AGE = 330  # > сторожа 300 c, легитимные замеры не задеваются


def reaper_loop(db_path: str) -> None:
    while True:
        try:
            db = fbenv.connect_fb(db_path)
            cur = db.cursor()
            cur.execute(FIND_SQL.format(age=REAPER_AGE))
            ids = [r[0] for r in cur.fetchall()]
            for i in ids:
                cur.execute(KILL_SQL.format(att=i))
            db.commit()
            db.close()
            if ids:
                print(f"[reaper] killed {ids}", flush=True)
        except Exception:
            pass
        time.sleep(15)


def rows_checksum(rows) -> str:
    canon = "\x1e".join(repr(tuple(r)) for r in sorted(rows, key=repr))
    return "sha1:" + hashlib.sha1(canon.encode("utf-8")).hexdigest()


# Соединения, пережившие таймаут (и убитые жнецом на сервере): держим
# ссылки до конца процесса — GC не должен финализировать убитый хэндл
# (access violation в __del__ роняет весь процесс).
ZOMBIES = []


def run_one(db_path: str, sql: str, watchdog_s: float) -> dict:
    box: dict = {}

    def work():
        db = None
        try:
            t0 = time.perf_counter()
            db = fbenv.connect_fb(db_path)
            cur = db.cursor()
            cur.execute(SET_CARD)
            cur.fetchall()
            cur.execute(sql)
            rows = cur.fetchall()
            ms = (time.perf_counter() - t0) * 1000.0
            try:
                db.close()
            except Exception:
                pass
            box.update(status="ok", exec_ms=round(ms, 1), rows=len(rows),
                       checksum=rows_checksum(rows), error=None)
        except BaseException as e:
            if db is not None:
                ZOMBIES.append(db)  # без close(): хэндл уже мертв на сервере
            box.update(status="error", exec_ms=None, rows=None,
                       checksum=None, error=repr(e)[:300])

    th = threading.Thread(target=work, daemon=True)
    th.start()
    th.join(watchdog_s)
    if th.is_alive():
        return dict(status="timeout", exec_ms=None, rows=None, checksum=None,
                    error=f"watchdog {watchdog_s:.0f}s")
    return box


def plan_hash(p: str) -> str:
    return "md5:" + hashlib.md5(" ".join(p.split()).encode("utf-8")
                                ).hexdigest() if p else ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=r"E:/fbdata/impropt_work/imdb_fb5.fdb")
    ap.add_argument("--queries", default=r"E:\bench\queries")
    ap.add_argument("--expected", default=r"E:\fbdata\expected_imdb.json")
    ap.add_argument("--out", default=r"E:\results\hash_imdb_ab.csv")
    ap.add_argument("--warmup", type=int, default=1)
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--watchdog", type=float, default=300.0)
    args = ap.parse_args()

    expected = json.load(open(args.expected, encoding="utf-8"))
    threading.Thread(target=reaper_loop, args=(args.db,), daemon=True,
                     name="reaper").start()

    done = set()
    if os.path.isfile(args.out):
        with open(args.out, encoding="utf-8") as f:
            try:
                for row in csv.DictReader(f):
                    if row["kind"] == "measured":
                        done.add(row["qid"])
            except Exception as e:  # обрезанная последняя строка после краша
                print(f"resume: останов на битой строке ({e!r})", flush=True)
        print(f"resume: {len(done)} уже измерено", flush=True)

    new = not os.path.isfile(args.out)
    with open(args.out, "a", newline="", encoding="utf-8") as fcsv:
        w = csv.DictWriter(fcsv, fieldnames=FIELDS)
        if new:
            w.writeheader()
            fcsv.flush()
        print(f"=== hash_imdb_ab db={args.db} warmup={args.warmup} "
              f"reps={args.reps} watchdog={args.watchdog:.0f}s "
              f"корпус={len(expected)}", flush=True)
        for qid in sorted(expected, key=lambda q: (expected[q]["suite"], q)):
            e = expected[qid]
            if qid in done:
                continue
            qfile = os.path.join(args.queries, e["suite"], qid + ".sql")
            if not os.path.isfile(qfile):
                w.writerow({"qid": qid, "suite": e["suite"], "kind": "measured",
                            "status": "no_sql", "exec_ms": None, "rows": None,
                            "check": "n/a", "checksum": None,
                            "prepare_ms": None, "plan_hash": "", "plan": "",
                            "dplan": "", "error": qfile})
                fcsv.flush(); os.fsync(fcsv.fileno())
                print(f"[{qid}] no_sql: {qfile}", flush=True)
                continue
            sql = open(qfile, encoding="utf-8").read()

            # prepare-фаза: планы как в collect-фазе бейслина
            prep = fbenv.prepare_with_watchdog(args.db, sql, args.watchdog)
            ph = plan_hash(prep["plan"] or "")
            prow = {"qid": qid, "suite": e["suite"], "kind": "prepare",
                    "status": ("timeout" if prep["timed_out"]
                               else ("error" if prep["error"] else "ok")),
                    "exec_ms": None, "rows": None, "check": "n/a",
                    "checksum": None,
                    "prepare_ms": (round(prep["prepare_ms"], 1)
                                   if prep["prepare_ms"] else None),
                    "plan_hash": ph, "plan": prep["plan"] or "",
                    "dplan": (prep["detailed_plan"] or "")[:8000],
                    "error": (prep["error"] or "")[:200]}
            w.writerow(prow)
            fcsv.flush(); os.fsync(fcsv.fileno())
            print(f"[{qid}] prepare: {prow['status']} "
                  f"{prow['prepare_ms']}ms", flush=True)
            if prow["status"] != "ok":
                w.writerow({"qid": qid, "suite": e["suite"], "kind": "measured",
                            "status": "prep_" + prow["status"], "exec_ms": None,
                            "rows": None, "check": "n/a", "checksum": None,
                            "prepare_ms": None, "plan_hash": ph, "plan": "",
                            "dplan": "", "error": prow["error"]})
                fcsv.flush(); os.fsync(fcsv.fileno())
                continue

            if args.warmup and not e["timed_out"]:
                r = run_one(args.db, sql, args.watchdog)
                print(f"[{qid}] warmup: {r['status']} "
                      f"{r.get('exec_ms')}ms", flush=True)
                if r["status"] == "error":
                    w.writerow({"qid": qid, "suite": e["suite"],
                                "kind": "warmup", "status": "error",
                                "exec_ms": None, "rows": None, "check": "n/a",
                                "checksum": None, "prepare_ms": None,
                                "plan_hash": ph, "plan": "", "dplan": "",
                                "error": (r["error"] or "")[:200]})
                    fcsv.flush(); os.fsync(fcsv.fileno())
                    continue
            reps = 1 if e["timed_out"] else args.reps
            for i in range(reps):
                r = run_one(args.db, sql, args.watchdog)
                check = "n/a"
                if r["status"] == "ok" and not e["timed_out"]:
                    check = ("match" if r["checksum"] == e["checksum"]
                             and r["rows"] == e["rows"] else "MISMATCH")
                elif r["status"] == "ok" and e["timed_out"]:
                    check = "FINISHED-WAS-TIMEOUT"
                w.writerow({"qid": qid, "suite": e["suite"], "kind": "measured",
                            "status": r["status"], "exec_ms": r["exec_ms"],
                            "rows": r["rows"], "check": check,
                            "checksum": r["checksum"], "prepare_ms": None,
                            "plan_hash": ph, "plan": "", "dplan": "",
                            "error": (r["error"] or "")[:200]})
                fcsv.flush(); os.fsync(fcsv.fileno())
                print(f"[{qid}] rep{i+1}: {r['status']} {r['exec_ms']}ms "
                      f"rows={r['rows']} {check}", flush=True)
    print("=== done", flush=True)
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
