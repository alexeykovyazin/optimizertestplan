"""Быстрый контур (8.1) на одной сборке: только сборка-кандидат.

Этапы:
  0. Побайтовая копия золотого файла (read-only) уже на диске.
  1. Компиляция корпуса: prepare+план (без исполнения), бюджет замеряется.
  2a. Исполнение fast-запросов с изменившимся планом (vs эталон по хешу),
      таймаут = k x эталонное время.
  2b. Контрольный набор: счётчики + время.
  4. Гейт и отчёт (сравнение с хранимым эталоном). Этап 3 (живое A/B) — на
     выделенной машине, в фазе 0 не выполняется: подозрительные FAIL помечаются
     "needs confirmation".

Запуск:
  python bench/harness/fast_contour.py <baseline_key_id> [--label candidate]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
import pipeline  # noqa: E402
import calibrate  # noqa: E402
from collector import collect_suite  # noqa: E402
from runner import run_suite  # noqa: E402
from compare import compare_run, load_accepted  # noqa: E402
from ratchet import check_ratchets, load_ratchets  # noqa: E402
from phase0_make_baseline import flatten_exec, load_truth  # noqa: E402
import report  # noqa: E402

CORPUS = ("stats-ceb", "stats-ceb-single", "stats-ceb-subplans")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline_key_id")
    ap.add_argument("--label", default="candidate")
    ap.add_argument("--config", default="pk_fk")
    ap.add_argument("--mutate-plans", action="store_true",
                    help="симуляция кандидата: инвертировать хеши планов "
                         "у случайных 10 fast-запросов (для проверки контура)")
    args = ap.parse_args()

    bdir = os.path.join(pipeline.RESULTS_DIR, "baselines", args.baseline_key_id)
    assert os.path.isdir(bdir), f"нет эталона {bdir}"
    base_exec = pipeline.load_parquet(os.path.join(bdir, "executed.parquet"))
    base_col = pipeline.load_parquet(os.path.join(bdir, "collected.parquet"))
    base_by_qid = {r["query_id"]: r for r in base_exec}
    cal = calibrate.load_calibration(args.baseline_key_id)
    assert cal, f"нет калибровки для {args.baseline_key_id}"

    run_dir = pipeline.new_run_dir(args.label)
    work = pipeline.make_work_copy(args.config, run_dir)
    key = pipeline.baseline_key(args.config)
    assert pipeline.key_id(key) == args.baseline_key_id, \
        "ключ среды изменился (сборка/БД/конфиг/индексы) — нужен новый эталон"

    # --- этап 1: компиляция
    t0 = time.perf_counter()
    collected = []
    for suite in CORPUS:
        collected += collect_suite(work, suite)
    compile_s = time.perf_counter() - t0
    print(f"stage 1 compile: {compile_s:.1f}s for {len(collected)} queries")

    cand_by_qid = {r["query_id"]: r for r in collected}
    if args.mutate_plans:
        # симуляция кандидата с другим оптимизатором
        mutated = 0
        for r in collected:
            b = base_by_qid.get(r["query_id"], {})
            ms = cal["entries"].get(r["query_id"], {}).get("baseline_ms", 1e9)
            if b.get("detailed_plan_hash") and ms < 200 and mutated < 10:
                r["detailed_plan_hash"] = "mut_" + str(r["detailed_plan_hash"])
                mutated += 1
        print(f"simulation: mutated plan hashes for {mutated} fast queries")

    changed_fast = [r["query_id"] for r in collected
                    if r["detailed_plan_hash"] and
                    r["detailed_plan_hash"] != base_by_qid.get(
                        r["query_id"], {}).get("detailed_plan_hash") and
                    cal["entries"].get(r["query_id"], {}).get("tier") == "fast"]
    changed_heavy = [r["query_id"] for r in collected
                     if r["detailed_plan_hash"] and
                     r["detailed_plan_hash"] != base_by_qid.get(
                         r["query_id"], {}).get("detailed_plan_hash") and
                     cal["entries"].get(r["query_id"], {}).get("tier") == "heavy"]
    print(f"stage 2a: changed plans: fast={len(changed_fast)}, "
          f"heavy={len(changed_heavy)} (heavy -> INCOMPLETE по 8.1)")

    # --- этап 2a: исполнение изменившихся fast-запросов
    t0 = time.perf_counter()
    exec_changed = []
    if changed_fast:
        exec_changed = run_suite(
            work, "stats-ceb", only_ids=changed_fast,
            per_query_timeout_s=60)
    stage2a_s = time.perf_counter() - t0

    # --- этап 2b: контрольный набор (поганжетно; подпланы только компилируются)
    control = cal["control_set"]
    t0 = time.perf_counter()
    exec_control = []
    for suite in calibrate.CONTROL_SUITES:
        ids = [q for q in control if
               q in set(f[:-4] for f in os.listdir(
                   os.path.join(ROOT, "bench", "queries", suite))
                   if f.endswith(".sql"))]
        if ids:
            exec_control += run_suite(work, suite, only_ids=ids,
                                      per_query_timeout_s=120)
    stage2b_s = time.perf_counter() - t0
    print(f"stage 2a: {len(exec_changed)} queries in {stage2a_s:.1f}s; "
          f"stage 2b: {len(exec_control)} queries in {stage2b_s:.1f}s")

    executed = flatten_exec(exec_changed + exec_control, cand_by_qid)

    # --- валидация строк против истины (корректность)
    mismatch = 0
    for suite in ("stats-ceb", "stats-ceb-single", "stats-ceb-subplans"):
        truth = load_truth(suite)
        for r in exec_changed + exec_control:
            if r["suite"] != suite:
                continue
            v = r.get("result_value")
            if v is not None and r["query_id"] in truth and \
                    truth[r["query_id"]] is not None and \
                    v != truth[r["query_id"]]:
                mismatch += 1
                r["checksum"] = "WRONG"

    # --- этап 4: гейт
    base_subset = [base_by_qid[q] for q in
                   {r["query_id"] for r in exec_changed + exec_control}
                   if q in base_by_qid]
    per_query, gate = compare_run(base_subset, executed, load_accepted())

    rat = check_ratchets(executed)
    # дешёвая часть храповика по ВСЕМУ корпусу (8.1): plan_required /
    # plan_forbidden проверяются по хешам планов из этапа 1, без исполнения;
    # запросы, попавшие в исполнение, уже проверены выше — не дублируем
    executed_ids = {r["query_id"] for r in executed}
    plan_ratchets = [r for r in load_ratchets()
                     if r["query_id"] not in executed_ids and
                     ("plan_required" in str(r.get("kind", "")) or
                      "plan_forbidden" in str(r.get("kind", "")))]
    plan_checked, plan_viol = 0, []
    for r in collected:
        for rat_t in plan_ratchets:
            if rat_t["query_id"] != r["query_id"]:
                continue
            if not r.get("detailed_plan_hash"):
                continue
            plan_checked += 1
            if "plan_required" in rat_t["kind"] and \
                    r["detailed_plan_hash"] != rat_t["plan_hash"]:
                plan_viol.append((rat_t["id"], "ожидаемый план не выбран"))
            if "plan_forbidden" in rat_t["kind"] and \
                    r["detailed_plan_hash"] == rat_t["plan_hash"]:
                plan_viol.append((rat_t["id"], "воспроизвёлся запрещённый план"))
    rat["plan_checked_corpus"] = plan_checked
    rat["violations"].extend({"ratchet": i, "reason": rr}
                             for i, rr in plan_viol)
    if rat["violations"]:
        gate["status"] = "FAIL"
        gate["fail"].extend({"query_id": f"ratchet:{v['ratchet']}",
                             "reason": v["reason"]} for v in rat["violations"])
    for qid in changed_heavy:
        gate["incomplete"].append({"query_id": qid,
                                   "reason": "heavy-запрос с изменившимся "
                                             "планом не исполнен в быстром "
                                             "контуре"})

    # --- сохранение и отчёт
    pipeline.save_parquet(collected, os.path.join(run_dir, "collected.parquet"))
    pipeline.save_parquet(executed, os.path.join(run_dir, "executed.parquet"))
    meta = {"kind": "fast_contour", "key_id": args.baseline_key_id,
            "baseline_key": key, "compile_budget_s": round(compile_s, 1),
            "stage2a_s": round(stage2a_s, 1), "stage2b_s": round(stage2b_s, 1),
            "changed_fast": changed_fast, "changed_heavy": changed_heavy,
            "control_set": control, "ratchet": rat,
            "gate_status": gate["status"], "total_s":
                round(compile_s + stage2a_s + stage2b_s, 1)}
    with open(os.path.join(run_dir, "run_meta.json"), "w",
              encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    md = report.render_report(meta, gate, cal, phase0_notes=[
        "Этап 3 (живое A/B) в фазе 0 не выполняется: подозрительные FAIL "
        "требуют подтверждения на выделенной машине (8.1)."])
    with open(os.path.join(run_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write(md)
    report.write_status_json(gate, os.path.join(run_dir, "ci_status.json"))
    print(f"\nGATE: {gate['status']}  (run dir: {run_dir})")
    for fi in gate["fail"]:
        print(f"  FAIL {fi['query_id']}: {fi['reason']}")
    for wi in gate["warn"]:
        print(f"  WARN {wi['query_id']}: {wi['reason']}")
    print(f"  INCOMPLETE: {len(gate['incomplete'])} items")
    # коды выхода для CI-гейта (принцип 7)
    sys.exit({"PASS": 0, "WARN": 0, "INCOMPLETE": 1, "FAIL": 2}[gate["status"]])


if __name__ == "__main__":
    main()
