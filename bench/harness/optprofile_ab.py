"""A/B профилей оптимизации (ветка feature/optimization-profile) на dellg15.

Запуск (на dellg15):
  set FB_CLIENT_DIR=C:\\HQbird\\Firebird50
  python E:/bench/harness/optprofile_ab.py

Протокол (запрос — 5 самых медленных JOB corr-прогона, или --qids):
  1. PLAN-ONLY без профиля (databases.conf без OptimizationProfileFile,
     рестарт FB_optprofile), prepare -> план
  2. PLAN-ONLY с профилем (OptimizationProfileFile по алиасам, рестарт)
  3. дифф планов; для изменивших — исполнение в обоих режимах
     (2 прогона, 1-й — прогрев), серверный таймаут 600 c
Результат: E:\\results\\optprofile_ab\\{report.json, plans.md, times.csv}
"""
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, r"E:\bench\harness")

OUT = r"E:\results\optprofile_ab"
ROOT = r"E:\fb50-optprofile"
DBCONF = os.path.join(ROOT, "databases.conf")
SVC = "FB_optprofile"
PORT = 3180
QDIR = r"E:\bench\queries\job"
CORR_EXEC = r"E:\results\dedicated_dellg15\impropt_matrix\corr\executed.parquet"
CORR_COLL = r"E:\results\dedicated_dellg15\impropt_matrix\corr\collected.parquet"
IMDB_ALIAS, STATS_ALIAS = "imdb_opt", "stats_opt"
TIMEOUT_MS = 600_000

PROFILE_ON = f"""\
{IMDB_ALIAS} = E:\\fbdata\\optprofile_work\\imdb_fb5.fdb
{{
\tOptimizationProfileFile = E:/fbdata/optprofile_work/imdb.profile
}}
{STATS_ALIAS} = E:\\fbdata\\optprofile_work\\stats_pk_fk.fdb
{{
\tOptimizationProfileFile = E:/fbdata/optprofile_work/stats.profile
}}
"""
PROFILE_OFF = f"""\
{IMDB_ALIAS} = E:\\fbdata\\optprofile_work\\imdb_fb5.fdb
{STATS_ALIAS} = E:\\fbdata\\optprofile_work\\stats_pk_fk.fdb
"""


def sh(cmd, timeout=300):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       encoding="cp1251", errors="replace", timeout=timeout)
    return (r.stdout or "") + (r.stderr or "")


def set_profile(on: bool):
    with open(DBCONF, "w", newline="\r\n", encoding="utf-8") as f:
        f.write(PROFILE_ON if on else PROFILE_OFF)
    sh(f"net stop {SVC} >nul 2>&1")
    sh(f"net start {SVC}")
    import socket
    for i in range(60):
        time.sleep(1 + i // 10)
        try:
            with socket.create_connection(("127.0.0.1", PORT), 2):
                return
        except OSError:
            continue
    raise SystemExit("FB_optprofile did not come back")


def connect(alias):
    import fbenv
    fbenv.HOST_PORT = f"localhost:{PORT}"
    fbenv.ensure_client()
    from firebird.driver import connect
    db = connect(f"inet://localhost:{PORT}/{alias}",
                 user="SYSDBA", password="masterkey", charset="UTF8")
    db.info.set_statement_timeout = TIMEOUT_MS
    return db


def norm(plan: str) -> str:
    """Нормализация для сравнения: вырезать rows=, сжать пробелы."""
    t = re.sub(r"\s*\(rows=[\d.]+\)", "", plan or "")
    return re.sub(r"\s+", " ", t).strip()


# 5 самых медленных corr-прогона (вычислено локально из executed.parquet)
SLOWEST5 = ["19d", "8c", "9d", "9c", "8d"]


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--qids", nargs="+", default=None)
    ap.add_argument("--skip-exec", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    qids = a.qids or SLOWEST5
    print("queries:", qids, flush=True)
    sqls = {q: open(os.path.join(QDIR, q + ".sql"),
                    encoding="utf-8").read() for q in qids}

    corr_plans = {}  # заполняется из plans.md A/B прогона при наличии

    plans = {}
    for on in (False, True):
        set_profile(on)
        tag = "profile" if on else "plain"
        db = connect(IMDB_ALIAS)
        cur = db.cursor()
        for q in qids:
            ps = cur.prepare(sqls[q])
            plans[(q, tag)] = {"plan": ps.plan,
                               "detailed": ps.detailed_plan}
            print(f"[{tag}] {q} prepared", flush=True)
        cur.close()
        db.close()

    changed = [q for q in qids
               if norm(plans[(q, "plain")]["detailed"]) !=
               norm(plans[(q, "profile")]["detailed"])]
    print("plans changed:", changed, flush=True)

    times = []
    if changed and not a.skip_exec:
        for on in (False, True):
            set_profile(on)
            tag = "profile" if on else "plain"
            db = connect(IMDB_ALIAS)
            cur = db.cursor()
            for q in changed:
                runs = []
                for rep in range(2):
                    t0 = time.perf_counter()
                    cur.execute(sqls[q])
                    cur.fetchall()
                    runs.append(round((time.perf_counter() - t0) * 1000, 1))
                    print(f"[{tag}] {q} run{rep}: {runs[-1]:,.0f} ms",
                          flush=True)
                times.append({"qid": q, "mode": tag, "runs_ms": runs,
                              "median_ms": sorted(runs)[0]})
            cur.close()
            db.close()

    json.dump({"qids": qids, "changed": changed, "plans": {
                   f"{q}|{t}": v for (q, t), v in plans.items()},
               "times": times},
              open(os.path.join(OUT, "report.json"), "w",
                   encoding="utf-8"), indent=1, ensure_ascii=False)
    with open(os.path.join(OUT, "plans.md"), "w", encoding="utf-8",
              newline="\n") as f:
        f.write("# OptProfile A/B: планы 5 самых медленных JOB\n\n")
        for q in qids:
            mark = " ⚠ СМЕНА ПЛАНА" if q in changed else ""
            f.write(f"## {q}{mark}\n\n```sql\n{sqls[q].strip()}\n```\n\n")
            for tag, title in (("plain", "Без профиля"),
                               ("profile", "С профилем")):
                f.write(f"**{title}:**\n```\n"
                        f"{plans[(q, tag)]['detailed']}\n```\n\n")
            cq = corr_plans.get(q)
            if cq:
                f.write("**Для справки: план corr-прогона (v5.0-impr-opt):"
                        "\n```\n" + cq + "\n```\n\n")
    if times:
        import csv
        with open(os.path.join(OUT, "times.csv"), "w", newline="",
                  encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["qid", "mode", "runs_ms",
                                              "median_ms"])
            w.writeheader()
            w.writerows(times)
    print("DONE ->", OUT, flush=True)


if __name__ == "__main__":
    main()
