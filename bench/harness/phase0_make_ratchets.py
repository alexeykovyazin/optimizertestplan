"""Bootstrap храповика: по эталонному прогону создаёт начальные тесты.

Для каждого fast-запроса контрольного набора фиксируется:
  - plan_required: текущий нормализованный план (detailed_plan_hash);
  - counters_max: верхняя граница счётчиков (fetches, record_reads) с запасом
    (baseline x A/A-шум p99 x 1.05, минимум +1).

Запуск: python bench/harness/phase0_make_ratchets.py <baseline_run_dir> <aa_noise.json>
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
import pipeline  # noqa: E402
import calibrate  # noqa: E402


def main():
    run_dir = sys.argv[1]
    aa_path = sys.argv[2] if len(sys.argv) > 2 else None
    noise_p99 = 1.02
    if aa_path and os.path.exists(aa_path):
        aa = json.load(open(aa_path, encoding="utf-8"))
        noise_p99 = max(aa.get("fetches_ratio", {}).get("p99", 1.02),
                        aa.get("record_reads_ratio", {}).get("p99", 1.02))
    meta = json.load(open(os.path.join(run_dir, "run_meta.json"),
                          encoding="utf-8"))
    cal = calibrate.load_calibration(meta["key_id"])
    rows = {r["query_id"]: r for r in
            pipeline.load_parquet(os.path.join(run_dir, "executed.parquet"))}
    collected = {r["query_id"]: r for r in
                 pipeline.load_parquet(os.path.join(run_dir, "collected.parquet"))}

    made = []
    for qid in cal["control_set"]:
        r, c = rows.get(qid), collected.get(qid)
        if not r or not c or r.get("error") or r.get("timed_out") or \
                not c.get("detailed_plan_hash"):
            continue
        if (r.get("median_ms") or 0) > 1000:
            continue  # исполнение по времени/счётчикам — только < 1 c (8.1)
        entry = {
            "id": f"rat_{qid}",
            "query_id": qid,
            "suite": r["suite"],
            "kind": "plan_required+counters_max",
            "plan_hash": c["detailed_plan_hash"],
            "max_fetches": max(1, int(r["fetches"] * noise_p99 * 1.05) + 1),
            "max_record_reads": max(1, int(r["record_reads"] * noise_p99 * 1.05) + 1),
            "added": "2026-10-08",
            "reason": "bootstrap: эталонный план и границы счётщиков "
                      "контрольного набора фазы 0",
        }
        path = os.path.join(ROOT, "bench", "regressions", f"{entry['id']}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2, ensure_ascii=False)
        made.append(qid)
    print(f"ratchets created: {len(made)} -> {made}")


if __name__ == "__main__":
    main()
