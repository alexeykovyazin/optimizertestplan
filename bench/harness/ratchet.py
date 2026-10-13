"""Храповик (принцип 5, раздел 8.1): каждая найденная регрессия становится
постоянным тестом. Проверка дешёвая: по плану (ожидаемый или запрещённый
план) и по счётчикам (верхняя граница). Исполнение по времени — только для
храповика с эталонным временем < 1 с.

Формат теста (bench/regressions/<id>.json):
{
  "id": "rat_001",
  "query_id": "stats_ceb_001",
  "suite": "stats-ceb",
  "kind": "plan_forbidden | plan_required | counters_max",
  "plan_hash": "sha1:...",        # для plan_*: detailed_plan_hash
  "max_fetches": 12345,           # для counters_max
  "max_record_reads": 6789,
  "added": "2026-10-07",
  "reason": "описание найденной регрессии"
}
"""
from __future__ import annotations

import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REG_DIR = os.path.join(ROOT, "bench", "regressions")


def load_ratchets() -> list[dict]:
    out = []
    if os.path.isdir(REG_DIR):
        for f in sorted(os.listdir(REG_DIR)):
            if f.endswith(".json"):
                with open(os.path.join(REG_DIR, f), encoding="utf-8") as fh:
                    out.append(json.load(fh))
    return out


def check_ratchets(run_rows: list[dict]) -> dict:
    """Прогнать храповик по строкам прогона (планы + счётчики, без времени)."""
    by_qid = {r["query_id"]: r for r in run_rows}
    violations, checked = [], 0
    for rat in load_ratchets():
        r = by_qid.get(rat["query_id"])
        if r is None:
            continue
        checked += 1
        if r.get("error") or r.get("timed_out"):
            violations.append((rat["id"], "запрос не исполнился"))
            continue
        for kind in str(rat.get("kind", "")).split("+"):
            if kind == "plan_forbidden" and \
               r.get("detailed_plan_hash") == rat.get("plan_hash"):
                violations.append((rat["id"], "воспроизвёлся запрещённый план"))
            elif kind == "plan_required" and \
                    r.get("detailed_plan_hash") != rat.get("plan_hash"):
                violations.append((rat["id"], "ожидаемый план не выбран"))
            elif kind == "counters_max":
                f, rr = r.get("fetches"), r.get("record_reads")
                if rat.get("max_fetches") and f and f > rat["max_fetches"]:
                    violations.append((rat["id"],
                                       f"fetches {f} > {rat['max_fetches']}"))
                if rat.get("max_record_reads") and rr and \
                        rr > rat["max_record_reads"]:
                    violations.append((rat["id"],
                                       f"record_reads {rr} > "
                                       f"{rat['max_record_reads']}"))
    return {"checked": checked, "violations": [{"ratchet": i, "reason": r}
                                               for i, r in violations]}
