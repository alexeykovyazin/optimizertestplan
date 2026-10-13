"""A/B прогона ветки IBSurgeon/hqbird v5.0-impr-opt на dellg15.

Запускается НА dellg15 (ssh-host=local): второй инстанс — Firebird 5,
собранный из ветки v5.0-impr-opt, root E:\fb50-impropt, порт 3056,
служба FB_impropt. Базовая матрица §7 (HQbird 5.0.5, порт 3055) не трогается.

Режимы (переключаются через firebird.conf инстанса + рестарт):
  stock : PredicateCorrelation = false — по документации ветки побайтно
          идентичен стоковому оптимизатору FB5; служит контролем
          эквивалентности (планы и checksums против базовой матрицы)
  corr  : PredicateCorrelation = true — back-off exponential для
          комбинации селективностей AND/OR

В обоих режимах ShowExplainCardinality = true (новинка ветки): в
detailed_plan попадают оценки кардинальности (rows=...).

Протокол: stock — 1 замер на запрос (планы+checksums, время ориентировочно),
corr — как в базовой матрице (repeats=2, runs[0] — прогрев, тяжёлые >15 c —
один замер). Сравнение — с
E:/results/dedicated_dellg15/optimize_matrix/first_rows/executed.parquet
(HQbird 5.0.5, OptimizeForFirstRows=true — тот же протокол).

Запуск (на dellg15):
  python bench/harness/impropt_matrix.py --modes stock corr
Результаты: results/dedicated_dellg15/impropt_matrix/<mode>/
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
import yaml  # noqa: E402

# на dellg15 результаты живут в E:\results (не ROOT/results) — env-оверрайд
BASE = os.environ.get(
    "IMPROPT_BASE",
    os.path.join(ROOT, "results", "dedicated_dellg15", "impropt_matrix"))
CONF_REMOTE = "E:/fb50-impropt/firebird.conf"
CONF_TMP = "E:/fbdata/impropt_conf_mode.conf"
GOLDEN_DIR = "E:/fbdata/golden"
WORK_DIR = "E:/fbdata/impropt_work"
SVC = "FB_impropt"
# базовая матрица §7 на этой же машине (HQbird 5.0.5, порт 3055)
BASELINE = os.environ.get(
    "IMPROPT_BASELINE",
    os.path.join(ROOT, "results", "dedicated_dellg15",
                 "optimize_matrix", "first_rows"))
CAL_YAML = os.environ.get(
    "IMPROPT_CAL", os.path.join(ROOT, "results", "calibration",
                                "8d618622f064.yaml"))

COMMON = {"OptimizeForFirstRows": "true", "ShowExplainCardinality": "true",
          # паритет кэшей/локов с инстансом HQbird (порт 3055)
          "DefaultDbCachePages": "2048", "LockMemSize": "20M",
          "LockHashSlots": "40099", "TempCacheLimit": "256M",
          "InlineSortThreshold": "16384"}
MODES = {
    "stock": {**COMMON, "PredicateCorrelation": "false"},
    "corr": {**COMMON, "PredicateCorrelation": "true"},
}


def sh(cmd: str, timeout: int = 600) -> str:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    return (r.stdout or "") + (r.stderr or "")


def push_file(local: str, remote: str):
    import shutil
    shutil.copyfile(local, remote.replace("/", os.sep))


def set_conf_mode(mode: str):
    conf_path = CONF_REMOTE.replace("/", os.sep)
    with open(conf_path, encoding="utf-8", errors="replace") as f:
        conf = f.read()
    assert "Providers" in conf and len(conf) > 5000, (
        f"conf read failed, got {len(conf)} bytes")
    lines = conf.splitlines()
    want = MODES[mode]
    keys = "|".join(want)
    lines = [ln for ln in lines
             if not re.match(rf"^\s*({keys})\s*=", ln, re.I)]
    lines += [f"{k} = {v}" for k, v in want.items()]
    os.makedirs(BASE, exist_ok=True)
    local = os.path.join(BASE, f"firebird.conf.{mode}")
    with open(local, "w", newline="\r\n", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    push_file(local, CONF_TMP)
    sh(f'copy /y "{CONF_TMP.replace("/", chr(92))}" '
       f'"{conf_path}" >nul && echo CONF_SET')
    with open(conf_path, encoding="utf-8", errors="replace") as f:
        tail = f.read()
    for k, v in want.items():
        assert f"{k} = {v}" in tail, f"{k} not set"


def restart_service():
    sh(f"net stop {SVC} & net start {SVC}", timeout=300)
    import fbenv
    fbenv.ensure_client()
    from firebird.driver import connect
    probe = WORK_DIR + "/stats_pk_fk.fdb"
    for i in range(60):
        time.sleep(1 + i // 10)
        try:
            db = connect(f"inet://{BENCH_HOST}/{probe}",
                         user="SYSDBA", password="masterkey")
            db.close()
            print("  service is back", flush=True)
            return
        except Exception:
            continue
    raise SystemExit("service did not come back")


def copy_work():
    """Рабочие копии голденов для impr-opt-инстанса (файловые копии)."""
    import hashlib
    import shutil
    os.makedirs(WORK_DIR.replace("/", os.sep), exist_ok=True)
    for name in ("stats_pk_fk.fdb", "imdb_fb5.fdb"):
        src = f"{GOLDEN_DIR}/{name}".replace("/", os.sep)
        dst = f"{WORK_DIR}/{name}".replace("/", os.sep)
        if not (os.path.exists(dst) and
                os.path.getsize(dst) == os.path.getsize(src)):
            print(f"  copying {name}...", flush=True)
            shutil.copyfile(src, dst)
        assert (os.path.getsize(src) == os.path.getsize(dst)), (
            f"copy truncated: {name}")
        h = hashlib.sha256()
        with open(dst, "rb") as f:
            while chunk := f.read(1 << 22):
                h.update(chunk)
        yield name, h.hexdigest()


def run_mode(mode: str, control: list[str], quick: bool):
    import fbenv
    fbenv.HOST_PORT = BENCH_HOST
    from collector import collect_suite
    from runner import run_suite
    from phase0_make_baseline import flatten_exec
    import pipeline

    run_dir = os.path.join(BASE, mode)
    os.makedirs(run_dir, exist_ok=True)
    work_stats = WORK_DIR + "/stats_pk_fk.fdb"
    work_imdb = WORK_DIR + "/imdb_fb5.fdb"
    reps = 1 if quick else 2
    timeout = 600

    print(f"[{mode}] collecting plans (job + stats control)", flush=True)
    collected = []
    collected += collect_suite(work_stats, "stats-ceb", only_ids=control)
    collected += collect_suite(work_stats, "stats-ceb-single",
                               only_ids=control)
    collected += collect_suite(work_imdb, "job")
    coll_by_qid = {r["query_id"]: r for r in collected}
    pipeline.save_parquet(collected, os.path.join(run_dir, "collected.parquet"))

    print(f"[{mode}] executing stats control "
          f"(repeats={reps})", flush=True)
    exec_rows = []
    exec_rows += run_suite(work_stats, "stats-ceb", only_ids=control,
                           per_query_timeout_s=180, repeats=reps,
                           progress=False)
    exec_rows += run_suite(work_stats, "stats-ceb-single", only_ids=control,
                           per_query_timeout_s=180, repeats=reps,
                           progress=False)
    print(f"[{mode}] executing full job (repeats={reps})", flush=True)
    exec_rows += run_suite(work_imdb, "job", per_query_timeout_s=timeout,
                           repeats=reps, progress=True)
    flat = flatten_exec(exec_rows, coll_by_qid)
    for r in flat:
        if r.get("result_value") is not None:
            r["result_value"] = str(r["result_value"])
    pipeline.save_parquet(flat, os.path.join(run_dir, "executed.parquet"))
    meta = {"mode": mode, "conf": MODES[mode], "quick": quick,
            "bench_host": BENCH_HOST,
            "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "build": "hqbird v5.0-impr-opt 56cf3322 (self-built VS2019)"}
    json.dump(meta, open(os.path.join(run_dir, "run_meta.json"), "w",
                         encoding="utf-8"), indent=1)
    print(f"[{mode}] done -> {run_dir}", flush=True)


def compare(modes_done: list[str]):
    import pipeline

    def load(d):
        rows = pipeline.load_parquet(os.path.join(d, "executed.parquet"))
        coll = pipeline.load_parquet(os.path.join(d, "collected.parquet"))
        return rows, coll

    base_rows, base_coll = load(BASELINE)
    base = {"plans": {r["query_id"]: r.get("plan_hash") for r in base_coll},
            "exec": {r["query_id"]: r for r in base_rows}}
    out = {}
    for mode in modes_done:
        rows, coll = load(os.path.join(BASE, mode))
        plans = {r["query_id"]: r for r in coll}
        exec_by_q = {r["query_id"]: r for r in rows}
        plan_same = plan_diff = res_diff = 0
        changed, res_changed = [], []
        t = []
        for qid, bph in base["plans"].items():
            ph = plans.get(qid, {}).get("plan_hash")
            if not ph:
                continue
            if ph == bph:
                plan_same += 1
            else:
                plan_diff += 1
                changed.append(qid)
            b = base["exec"].get(qid)
            e = exec_by_q.get(qid)
            if b and e and b.get("checksum") and e.get("checksum"):
                if b["checksum"] != e["checksum"]:
                    res_diff += 1
                    res_changed.append(qid)
            if b is not None and e is not None and \
                    b.get("median_ms") and e.get("median_ms"):
                t.append(e["median_ms"] / b["median_ms"])
        t.sort()
        out[mode] = {
            "plans_compared": plan_same + plan_diff,
            "plans_changed_vs_baseline": plan_diff,
            "changed_ids": changed,
            "results_diff_vs_baseline": res_diff,
            "results_diff_ids": res_changed,
            "time_vs_baseline_median": t[len(t) // 2] if t else None,
            "time_vs_baseline_p90": t[int(0.9 * (len(t) - 1))] if t else None,
        }
    os.makedirs(BASE, exist_ok=True)
    json.dump(out, open(os.path.join(BASE, "impropt_report.json"), "w",
                        encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps({k: {kk: (vv if kk != "changed_ids" else vv[:20])
                          for kk, vv in v.items()}
                      for k, v in out.items()}, indent=2, ensure_ascii=False))
    print("written", os.path.join(BASE, "impropt_report.json"))


SSH_HOST = "local"
BENCH_HOST = "localhost:3056"


def main():
    global SSH_HOST, BENCH_HOST
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="localhost:3056")
    ap.add_argument("--ssh-host", default="local")
    ap.add_argument("--modes", nargs="+", default=["stock", "corr"])
    ap.add_argument("--no-quick-stock", action="store_true",
                    help="полный протокол и для stock (4 повтора)")
    a = ap.parse_args()
    SSH_HOST, BENCH_HOST = a.ssh_host, a.host

    cal = yaml.safe_load(open(CAL_YAML, encoding="utf-8"))
    control = cal["control_set"]

    if os.environ.get("IMPROPT_NOCOPY") == "1":
        print("IMPROPT_NOCOPY=1: рабочие копии не обновляются "
              "(сохраняется собранная STAT$ статистика)", flush=True)
        shas = {}
    else:
        shas = dict(copy_work())
        print(f"work copies: stats={shas['stats_pk_fk.fdb'][:12]} "
              f"imdb={shas['imdb_fb5.fdb'][:12]}", flush=True)

    for mode in a.modes:
        print(f"=== mode {mode}: {MODES[mode]} ===", flush=True)
        set_conf_mode(mode)
        restart_service()
        run_mode(mode, control, quick=(mode == "stock"
                                       and not a.no_quick_stock))
    compare(a.modes)


if __name__ == "__main__":
    main()
