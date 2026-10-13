"""Трёхсторонний прогон полного stats-корпуса (146 джоинов + 632 одиночных)
на трёх сборках dellg15:

  hqbird     : порт 3055, неизменённый HQbird 5.0.5 (first_rows), база
               E:\\fbdata\\work\\stats_pk_fk.fdb
  impropt    : порт 3056, ветка v5.0-impr-opt, PredicateCorrelation=true +
               EXTENDED STATISTICS (STAT$ в копии), база
               E:\\fbdata\\impropt_work\\stats_pk_fk.fdb
  optprofile : порт 3180, ветка feature/optimization-profile, профиль
               stats.profile подключён алиасом stats_opt

На каждый тег: collect_suite (планы) + run_suite (repeats=3, runs[0] —
прогрев, тяжёлые >15 c — один замер). Сравнение: медианы времени, планы
(нормализованные, rows= вырезается), checksums (должны совпасть — копии
одного голдена).

Запуск (на dellg15): set FB_CLIENT_DIR=C:\\HQbird\\Firebird50 &&
python E:/bench/harness/stats_ceb_ab.py
Результат: E:\\results\\stats_ceb_ab\\
"""
import json
import math
import os
import re
import subprocess
import sys
import time

ROOT = r"E:\bench"
sys.path.insert(0, os.path.join(ROOT, "harness"))
OUT = r"E:\results\stats_ceb_ab"

TARGETS = {
    "hqbird": {"port": 3055, "db": r"E:\fbdata\work\stats_pk_fk.fdb"},
    "impropt": {"port": 3056, "db": r"E:\fbdata\impropt_work\stats_pk_fk.fdb"},
    "optprofile": {"port": 3180, "db": "stats_opt"},  # алиас с профилем
}
SUITES = ("stats-ceb", "stats-ceb-single")
CONF_PATHS = {"hqbird": r"C:\HQbird\Firebird50\firebird.conf",
              "impropt": r"E:\fb50-impropt\firebird.conf",
              "optprofile": r"E:\fb50-optprofile\firebird.conf"}
DBCONF = r"E:\fb50-optprofile\databases.conf"


def norm(plan):
    t = re.sub(r"\s*\(rows=[\d.]+\)", "", plan or "")
    return re.sub(r"\s+", " ", t).strip()


def geo(xs):
    xs = [x for x in xs if x and x > 0]
    return math.exp(sum(math.log(x) for x in xs) / len(xs)) if xs else None


def conf_active(path, keys):
    txt = open(path, encoding="utf-8", errors="replace").read()
    out = []
    for ln in txt.splitlines():
        m = re.match(rf"^\s*({'|'.join(keys)})\s*=\s*(\S+)", ln, re.I)
        if m:
            out.append(f"{m.group(1)}={m.group(2)}")
    return out


STMT_TIMEOUT_MS = 60000


SVC_RESTART = "FB_optprofile"
AUTO_RESTART = False


def make_conn(host_port, db):
    import fbenv
    fbenv.HOST_PORT = host_port
    fbenv.ensure_client()
    from firebird.driver import connect
    conn = connect(fbenv.dsn(db), user="SYSDBA", password="masterkey",
                   charset="UTF8")
    conn.info.set_statement_timeout = STMT_TIMEOUT_MS
    return conn


def checksum(rows):
    import hashlib
    def cell(v):
        s = str(v)
        return str(int(s)) if re.fullmatch(r"-?\d+", s) else s
    payload = "||".join("|".join(cell(v) for v in row) for row in rows)
    return "sha1:" + hashlib.sha1(payload.encode("utf-8")).hexdigest()


