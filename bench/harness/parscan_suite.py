"""Прогон JOB / CEB-IMDb на инстансе FB_PARSCAN (dellg15, порт 44830).

По строке на запрос в CSV (fsync после каждой строки) — промежуточные данные
переживают обрыв сессии; рестарт пропускает уже записанные qid.

Маркер параллельности — дельта строк 'PSCAN:' в firebird.log инстанса:
воркеры невидимы в MON$ATTACHMENTS, плоский план печатает NATURAL и для
параллельного скана. Разбор новых строк: 'startParallel=1 workers=N rel=X'
= скан реально распараллелен; строки 'cost ...' / 'no:' — только вердикт
гейта, без старта воркеров.

Таймауты: серверный statement timeout (через fbenv) + клиентский сторож
(поток, соединение бросается в потоке). По завершении os._exit(0) —
зомби-потоки не дают процессу выйти чисто.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fbenv

DB_PATH = r"E:\db\imdb\IMDB_FB5.FDB"
FB_LOG = r"E:\fbdata\parscan\firebird.log"

SUITES = {
    "job": dict(
        dir=r"E:\bench\queries\job",
        expected=r"E:\bench\parscan\expected_job.json",
        out=r"E:\results\parscan_suite_job.csv",
    ),
    "ceb": dict(
        dir=r"E:\bench\queries\ceb-imdb-regen",
        expected=r"E:\bench\parscan\expected_ceb.json",
        out=r"E:\results\parscan_suite_ceb.csv",
    ),
}

CSV_FIELDS = ["suite", "qid", "status", "prepare_ms", "exec_ms", "rows",
              "check", "checksum", "pscan", "pscan_lines", "error"]

STMT_TIMEOUT_S = 1500.0
WATCHDOG_S = 1560.0


def natkey(name: str):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", name)]


def rows_checksum(rows) -> str:
    canon = "\x1e".join(repr(tuple(r)) for r in sorted(rows, key=repr))
    return "sha1:" + hashlib.sha1(canon.encode("utf-8")).hexdigest()


def pscan_count() -> int:
    try:
        with open(FB_LOG, "r", errors="replace") as f:
            return sum(1 for ln in f if "PSCAN:" in ln)
    except OSError:
        return 0


def pscan_read_full() -> list[str]:
    try:
        with open(FB_LOG, "r", errors="replace") as f:
            return [ln.strip() for ln in f if "PSCAN:" in ln]
    except OSError:
        return []


def pscan_summarize(before_cnt: int, after_cnt: int,
                    full_after: list[str]) -> tuple[str, int]:
    """(метка, дельта). startParallel=1 → 'REL:N', только вердикт гейта → 'gateonly'."""
    delta = after_cnt - before_cnt
    if delta <= 0:
        return "", 0
    new = full_after[before_cnt:after_cnt]
    started: list[str] = []
    for ln in new:
        m = re.search(r"startParallel=1\s+workers=(\d+)\s+rel=(\S+)", ln)
        if m:
            started.append(f"{m.group(2)}:{m.group(1)}")
    return ("|".join(started) if started else "gateonly"), delta


def run_one(sql: str) -> dict:
    c0 = pscan_count()
    t0 = time.perf_counter()
    db = fbenv.connect_fb(DB_PATH, stmt_timeout_s=STMT_TIMEOUT_S)
    conn_ms = (time.perf_counter() - t0) * 1000.0
    try:
        cur = db.cursor()
        te = time.perf_counter()
        # без явного prepare(): execute() без аргументов в этом драйвере
        # не поддержан (TypeError), а деструктор подготовленного Statement
        # подвешивает процесс на выходе
        cur.execute(sql)
        rows = cur.fetchall()
        exec_ms = (time.perf_counter() - te) * 1000.0
        prepare_ms = None
    finally:
        try:
            db.close()
        except Exception:
            pass
    c1 = pscan_count()
    full = pscan_read_full() if c1 > c0 else []
    tag, delta = pscan_summarize(c0, c1, full)
    return {"status": "ok", "prepare_ms": None,
            "exec_ms": round(exec_ms, 1), "rows": len(rows),
            "checksum": rows_checksum(rows), "pscan": tag,
            "pscan_lines": delta, "error": None, "conn_ms": round(conn_ms, 1)}


def guarded(sql: str) -> dict:
    box: dict = {}

    def work():
        try:
            box.update(run_one(sql))
        except BaseException as e:  # таймаут сервера/драйвера тоже сюда
            box.clear()
            box["status"] = "error"
            box["error"] = repr(e)[:300]

    th = threading.Thread(target=work, daemon=True)
    th.start()
    th.join(WATCHDOG_S)
    if th.is_alive():
        return {"status": "timeout", "error": f"watchdog {WATCHDOG_S:.0f}s",
                "exec_ms": None, "rows": None, "checksum": None,
                "pscan": "", "pscan_lines": "", "prepare_ms": None}
    return box


def resume_set(out_path: str) -> set[str]:
    done: set[str] = set()
    if os.path.isfile(out_path):
        with open(out_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("qid"):
                    done.add(row["qid"])
    return done


def control_query(label: str) -> None:
    """Тёплый контроль деградации: SELECT COUNT(*) FROM TITLE."""
    try:
        t0 = time.perf_counter()
        db = fbenv.connect_fb(DB_PATH)
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) FROM TITLE")
        n = cur.fetchone()[0]
        db.close()
        print(f"[control] {label}: {n} rows, "
              f"{(time.perf_counter() - t0) * 1000:.0f} ms", flush=True)
    except Exception as e:
        print(f"[control] {label}: FAILED {e!r}", flush=True)


def run_suite(suite: str, limit: int) -> None:
    cfg = SUITES[suite]
    exp = {}
    if os.path.isfile(cfg["expected"]):
        with open(cfg["expected"], encoding="utf-8") as f:
            exp = json.load(f)
    qids = sorted(
        (os.path.basename(p)[:-4] for p in os.listdir(cfg["dir"])
         if p.lower().endswith(".sql")), key=natkey)
    if limit:
        qids = qids[:limit]
    done = resume_set(cfg["out"])
    new_file = not os.path.isfile(cfg["out"])
    with open(cfg["out"], "a", newline="", encoding="utf-8") as fcsv:
        w = csv.DictWriter(fcsv, fieldnames=CSV_FIELDS)
        if new_file:
            w.writeheader()
            fcsv.flush()
        todo = [q for q in qids if q not in done]
        print(f"=== suite {suite}: {len(todo)} to run "
              f"({len(done)} already done, {len(qids)} total)", flush=True)
        for i, qid in enumerate(todo, 1):
            with open(os.path.join(cfg["dir"], qid + ".sql"),
                      encoding="utf-8") as f:
                sql = f.read()
            t0 = time.perf_counter()
            res = guarded(sql)
            wall = time.perf_counter() - t0
            e = exp.get(qid) or {}
            check = "n/a"
            if res.get("status") == "ok" and e:
                ok = (res.get("checksum") == e.get("checksum")
                      and res.get("rows") == e.get("rows"))
                check = "match" if ok else "MISMATCH"
            row = {"suite": suite, "qid": qid, "status": res.get("status"),
                   "prepare_ms": res.get("prepare_ms"),
                   "exec_ms": res.get("exec_ms"), "rows": res.get("rows"),
                   "check": check, "checksum": res.get("checksum"),
                   "pscan": res.get("pscan", ""),
                   "pscan_lines": res.get("pscan_lines", ""),
                   "error": (res.get("error") or "")[:300]}
            w.writerow(row)
            fcsv.flush()
            os.fsync(fcsv.fileno())
            print(f"[{suite} {i}/{len(todo)}] {qid} "
                  f"exec={row['exec_ms']}ms rows={row['rows']} "
                  f"{check} pscan={row['pscan'] or '-'} "
                  f"({row['pscan_lines']}) wall={wall:.1f}s"
                  + (f" ERR={row['error']}" if row["error"] else ""),
                  flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suites", nargs="+", default=["job", "ceb"],
                    choices=sorted(SUITES))
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    print(f"parscan_suite start pid={os.getpid()} suites={args.suites} "
          f"hostport={fbenv.HOST_PORT} client={fbenv.FB_CLIENT_DIR}",
          flush=True)
    control_query("start")
    for s in args.suites:
        control_query(f"before-{s}")
        run_suite(s, args.limit)
        control_query(f"after-{s}")
    print("=== all suites done", flush=True)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)  # зомби-потоки таймаутов не дают выйти чисто


if __name__ == "__main__":
    main()
