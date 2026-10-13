"""calibrate: разметка fast/heavy и отбор контрольного набора (раздел 8.1).

Динамические данные (baseline_ms, tier, контрольный набор) хранятся в
results/calibration/<key_id>.yaml, а не в манифестах (4.3).

Отбор контрольного набора:
  1. только fast-запросы;
  2. жадно добавляем самые дешёвые, пока каждый тег и каждое семейство
     шаблонов не покрыты минимум 2 запросами;
  3. добираем до бюджета запросами с исторически чаще всего менявшимся
     планом (в фазе 0 истории нет — добираем самыми дешёвыми).
"""
from __future__ import annotations

import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CALIB_DIR = os.path.join(ROOT, "results", "calibration")

HEAVY_THRESHOLD_MS = float(os.environ.get("BENCH_HEAVY_MS", "1000"))
# Бюджет контрольного набора — сумма baseline_ms одного прохода на набор;
# с прогревом и 3 замерами это даёт ~4x стены (8.1: этап 2b ~6 мин).
CONTROL_BUDGET_MS = float(os.environ.get("BENCH_CONTROL_BUDGET_MS", "90000"))
# Наборы контрольного набора; подпланы в быстром контуре только
# компилируются (8.1), поэтому в контрольный набор не входят.
CONTROL_SUITES = ("stats-ceb", "stats-ceb-single")


def load_manifest(suite: str) -> dict[str, dict]:
    import yaml
    path = os.path.join(ROOT, "bench", "manifest", f"{suite}.yaml")
    return {e["id"]: e for e in yaml.safe_load(open(path, encoding="utf-8"))}


def calibrate(baseline_exec_rows: list[dict], suites=("stats-ceb",),
              heavy_ms: float = HEAVY_THRESHOLD_MS,
              control_budget_ms: float = CONTROL_BUDGET_MS) -> dict:
    manifest = {}
    for s in suites:
        manifest.update(load_manifest(s))
    entries, control = {}, []
    rows = [r for r in baseline_exec_rows if r.get("median_ms") is not None
            and not r.get("timed_out") and not r.get("error")]
    for r in rows:
        m = manifest.get(r["query_id"], {})
        # семейство шаблонов (8.1) — coarse-группа: множество таблиц
        # (для одно-табличного набора — template_id из файла CEB)
        family = m.get("template") or "+".join(sorted(m.get("table_list") or []))
        entries[r["query_id"]] = {
            "baseline_ms": round(r["median_ms"], 3),
            "tier": "heavy" if r["median_ms"] > heavy_ms else "fast",
            "tags": m.get("tags", []),
            "template": m.get("template"),
            "family": family,
        }
    # контрольный набор: поганжетно, бюджет на каждый набор (8.1)
    tag_cov, tpl_cov = {}, {}
    for suite in CONTROL_SUITES:
        suite_rows = sorted((r for r in rows
                             if r["suite"] == suite and
                             entries[r["query_id"]]["tier"] == "fast"),
                            key=lambda r: r["median_ms"])
        budget_left = control_budget_ms
        chosen = set()
        # проход 1: покрытие тегов и семейств шаблонов >= 2, жадно дешёвые
        for r in suite_rows:
            qid = r["query_id"]
            e = entries[qid]
            needed = any(tag_cov.get(t, 0) < 2 for t in e["tags"]) or \
                tpl_cov.get(e["family"], 0) < 2
            if not needed:
                continue
            chosen.add(qid)
            budget_left -= e["baseline_ms"]
            for t in e["tags"]:
                tag_cov[t] = tag_cov.get(t, 0) + 1
            tpl_cov[e["family"]] = tpl_cov.get(e["family"], 0) + 1
        # проход 2: добор до бюджета дешёвыми (в фазе 0 истории изменения
        # планов нет; при её появлении сортировать по ней — 8.1 п.3)
        for r in suite_rows:
            qid = r["query_id"]
            if qid in chosen or budget_left <= 0:
                continue
            chosen.add(qid)
            budget_left -= entries[qid]["baseline_ms"]
        control.extend(sorted(chosen))
    return {
        "heavy_threshold_ms": heavy_ms,
        "control_budget_ms": control_budget_ms,
        "entries": entries,
        "control_set": control,
        "control_est_ms": round(sum(entries[q]["baseline_ms"] for q in control), 1),
        "tag_coverage": tag_cov,
    }


def save_calibration(cal: dict, key_id_str: str) -> str:
    import yaml
    os.makedirs(CALIB_DIR, exist_ok=True)
    path = os.path.join(CALIB_DIR, f"{key_id_str}.yaml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cal, f, allow_unicode=True, sort_keys=False)
    return path


def load_calibration(key_id_str: str) -> dict | None:
    import yaml
    path = os.path.join(CALIB_DIR, f"{key_id_str}.yaml")
    if os.path.exists(path):
        return yaml.safe_load(open(path, encoding="utf-8"))
    return None