def run_tag(tag):
    """collect_suite для планов + устойчивый построчный исполнитель
    (пересоздание соединения после любой ошибки; постặpочный лог)."""
    import fbenv
    t = TARGETS[tag]
    host_port = f"localhost:{t['port']}"
    fbenv.HOST_PORT = host_port
    from collector import collect_suite
    import pipeline

    run_dir = os.path.join(OUT, tag)
    os.makedirs(run_dir, exist_ok=True)
    collected = []
    for suite in SUITES:
        for attempt in range(6):
            try:
                print(f"[{tag}] collect {suite}", flush=True)
                collected += collect_suite(t["db"], suite)
                break
            except Exception as e:
                print(f"[{tag}] collect {suite} failed ({e}), "
                      f"restart+retry {attempt+1}/6", flush=True)
                restart_server()
        else:
            raise SystemExit(f"collect {suite} impossible")

    executed = []
    import threading
    STMT_TIMEOUT_MS = 90000
    WATCHDOG_S = 60.0

    def restart_server():
        """Автоперезапуск службы инстанса (для нестабильной optprofile-сборки)."""
        import subprocess
        subprocess.run(f"net stop {SVC_RESTART} >nul 2>&1", shell=True)
        subprocess.run(f"net start {SVC_RESTART}", shell=True)
        import socket
        port = int(host_port.split(":")[1])
        for i in range(45):
            time.sleep(1 + i // 10)
            try:
                with socket.create_connection(("127.0.0.1", port), 2):
                    return True
            except OSError:
                continue
        return False

    TRANSIENT = ("network request", "reading data", "connection shutdown",
                 "Error writing data")

    def one_rep(host_port, db, sql, retry_on_transient=False):
        """Одно повторение на СВОЕМ соединении и потоке.
        Возврат: (ms, rows) | ('timeout', None) | ('error', text)."""
        box = {}

        def work():
            try:
                conn = make_conn(host_port, db)
                try:
                    cur = conn.cursor()
                    t0 = time.perf_counter()
                    cur.execute(sql)
                    rows = cur.fetchall()
                    box["ms"] = (time.perf_counter() - t0) * 1000
                    box["rows"] = rows
                    cur.close()
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass
            except Exception as e:
                box["err"] = f"{type(e).__name__}: {e}"[:300]

        th = threading.Thread(target=work, daemon=True)
        th.start()
        th.join(WATCHDOG_S)
        if th.is_alive():
            return "timeout", None
        if "err" in box:
            ms_guess = 10**9
            return "error", box["err"]
        return box["ms"], box["rows"]

    for suite in SUITES:
        qdir = os.path.join(ROOT, "queries", suite)
        ids = sorted(f[:-4] for f in os.listdir(qdir) if f.endswith(".sql"))
        for i, qid in enumerate(ids, 1):
            sql = open(os.path.join(qdir, qid + ".sql"),
                       encoding="utf-8").read()
            rec = {"query_id": qid, "suite": suite, "median_ms": None,
                   "rows_count": None, "checksum": None, "counters": None,
                   "runs_ms": None, "timed_out": False, "error": None}
            runs = []
            for rep in range(3):
                ms, payload = one_rep(host_port, t["db"], sql,
                                      retry_on_transient=AUTO_RESTART)
                if ms == "error" and AUTO_RESTART and                         any(t_ in str(payload).lower()
                            for t_ in TRANSIENT):
                    print(f"[{tag} {suite} {i}/{len(ids)}] {qid} "
                          "SERVER-DIED, restarting", flush=True)
                    if restart_server():
                        ms, payload = one_rep(host_port, t["db"], sql)
                if ms == "timeout":
                    rec["timed_out"] = True
                    runs.append(None)
                    print(f"[{tag} {suite} {i}/{len(ids)}] {qid} "
                          "WATCHDOG-TIMEOUT", flush=True)
                    # монстры детерминированы: остальные поворы не нужны
                    break
                if ms == "error":
                    if "timeout" in str(payload).lower() or                             "cancel" in str(payload).lower():
                        rec["timed_out"] = True
                    else:
                        rec["error"] = payload
                    runs.append(None)
                    continue
                runs.append(round(ms, 2))
                if rep == 0 or ms > 15000:
                    rec["rows_count"] = len(payload)
                    rec["checksum"] = checksum(payload) if payload                         else "empty"
            runs_ok = [r for r in runs if r is not None]
            if runs_ok:
                use = runs_ok[1:] if len(runs_ok) > 1 else runs_ok
                rec["runs_ms"] = runs_ok
                # statistics.median: для чётного длины — среднее двух середин
                import statistics
                rec["median_ms"] = statistics.median(use)
            executed.append(rec)
            flag = (rec["error"] or ("TIMEOUT" if rec["timed_out"]
                    else f"{rec['median_ms']:.0f}ms"))
            if not rec["timed_out"]:
                print(f"[{tag} {suite} {i}/{len(ids)}] {qid} {flag}",
                      flush=True)
        # инкрементально: сюита сохранена, даже если следующая упадёт
        pipeline.save_parquet([r for r in collected if r["suite"] == suite],
                              os.path.join(run_dir, f"collected_{suite}.parquet"))
        pipeline.save_parquet([r for r in executed if r["suite"] == suite],
                              os.path.join(run_dir, f"executed_{suite}.parquet"))
    pipeline.save_parquet(collected, os.path.join(run_dir, "collected.parquet"))
    pipeline.save_parquet(executed, os.path.join(run_dir, "executed.parquet"))
    return collected, executed


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", nargs="+", default=list(TARGETS))
    ap.add_argument("--auto-restart", action="store_true",
                    help="перезапускать службу при смерти соединения")
    a = ap.parse_args()
    global AUTO_RESTART
    AUTO_RESTART = a.auto_restart
    os.makedirs(OUT, exist_ok=True)
    assert "OptimizationProfileFile" in open(DBCONF, encoding="utf-8",
                                             errors="replace").read(), \
        "профиль stats_opt не подключён в databases.conf"
    meta = {"conf": {k: conf_active(v, ["OptimizeForFirstRows",
                                        "PredicateCorrelation",
                                        "ShowExplainCardinality"])
                     for k, v in CONF_PATHS.items()},
            "optprofile_databases.conf": open(DBCONF, encoding="utf-8",
                                              errors="replace").read(),
            "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    data = {}
    for tag in a.tags:
        coll, flat = run_tag(tag)
        data[tag] = {"coll": coll, "exec": flat}
        print(f"[{tag}] done: {len(coll)} collected, {len(flat)} executed",
              flush=True)

    base = "hqbird" if "hqbird" in data else list(data)[0]
    report = {"conf": meta["conf"], "suites": {}}
    for suite in SUITES:
        rows = {tg: {r["query_id"]: r for r in data[tg]["exec"]
                     if r["suite"] == suite} for tg in data}
        for tg in ("impropt", "optprofile"):
            if tg not in data:
                continue
            rows[tag] = {r["query_id"]: r for r in data[tag]["exec"]
                         if r["suite"] == suite}
        qids = sorted(set.intersection(*[
            set(r) for r in rows.values()]))
        summ = {"n": len(qids), "sum_ms": {}, "geo_vs_hqbird": {},
                "plan_diff_vs_hqbird": [], "checksum_diff": [],
                "timeouts": {}, "errors": {}}
        for tag in TARGETS:
            ms = [rows[tag][q]["median_ms"] for q in qids
                  if rows[tag][q]["median_ms"]]
            summ["sum_ms"][tag] = round(sum(ms), 1)
            summ["timeouts"][tag] = sum(1 for q in qids
                                        if rows[tag][q]["timed_out"])
            summ["errors"][tag] = sum(1 for q in qids
                                      if rows[tag][q]["error"])
        for tag in rows:
            if tag == "hqbird":
                continue
            if "hqbird" not in rows:
                continue
            ratios = [rows[tag][q]["median_ms"] /
                      rows["hqbird"][q]["median_ms"]
                      for q in qids
                      if rows[tag][q]["median_ms"] and
                      rows["hqbird"][q]["median_ms"]]
            summ["geo_vs_hqbird"][tag] = round(geo(ratios), 4)
        # планы и checksums
        coll_by = {tag: {(r["query_id"]): r for r in data[tag]["coll"]
                         if r["suite"] == suite} for tag in data}
        for q in qids:
            b = coll_by.get("hqbird", {}).get(q)
            for tag in rows:
                if tag == "hqbird":
                    continue
                c = coll_by[tag].get(q)
                if b and c and norm(b["detailed_plan"]) != \
                        norm(c["detailed_plan"]):
                    summ["plan_diff_vs_hqbird"].append(f"{tag}:{q}")
            chs = {rows[t][q]["checksum"] for t in rows
                   if rows[t][q]["checksum"]}
            if len(chs) > 1:
                summ["checksum_diff"].append(q)
        report["suites"][suite] = summ

    json.dump(report, open(os.path.join(OUT, "report.json"), "w",
                           encoding="utf-8"), indent=1, ensure_ascii=False)
    meta["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    json.dump(meta, open(os.path.join(OUT, "run_meta.json"), "w",
                         encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps(report, indent=1, ensure_ascii=False))
    print("DONE ->", OUT, flush=True)
    sys.stdout.flush()
    os._exit(0)  # daemon-потоки сторожа вешают финализацию python


if __name__ == "__main__":
    main()
