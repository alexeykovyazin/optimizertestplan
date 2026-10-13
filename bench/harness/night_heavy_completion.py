"""Ночной контур, элемент 1: полное исполнение тяжёлых корневых запросов,
цензурированных в быстром baseline (таймаут 120 с). Бюджет — 900 с на
исполнение; счётчики детерминированы, поэтому главная ценность — полные
fetches/record_reads и время для Heavy-хвоста.

Результат мержится в хранимый эталон того же ключа (файл БД и конфигурация
не менялись); оригинал сохраняется как executed.parquet.bak-pre-heavy.

Запуск: python bench/harness/night_heavy_completion.py <baseline_key_id> [--config pk_fk]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
import pipeline  # noqa: E402
from runner import run_suite  # noqa: E402
from phase0_make_baseline import flatten_exec, load_truth  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline_key_id")
    ap.add_argument("--config", default="pk_fk")
    ap.add_argument("--timeout-s", type=float, default=900.0)
    args = ap.parse_args()

    bdir = os.path.join(pipeline.RESULTS_DIR, "baselines", args.baseline_key_id)
    base_rows = pipeline.load_parquet(os.path.join(bdir, "executed.parquet"))
    heavy_ids = [r["query_id"] for r in base_rows
                 if r["suite"] == "stats-ceb" and r.get("timed_out")]
    print(f"heavy queries to complete: {len(heavy_ids)}")
    if not heavy_ids:
        return

    key = pipeline.baseline_key(args.config)
    assert pipeline.key_id(key) == args.baseline_key_id, \
        "ключ среды изменился — мержить некуда, снимайте новый эталон"

    run_dir = pipeline.new_run_dir("night_heavy")
    work = pipeline.make_work_copy(args.config, run_dir)

    executed = run_suite(work, "stats-ceb", only_ids=heavy_ids,
                         per_query_timeout_s=args.timeout_s, repeats=2)
    executed_f = flatten_exec(executed)

    # сверка с истиной
    truth = load_truth("stats-ceb")
    mismatch = []
    for r in executed_f:
        v = r.get("result_value")
        if v is not None and truth.get(r["query_id"]) is not None and \
                v != truth[r["query_id"]]:
            mismatch.append((r["query_id"], v, truth[r["query_id"]]))
    print(f"truth check: mismatches={len(mismatch)} {mismatch[:5]}")

    pipeline.save_parquet(executed_f, os.path.join(run_dir, "executed.parquet"))

    # мерж в эталон того же ключа
    bak = os.path.join(bdir, "executed.parquet.bak-pre-heavy")
    if not os.path.exists(bak):
        data = open(os.path.join(bdir, "executed.parquet"), "rb").read()
        open(bak, "wb").write(data)
    by_qid = {r["query_id"]: r for r in base_rows}
    replaced = 0
    for r in executed_f:
        if not r.get("timed_out") and not r.get("error"):
            by_qid[r["query_id"]] = r
            replaced += 1
    merged = [by_qid[q] for q in by_qid]
    pipeline.save_parquet(merged, os.path.join(bdir, "executed.parquet"))
    print(f"merged: {replaced}/{len(heavy_ids)} heavy queries completed "
          f"-> {bdir} (backup: {os.path.basename(bak)})")
    with open(os.path.join(run_dir, "run_meta.json"), "w",
              encoding="utf-8") as f:
        json.dump({"kind": "night_heavy_completion",
                   "key_id": args.baseline_key_id,
                   "queries": heavy_ids,
                   "replaced": replaced,
                   "truth_mismatches": len(mismatch),
                   "timeout_s": args.timeout_s}, f, indent=2)


if __name__ == "__main__":
    main()
