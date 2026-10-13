"""Замеры на выделенной машине (dellg15, HQbird FB5 @ 3055) — §7/§10.

A/A на выделенном инстансе: N прогонов одного и того же корпуса на одной
рабочей копии, дрейф времени/счётчиков между прогонами. Отвечает на вопрос
плана «замеряемо ли время» (локальный 3055 давал систематический дрейф ×0.44
из-за фоновых агентов HQbird).

Клиент раннера — локальная машина (LAN): замер включает 2 roundtrip на
счётчики и fetch 1-строчных результатов, для запросов от десятков мс это
шум << 1%.

Запуск:
  FB_HOSTPORT=dellg15.local:3055 python bench/harness/bench_dedicated.py \
      --golden-dir "E:/fbdata/golden" --work-dir "E:/fbdata/work" \
      --aa-runs 3 [--job-subset 10a 13a 17b 19a 22c 8c]
"""
from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESULTS = os.path.join(ROOT, "results", "dedicated_dellg15")
REMOTE_HOST = os.environ.get("DELLG15_SSH", "dellg15")


def percentile(sorted_vals, p):
    if not sorted_vals:
        return float("nan")
    k = min(len(sorted_vals) - 1, max(0, int(round(p / 100 * (len(sorted_vals) - 1)))))
    return sorted_vals[k]


def remote_copy(golden: str, work: str):
    """Побайтовая копия золотого файла на целевой машине + сверка SHA-256."""
    if REMOTE_HOST == "local":
        # запуск на самой машине замеров: shutil + hashlib, без cmd-квотинга
        import hashlib
        import shutil
        src, dst = golden.replace("/", "\\"), work.replace("/", "\\")
        shutil.copyfile(src, dst)
        h = hashlib.sha256()
        with open(dst, "rb") as f:
            while chunk := f.read(1 << 22):
                h.update(chunk)
        return h.hexdigest()
    else:
        r = subprocess.run(
            ["ssh", REMOTE_HOST,
             f"copy /y {golden.replace('/', chr(92))} "
             f"{work.replace('/', chr(92))} >nul && "
             f"certutil -hashfile {work.replace('/', chr(92))} SHA256"],
            capture_output=True, text=True)
    sha = ""
    for ln in r.stdout.splitlines():
        ln = ln.strip()
        if len(ln) == 64 and all(c in "0123456789abcdef" for c in ln.lower()):
            sha = ln.lower()
    return sha


def run_one(work_db: str, suites_and_ids):
    os.environ.setdefault("FB_HOSTPORT", REMOTE_BENCH_HOST)
    sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
    import fbenv  # noqa: E402
    fbenv.HOST_PORT = REMOTE_BENCH_HOST      # явная цель замеров
    from runner import run_suite
    from phase0_make_baseline import flatten_exec
    t0 = time.perf_counter()
    by_qid = {}
    for suite, only_ids in suites_and_ids:
        rows = run_suite(work_db, suite, only_ids=only_ids,
                         per_query_timeout_s=180, warmup=False, repeats=2,
                         progress=False)
        by_qid.update({r["query_id"]: r
                       for r in flatten_exec(rows)})
    return by_qid, time.perf_counter() - t0


def noise(runs_rows: list[dict]):
    """runs_rows: список {qid: rec}. Возвращает дрейф между соседними прогонами."""
    r_time, r_fetch, r_reads, disagree, pairs = [], [], [], 0, 0
    for a, b in zip(runs_rows, runs_rows[1:]):
        for qid, ra in a.items():
            rb = b.get(qid)
            if not rb or ra.get("error") or rb.get("error") or \
                    ra.get("timed_out") or rb.get("timed_out"):
                continue
            pairs += 1
            if ra.get("median_ms") and rb.get("median_ms"):
                r_time.append(rb["median_ms"] / ra["median_ms"])
            if ra.get("fetches") and rb.get("fetches"):
                r_fetch.append(rb["fetches"] / ra["fetches"])
            if ra.get("record_reads") and rb.get("record_reads"):
                r_reads.append(rb["record_reads"] / ra["record_reads"])
            if ra.get("result_value") is not None and \
                    ra["result_value"] != rb.get("result_value"):
                disagree += 1

    def stats(v):
        v = sorted(x for x in v if x == x)
        return {"p50": percentile(v, 50), "p90": percentile(v, 90),
                "p99": percentile(v, 99), "max": v[-1] if v else float("nan"),
                "n": len(v)}

    return {"time_ratio": stats(r_time), "fetches_ratio": stats(r_fetch),
            "record_reads_ratio": stats(r_reads),
            "result_disagreements": disagree, "pairs": pairs}


