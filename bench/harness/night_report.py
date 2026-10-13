"""Сводный ночной отчёт: состояние эталонов, тяжёлых, истины, конфигураций.

Запуск: python bench/harness/night_report.py > results/NIGHT_REPORT.md
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
import pipeline  # noqa: E402
import calibrate  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402


def main():
    L = ["# Ночной отчёт (контур фазы 2, исполняемая часть)", ""]

    # эталоны
    L.append("## Эталоны (results/baselines)")
    L.append("")
    L.append("| key_id | config | замеров | таймауты | файл БД (sha256[:12]) |")
    L.append("|---|---|---|---|---|")
    bdir_root = os.path.join(pipeline.RESULTS_DIR, "baselines")
    for kid in sorted(os.listdir(bdir_root)):
        meta_p = os.path.join(bdir_root, kid, "run_meta.json")
        if not os.path.exists(meta_p):
            continue
        meta = json.load(open(meta_p, encoding="utf-8"))
        key = meta["baseline_key"]
        rows = pq.read_table(os.path.join(bdir_root, kid,
                                          "executed.parquet")).to_pylist()
        to = sum(1 for r in rows if r.get("timed_out"))
        L.append(f"| `{kid}` | {key['index_config']} | {len(rows)} | {to} | "
                 f"`{key['db_sha256'][:12]}` |")
    L.append("")

    # истина
    L.append("## Истина (DuckDB)")
    L.append("")
    tdir = os.path.join(ROOT, "bench", "truth", "stats-ceb")
    for f in sorted(os.listdir(tdir)):
        if not f.endswith(".parquet"):
            continue
        rows = pq.read_table(os.path.join(tdir, f)).to_pylist()
        missing = sum(1 for r in rows if r["true_rows"] is None)
        L.append(f"- {f}: {len(rows)} строк, без истины: {missing}")
    L.append("")

    # калибровки
    L.append("## Калибровки")
    L.append("")
    cdir = os.path.join(pipeline.RESULTS_DIR, "calibration")
    for f in sorted(os.listdir(cdir)):
        if not f.endswith(".yaml"):
            continue
        cal = calibrate.load_calibration(f[:-5])
        if cal:
            n_fast = sum(1 for e in cal["entries"].values()
                         if e["tier"] == "fast")
            L.append(f"- `{f[:-5]}`: fast={n_fast}, heavy="
                     f"{len(cal['entries']) - n_fast}, контрольный набор="
                     f"{len(cal['control_set'])} (~"
                     f"{cal['control_est_ms'] / 1000:.0f} c один проход)")
    L.append("")

    # ограничение среды
    L.append("## Напоминание")
    L.append("")
    L.append("Время на общем инстансе 3055 дрейфует (A/A: ×0,44 между "
             "прогонами) — гейт по времени только через живое A/B на "
             "выделенной машине. Счётчики детерминированы (макс 1,0002).")
    print("\n".join(L))


if __name__ == "__main__":
    main()
