"""Фаза 0, шаг 1: эталонный прогон (baseline) корпуса stats-ceb.

Состав:
  1. Побайтовая копия золотого файла (pk_fk — основная конфигурация быстрого
     контура; pk — ночное измерение, запускается отдельно).
  2. collector по всему корпусу (подготовка + планы, запросы не исполняются)
     — заодно измеряется бюджет компиляции.
  3. runner: исполнение stats-ceb (146, прогрев + медиана из 3), одно-табличных
     (632) и выборки подпланов; счётчики + время + строки.
  4. Валидация: сравнение COUNT(*) с истинными кардинальностями DuckDB (4.5.5).
  5. Калибровка fast/heavy + контрольный набор (8.1).
  6. Копия в results/baselines/<key_id>/.

Запуск: python bench/harness/phase0_make_baseline.py [--config pk_fk]
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
import pipeline  # noqa: E402
import calibrate  # noqa: E402
import fbenv  # noqa: E402
from collector import collect_suite  # noqa: E402
from runner import run_suite  # noqa: E402

TRUTH_DIR = os.path.join(ROOT, "bench", "truth", "stats-ceb")


def load_truth(suite: str) -> dict:
    import pyarrow.parquet as pq
    path = os.path.join(TRUTH_DIR, f"{suite}.parquet")
    if not os.path.exists(path):
        return {}
    return {r["query_id"]: r["true_rows"]
            for r in pq.read_table(path).to_pylist()}


def flatten_exec(rows: list[dict], collected_by_qid: dict | None = None) -> list[dict]:
    out = []
    for r in rows:
        c = r.get("counters") or {}
        flat = dict(r)
        if collected_by_qid and r["query_id"] in collected_by_qid:
            for k in ("plan", "detailed_plan", "plan_hash",
                      "detailed_plan_hash"):
                flat[k] = collected_by_qid[r["query_id"]].get(k)
        flat["fetches"] = c.get("fetches")
        flat["record_reads"] = sum((c.get("seq_reads") or {}).values()) + \
            sum((c.get("idx_reads") or {}).values())
        flat["counters"] = json.dumps(c, ensure_ascii=False)
        flat["runs_ms"] = json.dumps(r.get("runs_ms"))
        out.append(flat)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="pk_fk", choices=["pk", "pk_fk"])
    ap.add_argument("--subplan-sample", type=int, default=50)
    ap.add_argument("--label", default="baseline")
    args = ap.parse_args()

    key = pipeline.baseline_key(args.config)
    kid = pipeline.key_id(key)
    run_dir = pipeline.new_run_dir(f"{args.label}_{args.config}")
    t_start = time.perf_counter()
    print(f"run dir: {run_dir}\nkey: {key} -> {kid}")

    work = pipeline.make_work_copy(args.config, run_dir)

    # --- collector: весь корпус, запросы не исполняются
    t0 = time.perf_counter()
    collected = []
    for suite in ("stats-ceb", "stats-ceb-single", "stats-ceb-subplans"):
        rows = collect_suite(work, suite)
        collected.extend(rows)
        prep_fail = sum(1 for r in rows if r["error"])
        print(f"collector {suite}: {len(rows)} queries, "
              f"errors={prep_fail}, "
              f"prepare_total={sum(r['prepare_ms'] or 0 for r in rows):.0f} ms")
    compile_budget_s = time.perf_counter() - t0
    print(f"compile budget: {compile_budget_s:.1f} s")

    # --- runner (таймаут с запасом: в корпусе есть запросы на ~3 мин;
    #     адаптивные повторы не дают хвосту тяжёлых раздуть прогон)
    executed = []
    t0 = time.perf_counter()
    executed += run_suite(work, "stats-ceb", per_query_timeout_s=120)
    executed += run_suite(work, "stats-ceb-single", per_query_timeout_s=120)
    sub_ids = sorted(f[:-4] for f in
                     os.listdir(os.path.join(ROOT, "bench", "queries",
                                             "stats-ceb-subplans"))
                     if f.endswith(".sql"))
    rng = random.Random(42)
    sample = rng.sample(sub_ids, min(args.subplan_sample, len(sub_ids)))
    executed += run_suite(work, "stats-ceb-subplans", only_ids=sample,
                          per_query_timeout_s=90)
    exec_budget_s = time.perf_counter() - t0
    print(f"executed: {len(executed)} queries in {exec_budget_s:.1f} s "
          f"(warmup+3 reps; subplans sample={len(sample)})")

    executed_f = flatten_exec(executed, {r["query_id"]: r for r in collected})

    # --- валидация против истины (DuckDB)
    mismatches = []
    truth_checked = 0
    for suite in ("stats-ceb", "stats-ceb-single", "stats-ceb-subplans"):
        truth = load_truth(suite)
        for r in executed_f:
            if r["suite"] == suite and r.get("result_value") is not None and \
               r["query_id"] in truth:
                truth_checked += 1
                if r["result_value"] != truth[r["query_id"]]:
                    mismatches.append((r["query_id"], r["result_value"],
                                       truth[r["query_id"]]))
    print(f"truth validation: checked={truth_checked}, "
          f"mismatches={len(mismatches)}")
    for m in mismatches[:10]:
        print("  MISMATCH:", m)

    # --- сохранить прогон
    pipeline.save_parquet(collected, os.path.join(run_dir, "collected.parquet"))
    pipeline.save_parquet(executed_f, os.path.join(run_dir, "executed.parquet"))
    meta = {
        "kind": "baseline" if args.label == "baseline" else args.label,
        "baseline_key": key, "key_id": kid,
        "compile_budget_s": round(compile_budget_s, 1),
        "exec_budget_s": round(exec_budget_s, 1),
        "queries_collected": len(collected),
        "queries_executed": len(executed),
        "truth_checked": truth_checked,
        "truth_mismatches": len(mismatches),
        "subplan_sample": sample,
    }
    with open(os.path.join(run_dir, "run_meta.json"), "w",
              encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    # --- калибровка
    cal = calibrate.calibrate(executed_f, suites=("stats-ceb",))
    cal_path = calibrate.save_calibration(cal, kid)
    n_fast = sum(1 for e in cal["entries"].values() if e["tier"] == "fast")
    print(f"calibration: fast={n_fast} heavy={len(cal['entries']) - n_fast}; "
          f"control set={len(cal['control_set'])} queries, "
          f"est {cal['control_est_ms']:.0f} ms -> {cal_path}")

    # --- копия эталона
    bdir = os.path.join(pipeline.RESULTS_DIR, "baselines", kid)
    os.makedirs(bdir, exist_ok=True)
    for name in ("collected.parquet", "executed.parquet", "run_meta.json"):
        data = open(os.path.join(run_dir, name), "rb").read()
        open(os.path.join(bdir, name), "wb").write(data)
    print(f"baseline stored: {bdir}")
    print(f"total wall time: {time.perf_counter() - t_start:.1f} s")


if __name__ == "__main__":
    main()