def per_query_cv(runs_rows):
    out = {}
    for qid in runs_rows[0]:
        vals = [r[qid].get("median_ms") for r in runs_rows
                if r.get(qid) and r[qid].get("median_ms")]
        if len(vals) >= 2 and statistics.mean(vals) > 0:
            out[qid] = round(statistics.pstdev(vals) / statistics.mean(vals), 4)
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def main():
    global REMOTE_BENCH_HOST
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="dellg15.local:3055")
    ap.add_argument("--golden-dir", default="E:/fbdata/golden")
    ap.add_argument("--stats-golden", default=None)
    ap.add_argument("--imdb-golden", default=None)
    ap.add_argument("--work-dir", default="E:/fbdata/work")
    ap.add_argument("--aa-runs", type=int, default=3)
    ap.add_argument("--job-subset", nargs="*",
                    default=["1a", "10a", "13a", "17b", "19a", "22c"])
    a = ap.parse_args()
    REMOTE_BENCH_HOST = a.host
    os.makedirs(RESULTS, exist_ok=True)

    # --- контрольный набор stats (тот же, что в калибровке фазы 0/1)
    import yaml
    cal = yaml.safe_load(open(os.path.join(
        ROOT, "results", "calibration", "8d618622f064.yaml"), encoding="utf-8"))
    control = cal["control_set"]

    work_stats = a.work_dir + "/stats_pk_fk.fdb"
    stats_golden = a.stats_golden or (a.golden_dir + "/stats_pk_fk.fdb")
    sha = remote_copy(stats_golden, work_stats)
    print(f"work copy stats: sha256={sha[:16]}...", flush=True)

    runs = []
    suites_and_ids = [("stats-ceb", control), ("stats-ceb-single", control)]
    for i in range(a.aa_runs):
        by_qid, wall = run_one(work_stats, suites_and_ids)
        runs.append(by_qid)
        print(f"stats aa run {i + 1}/{a.aa_runs}: {len(by_qid)} queries, "
              f"wall {wall:.0f}s", flush=True)
    rep = {"stats_ceb_control": noise(runs),
           "stats_per_query_time_cv": per_query_cv(runs)}

    # --- JOB-подмножество
    work_imdb = a.work_dir + "/imdb_work.fdb"
    imdb_golden = a.imdb_golden or (a.golden_dir + "/imdb_fb5.fdb")
    sha = remote_copy(imdb_golden, work_imdb)
    print(f"work copy imdb: sha256={sha[:16]}...", flush=True)
    jids = list(a.job_subset)  # id файлов в queries/job без префикса
    jruns = []
    for i in range(a.aa_runs):
        by_qid, wall = run_one(work_imdb, [("job", jids)])
        jruns.append(by_qid)
        print(f"job aa run {i + 1}/{a.aa_runs}: {len(by_qid)} queries, "
              f"wall {wall:.0f}s", flush=True)
    rep["job_subset"] = noise(jruns)
    rep["job_per_query_time_cv"] = per_query_cv(jruns)

    dst = os.path.join(RESULTS, "aa_dedicated.json")
    json.dump(rep, open(dst, "w", encoding="utf-8"), indent=1,
              ensure_ascii=False)
    print(json.dumps({k: v for k, v in rep.items() if not k.endswith("_cv")},
                     indent=2))
    print("written", dst)


if __name__ == "__main__":
    main()
