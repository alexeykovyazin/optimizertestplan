"""Финальный отчёт фазы 0: сводка по замерам, гейту A/A, ограничениям среды.

Запуск: python bench/harness/phase0_report.py <baseline_run_dir> [<aa_run_dir>]
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
import pipeline  # noqa: E402
import report  # noqa: E402


def main():
    run_dir = sys.argv[1]
    aa_dir = sys.argv[2] if len(sys.argv) > 2 else None
    meta = json.load(open(os.path.join(run_dir, "run_meta.json"),
                          encoding="utf-8"))
    aa = None
    if aa_dir:
        p = os.path.join(aa_dir, "aa_noise.json")
        if os.path.exists(p):
            aa = json.load(open(p, encoding="utf-8"))

    cal = None
    import calibrate
    cal = calibrate.load_calibration(meta["key_id"])

    notes = [
        "Базовый инстанс — Firebird 5.0.5.1879 HQbird (localhost:3055). "
        "RDB$SQL.EXPLAIN с CARDINALITY — только FB 6: оценки по узлам, q-error, "
        "CERT и P-Error на этом инстансе недоступны (план раздела 13 это "
        "предусматривает).",
        "SET OPTIMIZE через DSQL движком не принимается (команда isql). В конфиге "
        "инстанса OptimizeForFirstRows=true — НЕ дефолт Firebird. Конфигурация "
        "зафиксирована снапшотом firebird.conf/databases.conf в bench/config и "
        "входит в хеш ключа эталона; при переносе на выделенный инстанс эталон "
        "снимается заново (4.2).",
        "Профайлер (PLG$PROF*) на инстансе отключён (Profiler не задан в "
        "firebird.conf, менять конфиг общего инстанса нельзя). Проверка "
        "RECORD_SOURCE_ID EXPLAIN↔профайлер (4.7) отложена до инстанса с "
        "включённым профайлером; подтверждено, что detailed_plan драйвера "
        "совпадает с выводом isql SET EXPLAIN — источник дерева для будущей "
        "сверки един.",
        "JOB/IMDb (порт по плану уже был в другом репозитории) в этой рабочей "
        "копии отсутствует: IMDb-дамп требует PostgreSQL-нагрузки; корпус фазы 0 "
        "здесь — STATS-CEB (P1, грузится из CSV). Это помечается как INCOMPLETE "
        "в объёме фазы 0 (принцип 7 — нет ложного PASS).",
        "Истина подпланов считается с бюджетом на запрос (10 с в этой фазе, DuckDB); "
        "непокрытые подпланы — кандидат в ночное досчитывание (4.6).",
    ]

    md = report.render_report(meta, gate=None, calibration=cal, aa_noise=aa,
                              phase0_notes=notes)
    out_md = os.path.join(run_dir, "phase0_report.md")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(md)
    report.write_status_json({"status": meta.get("gate_status", "UNKNOWN"),
                              "kind": "phase0", "run_dir": run_dir,
                              "key_id": meta.get("key_id")},
                             os.path.join(run_dir, "ci_status.json"))
    print(md)
    print("\nwritten:", out_md)


if __name__ == "__main__":
    main()
