"""Фаза 0: A/A-прогон — одна и та же сборка дважды на свежих побайтовых
копиях одного золотого файла. Даёт пороги шума для гейта (разделы 9, 10):
пороги выше p99 шума каждой метрики.

Запуск: python bench/harness/phase0_aa_noise.py <runA_dir> [<runB_dir>]
Если runB не указан — создаётся новый прогон на копии золотого файла.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
import pipeline  # noqa: E402
from runner import run_suite  # noqa: E402
from phase0_make_baseline import flatten_exec, load_truth  # noqa: E402


def percentile(sorted_vals, p):
    if not sorted_vals:
        return float("nan")
    k = min(len(sorted_vals) - 1, max(0, int(round(p / 100 * (len(sorted_vals) - 1)))))
    return sorted_vals[k]


def noise_stats(ratios):
    v = sorted(x for x in ratios if x is not None and x == x)
    if not v:
        return {"p50": float("nan"), "p90": float("nan"),
                "p99": float("nan"), "max": float("nan"), "n": 0}
    return {"p50": percentile(v, 50), "p90": percentile(v, 90),
            "p99": percentile(v, 99), "max": v[-1], "n": len(v)}


def main():
    run_a_dir = sys.argv[1]
    control_only = "--control-only" in sys.argv
    if control_only:
        sys.argv.remove("--control-only")
    if len(sys.argv) > 2:
        run_b_dir = sys.argv[2]
    else:
        run_b_dir = pipeline.new_run_dir("aa")
        work = pipeline.make_work_copy("pk_fk", run_b_dir)
        meta = json.load(open(os.path.join(run_a_dir, "run_meta.json"),
                              encoding="utf-8"))
        import calibrate
        cal = calibrate.load_calibration(meta["key_id"])
        only = cal["control_set"] if control_only else None
        executed = []
        for suite in ("stats-ceb", "stats-ceb-single"):
            executed += run_suite(work, suite, per_query_timeout_s=120,
                                  only_ids=only if suite == "stats-ceb" else None)
        pipeline.save_parquet(flatten_exec(executed),
                              os.path.join(run_b_dir, "executed.parquet"))
        with open(os.path.join(run_b_dir, "run_meta.json"), "w",
                  encoding="utf-8") as f:
            json.dump({"kind": "aa_control_only" if control_only else "aa",
                       "key_id": meta["key_id"]}, f)
        print(f"A/A run B: {run_b_dir}")

    a = {r["query_id"]: r for r in
         pipeline.load_parquet(os.path.join(run_a_dir, "executed.parquet"))}
    b = {r["query_id"]: r for r in
         pipeline.load_parquet(os.path.join(run_b_dir, "executed.parquet"))}

    r_time, r_fetch, r_reads, r_val = [], [], [], []
    for qid, ra in a.items():
        rb = b.get(qid)
        if not rb or ra.get("error") or rb.get("error") or \
           ra.get("timed_out") or rb.get("timed_out"):
            continue
        if ra.get("median_ms") and rb.get("median_ms"):
            r_time.append(rb["median_ms"] / ra["median_ms"])
        fa, fb = ra.get("fetches"), rb.get("fetches")
        if fa and fb:
            r_fetch.append(fb / fa)
        sa, sb = ra.get("record_reads"), rb.get("record_reads")
        if sa and sb:
            r_reads.append(sb / sa)
        if ra.get("result_value") is not None:
            r_val.append(1.0 if ra["result_value"] == rb.get("result_value")
                         else float("nan"))

    out = {
        "median_time_ratio_B_over_A": noise_stats(r_time),
        "fetches_ratio": noise_stats(r_fetch),
        "record_reads_ratio": noise_stats(r_reads),
        "result_disagreements": sum(1 for x in r_val if x != 1.0),
        "pairs_compared": len(r_time),
    }
    print(json.dumps(out, indent=2))
    dst = os.path.join(run_b_dir, "aa_noise.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("written", dst)


if __name__ == "__main__":
    main()
