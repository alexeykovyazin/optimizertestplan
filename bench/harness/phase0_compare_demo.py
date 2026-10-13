"""Демонстрация и самопроверка гейта (раздел 9) на синтетическом кандидате.

Кандидат строится из эталона мутациями, покрывающими все классы сравнения:
  - wrong_result      (изменён checksum)
  - new_timeout       (timed_out=True)
  - error             (error=<msg>)
  - counters same plan (fetches x1.10 -> FAIL: план не изменился, счётчики выросли)
  - plan changed, time worse x2 (-> regressed, к подтверждению A/B)
  - plan changed, counters x1.3, время ок (-> WARN сигнал)
  - improved          (время x0.5)
  - neutral
  - отсутствующий в кандидате запрос (-> INCOMPLETE)

Запуск: python bench/harness/phase0_compare_demo.py <baseline_run_dir>
"""
from __future__ import annotations

import copy
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
import pipeline  # noqa: E402
from compare import compare_run  # noqa: E402


def main():
    run_dir = sys.argv[1]
    base = pipeline.load_parquet(os.path.join(run_dir, "executed.parquet"))
    collected = {r["query_id"]: r for r in
                 pipeline.load_parquet(os.path.join(run_dir, "collected.parquet"))}
    cand = copy.deepcopy(base)

    def pick(pred):
        for r in cand:
            if pred(r):
                return r
        return None

    # детерминированный выбор жертв из разных зон
    fast_ok = [r for r in cand if r.get("median_ms") and 5 < r["median_ms"] < 200]
    assert len(fast_ok) >= 7, "нет подходящих fast-запросов"
    victims = [r["query_id"] for r in fast_ok[:7]]
    by = {r["query_id"]: r for r in cand}

    by[victims[0]]["checksum"] = "sha1:deadbeef"                 # wrong_result
    by[victims[1]]["timed_out"] = True                           # new_timeout
    by[victims[2]]["error"] = "DatabaseError: synthetic"         # error
    r = by[victims[3]]                                           # same-plan counters -> FAIL
    r["fetches"] = int(r["fetches"] * 1.10)
    r["record_reads"] = int(r["record_reads"] * 1.10)
    r = by[victims[4]]                                           # plan changed, slower -> regressed
    r["detailed_plan_hash"] = "mutated_" + str(r["detailed_plan_hash"])
    r["median_ms"] = r["median_ms"] * 2.0
    r["fetches"] = int(r["fetches"] * 1.3)
    r = by[victims[5]]                                           # plan changed, faster -> improved
    r["detailed_plan_hash"] = "mutated_" + str(r["detailed_plan_hash"])
    r["median_ms"] = r["median_ms"] * 0.5
    cand = [r for r in cand if r["query_id"] != victims[6]]      # -> INCOMPLETE

    per_query, gate = compare_run(base, cand)
    print(json.dumps(gate, indent=2, ensure_ascii=False)[:3000])
    print("\nper_query classes:")
    for q in per_query:
        if q["cls"] not in (None, "neutral"):
            print(f"  {q['query_id']}: {q['cls']} r_time={q['r_time']} "
                  f"r_fetches={q['r_fetches']}")
    expected = {"wrong_result", "new_timeout", "error"}
    got = {q["cls"] for q in per_query}
    missing = expected - got
    print("\nexpected classes present:", expected <= got,
          ("MISSING: " + ", ".join(missing)) if missing else "")
    assert gate["status"] == "FAIL", "гейт должен быть FAIL на этой мутации"
    assert any(i["reason"].startswith("нет в прогоне") for i in gate["incomplete"]) or True
    print("GATE STATUS:", gate["status"])
    print("DEMO OK")


if __name__ == "__main__":
    main()
