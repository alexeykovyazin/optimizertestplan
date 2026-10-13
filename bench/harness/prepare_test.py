"""S5-гейт порта набора: prepare всех запросов сюиты на Firebird (локально).

Для каждого запроса: fbenv.prepare_with_watchdog (свой сторож на зависания,
своя пара соединений — изоляция) -> status ok/timeout/error + prepare_ms.
Бюджет компиляции корпуса — сумма prepare_ms по портящимся (это же S5-метрика
из плана §3.1.1). Локальный 3055 используется только функционально (время
системно дрейфует — см. память проекта), замер prepare_ms здесь — ориентир.

Запуск:
  python bench/harness/prepare_test.py --fdb E:/.../imdb_fb5.fdb \
      --suites job-light scale synthetic
"""
from __future__ import annotations

import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
import fbenv  # noqa: E402

OUT = os.path.join(ROOT, "results", "prepare_test")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--fdb", required=True)
    ap.add_argument("--suites", nargs="+", required=True)
    ap.add_argument("--prepare-timeout-s", type=float, default=120.0)
    ap.add_argument("--progress-every", type=int, default=250)
    a = ap.parse_args()

    fbenv.ensure_client()
    os.makedirs(OUT, exist_ok=True)
    overall = {}
    for suite in a.suites:
        qdir = os.path.join(ROOT, "bench", "queries", suite)
        ids = sorted(f[:-4] for f in os.listdir(qdir) if f.endswith(".sql"))
        outdir = os.path.join(OUT, suite)
        os.makedirs(outdir, exist_ok=True)
        results = []
        # инкрементально: продолжаем с места прошлого прогона
        done = {}
        rep_path = os.path.join(outdir, "report.json")
        if os.path.exists(rep_path):
            done = {r["query_id"]: r for r in
                    json.load(open(rep_path, encoding="utf-8"))["results"]}
        t0 = time.perf_counter()
        n_err = n_to = 0
        for i, qid in enumerate(ids, 1):
            if qid in done:
                results.append(done[qid])
                continue
            sql = open(os.path.join(qdir, qid + ".sql"), encoding="utf-8").read()
            prep = fbenv.prepare_with_watchdog(a.fdb, sql, a.prepare_timeout_s)
            rec = {"query_id": qid,
                   "status": ("prepare_timeout" if prep["timed_out"] else
                              "error" if prep["error"] else "ok"),
                   "prepare_ms": (round(prep["prepare_ms"], 2)
                                  if prep["prepare_ms"] is not None else None),
                   "error": prep["error"]}
            if rec["status"] == "error":
                n_err += 1
            if rec["status"] == "prepare_timeout":
                n_to += 1
            results.append(rec)
            if i % a.progress_every == 0 or i == len(ids):
                el = time.perf_counter() - t0
                print(f"  [{suite} {i}/{len(ids)}] ok={i - n_err - n_to} "
                      f"err={n_err} to={n_to} ({el:.0f}s)", flush=True)
        cnt = {}
        for r in results:
            cnt[r["status"]] = cnt.get(r["status"], 0) + 1
        total_ms = sum(r["prepare_ms"] or 0 for r in results)
        report = {"suite": suite, "fdb": a.fdb, "total": len(results),
                  "statuses": cnt,
                  "compile_budget_ms": round(total_ms, 1),
                  "results": results}
        with open(rep_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
        overall[suite] = {"total": len(results), "statuses": cnt,
                          "compile_budget_s": round(total_ms / 1000, 1)}
        print(f"{suite}: {cnt} compile={total_ms:.0f}ms")
    print("SUMMARY:", json.dumps(overall))


if __name__ == "__main__":
    main()
