"""Матрица конфигураций оптимизатора на выделенном инстансе (§7 плана).

Сессионный SET OPTIMIZE недоступен через DSQL (isql-only), поэтому все
режимы переключаются через firebird.conf выделенного инстанса + рестарт
службы — это выделенная машина (dellg15), конфигом владеем.

Режимы:
  first_rows     : OptimizeForFirstRows = true  (совпадает с конфигом
                   базового 3055 и локальными эталонами)
  all_rows       : OptimizeForFirstRows = false (дефолт FB5)
  subquery_conv  : all_rows + SubQueryConversion = true (FB 5.0.1+)

На каждый режим: рестарт, планы (collector) по job и контрольному набору
stats, исполнение (runner: прогрев+медиана) контроля stats и полного job.
Результат: results/dedicated_dellg15/optimize_matrix/<mode>/...

Запуск:
  python bench/harness/optimize_matrix.py --host dellg15.local:3055 \
      --ssh-host dellg15 --modes first_rows all_rows subquery_conv
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

BASE = os.path.join(ROOT, "results", "dedicated_dellg15", "optimize_matrix")
CONF_REMOTE = "C:/HQbird/Firebird50/firebird.conf"
CONF_TMP = "E:/fbdata/conf_mode.conf"
GOLDEN_DIR = "E:/fbdata/golden"
WORK_DIR = "E:/fbdata/work"
SVC = "FirebirdServerHQBirdInstanceFB5"

MODES = {
    "first_rows": {"OptimizeForFirstRows": "true"},
    "all_rows": {"OptimizeForFirstRows": "false"},
    "subquery_conv": {"OptimizeForFirstRows": "false",
                      "SubQueryConversion": "true"},
}


def sh(cmd: str, timeout: int = 600) -> str:
    if SSH_HOST == "local":
        # shell=True: cmd /c списком аргументов калечит кавычки/пути
        r = subprocess.run(cmd, shell=True, capture_output=True,
                           text=True, timeout=timeout)
    else:
        r = subprocess.run(["ssh", SSH_HOST, cmd], capture_output=True,
                           text=True, timeout=timeout)
    return (r.stdout or "") + (r.stderr or "")


def push_file(local: str, remote: str):
    """Положить локальный файл на место (scp или локальный copy)."""
    if SSH_HOST == "local":
        import shutil
        shutil.copyfile(local, remote.replace("/", os.sep))
    else:
        subprocess.run(["scp", "-q", local, f"{SSH_HOST}:{remote}"],
                       check=True)


def set_conf_mode(mode: str):
    """Правка firebird.conf на dellg15: заменить/дописать параметры режима."""
    conf = sh('type "' + CONF_REMOTE.replace("/", chr(92)) + '"')
    # страховка: type мог не найти файл — не пишем однолинеечный конфиг
    assert "Providers" in conf and len(conf) > 10000, (
        f"conf read failed, got {len(conf)} bytes: {conf[:120]!r}")
    lines = conf.splitlines()
    want = MODES[mode]
    # сброс: удаляем существующие активные строки нужных параметров
    keys = "|".join(want)
    lines = [ln for ln in lines
             if not re.match(rf"^\s*({keys})\s*=", ln, re.I)]
    lines += [f"{k} = {v}" for k, v in want.items()]
    local = os.path.join(BASE, f"firebird.conf.{mode}")
    os.makedirs(BASE, exist_ok=True)
    with open(local, "w", newline="\r\n", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    push_file(local, CONF_TMP)
    sh(f'copy /y "{CONF_TMP.replace("/", chr(92))}" '
       f'"{CONF_REMOTE.replace("/", chr(92))}" >nul && echo CONF_SET')
    # контроль: читаем файл питоном (cmd-цепочки с кавычками ненадёжны)
    if SSH_HOST == "local":
        with open(CONF_REMOTE.replace("/", os.sep), encoding="utf-8",
                  errors="replace") as f:
            tail = f.read()
    else:
        tail = sh('findstr /i "' + keys + '" "' +
                  CONF_REMOTE.replace("/", chr(92)) + '"')
    for k, v in want.items():
        assert f"{k} = {v}" in tail, f"{k} not set:\n{tail}"


def restart_service():
    sh(f"net stop {SVC} & net start {SVC}", timeout=300)
    sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
    import fbenv
    fbenv.ensure_client()
    from firebird.driver import connect
    for i in range(60):
        time.sleep(1 + i // 10)
        try:
            db = connect(f"inet://{BENCH_HOST}/E:/fbdata/work/stats_pk_fk.fdb",
                         user="SYSDBA", password="masterkey")
            db.close()
            print("  service is back", flush=True)
            return
        except Exception:
            continue
    raise SystemExit("service did not come back")


def remote_copy(golden: str, work: str) -> str:
    if SSH_HOST == "local":
        # cmd copy обрезает большие файлы — копируем питоном + размер/хеш
        import hashlib
        import shutil
        src, dst = (golden.replace("/", os.sep), work.replace("/", os.sep))
        if not (os.path.exists(dst) and
                os.path.getsize(dst) == os.path.getsize(src)):
            shutil.copyfile(src, dst)
            print(f"  copied {src} -> {dst} ({os.path.getsize(dst)} B)",
                  flush=True)
        assert os.path.getsize(src) == os.path.getsize(dst), (
            f"copy truncated: {os.path.getsize(dst)} of {os.path.getsize(src)}")
        h = hashlib.sha256()
        with open(dst, "rb") as f:
            while chunk := f.read(1 << 22):
                h.update(chunk)
        return h.hexdigest()
    r = sh('copy /y "' + golden.replace("/", chr(92)) + '" "' +
           work.replace("/", chr(92)) + '" >nul && certutil -hashfile "' +
           work.replace("/", chr(92)) + '" SHA256')
    for ln in r.splitlines():
        ln = ln.strip()
        if len(ln) == 64 and re.fullmatch(r"[0-9a-f]{64}", ln.lower()):
            return ln.lower()
    return ""


def run_mode(mode: str, control: list[str]):
    import fbenv
    fbenv.HOST_PORT = BENCH_HOST
    from collector import collect_suite
    from runner import run_suite
    from phase0_make_baseline import flatten_exec
    import pipeline

    run_dir = os.path.join(BASE, mode)
    os.makedirs(run_dir, exist_ok=True)
    work_stats = WORK_DIR + "/stats_pk_fk.fdb"
    work_imdb = WORK_DIR + "/imdb_work.fdb"

    print(f"[{mode}] collecting plans (job + stats control)", flush=True)
    collected = []
    collected += collect_suite(work_stats, "stats-ceb", only_ids=control)
    collected += collect_suite(work_stats, "stats-ceb-single",
                               only_ids=control)
    collected += collect_suite(work_imdb, "job")
    coll_by_qid = {r["query_id"]: r for r in collected}
    pipeline.save_parquet(collected, os.path.join(run_dir, "collected.parquet"))

    print(f"[{mode}] executing stats control", flush=True)
    exec_rows = []
    exec_rows += run_suite(work_stats, "stats-ceb", only_ids=control,
                           per_query_timeout_s=180, progress=False)
    exec_rows += run_suite(work_stats, "stats-ceb-single", only_ids=control,
                           per_query_timeout_s=180, progress=False)
    print(f"[{mode}] executing full job", flush=True)
    exec_rows += run_suite(work_imdb, "job", per_query_timeout_s=600,
                           progress=True)
    flat = flatten_exec(exec_rows, coll_by_qid)
    # JOB-агрегаты дают строки (MIN(title)), stats — int: одна колонка
    # parquet не может быть смешанной — приводим к str (сравнения в матрице
    # идут по checksum, не по result_value)
    for r in flat:
        if r.get("result_value") is not None:
            r["result_value"] = str(r["result_value"])
    pipeline.save_parquet(flat, os.path.join(run_dir, "executed.parquet"))
    meta = {"mode": mode, "conf": MODES[mode],
            "db_sha_stats": STATS_SHA, "db_sha_imdb": IMDB_SHA,
            "bench_host": BENCH_HOST,
            "finished_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    json.dump(meta, open(os.path.join(run_dir, "run_meta.json"), "w",
                         encoding="utf-8"), indent=1)
    print(f"[{mode}] done -> {run_dir}", flush=True)


def compare(modes_done: list[str]):
    import pipeline
    summary = {}
    base = None
    for mode in modes_done:
        rows = pipeline.load_parquet(
            os.path.join(BASE, mode, "executed.parquet"))
        by_q = {r["query_id"]: r for r in rows}
        coll = pipeline.load_parquet(
            os.path.join(BASE, mode, "collected.parquet"))
        summary[mode] = {
            "plans": {r["query_id"]: r.get("plan_hash") for r in coll},
            "exec": {q: {"median_ms": r.get("median_ms"),
                         "fetches": r.get("fetches"),
                         "record_reads": r.get("record_reads"),
                         "checksum": r.get("checksum")}
                     for q, r in by_q.items()},
        }
        if base is None:
            base = mode
    out = {}
    for mode in modes_done:
        if mode == base:
            continue
        plan_same = plan_diff = 0
        diff_ids = []
        for qid, ph in summary[base]["plans"].items():
            ph2 = summary[mode]["plans"].get(qid)
            if ph and ph2:
                if ph == ph2:
                    plan_same += 1
                else:
                    plan_diff += 1
                    diff_ids.append(qid)
        t, f_, r_ = [], [], []
        for qid, e1 in summary[base]["exec"].items():
            e2 = summary[mode]["exec"].get(qid)
            if not e2 or not e1["median_ms"] or not e2["median_ms"]:
                continue
            t.append(e2["median_ms"] / e1["median_ms"])
            if e1["fetches"] and e2["fetches"]:
                f_.append(e2["fetches"] / e1["fetches"])
            if e1["record_reads"] and e2["record_reads"]:
                r_.append(e2["record_reads"] / e1["record_reads"])
        t.sort(), f_.sort(), r_.sort()
        out[f"{mode}_vs_{base}"] = {
            "plans_compared": plan_same + plan_diff,
            "plans_changed": plan_diff,
            "changed_ids": diff_ids,
            "time_ratio_median": t[len(t) // 2] if t else None,
            "time_ratio_p90": t[int(0.9 * (len(t) - 1))] if t else None,
            "fetches_ratio_max": f_[-1] if f_ else None,
            "reads_ratio_max": r_[-1] if r_ else None,
            "results_diff": sum(
                1 for qid, e1 in summary[base]["exec"].items()
                if e1["checksum"] and summary[mode]["exec"].get(qid, {})
                .get("checksum") and e1["checksum"] !=
                summary[mode]["exec"][qid]["checksum"]),
        }
    json.dump(out, open(os.path.join(BASE, "matrix_report.json"), "w",
                        encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps({k: {kk: vv for kk, vv in v.items()
                          if kk != "changed_ids"}
                      for k, v in out.items()}, indent=2, ensure_ascii=False))
    print("written", os.path.join(BASE, "matrix_report.json"))


SSH_HOST = "dellg15"
BENCH_HOST = "dellg15.local:3055"
STATS_SHA = IMDB_SHA = ""


def main():
    global SSH_HOST, BENCH_HOST, STATS_SHA, IMDB_SHA
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="dellg15.local:3055")
    ap.add_argument("--ssh-host", default="dellg15")
    ap.add_argument("--modes", nargs="+", default=list(MODES))
    a = ap.parse_args()
    SSH_HOST, BENCH_HOST = a.ssh_host, a.host

    cal = yaml.safe_load(open(os.path.join(ROOT, "results", "calibration",
                                           "8d618622f064.yaml"),
                              encoding="utf-8"))
    control = cal["control_set"]

    STATS_SHA = remote_copy(f"{GOLDEN_DIR}/stats_pk_fk.fdb",
                            f"{WORK_DIR}/stats_pk_fk.fdb")
    IMDB_SHA = remote_copy(f"{GOLDEN_DIR}/imdb_fb5.fdb",
                           f"{WORK_DIR}/imdb_work.fdb")
    print(f"work copies: stats={STATS_SHA[:12]} imdb={IMDB_SHA[:12]}",
          flush=True)

    for mode in a.modes:
        print(f"=== mode {mode}: {MODES[mode]} ===", flush=True)
        set_conf_mode(mode)
        restart_service()
        run_mode(mode, control)
    compare(a.modes)


if __name__ == "__main__":
    main()
