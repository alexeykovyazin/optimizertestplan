"""report: Markdown/HTML-отчёт + машиночитаемый статус для CI (раздел 5)."""
from __future__ import annotations

import json
import os


def render_report(run_meta: dict, gate: dict | None, calibration: dict | None,
                  aa_noise: dict | None = None,
                  phase0_notes: list[str] | None = None) -> str:
    L = []
    L.append(f"# Отчёт прогона: {run_meta.get('kind', 'run')} "
             f"`{run_meta.get('key_id', '?')}`")
    L.append("")
    key = run_meta.get("baseline_key", {})
    L.append("**Ключ эталона (4.2):**")
    L.append("")
    L.append("| Поле | Значение |")
    L.append("|---|---|")
    for k in ("build_id", "db_sha256", "ods", "config_hash", "index_config"):
        L.append(f"| {k} | `{key.get(k)}` |")
    L.append("")
    L.append(f"- Сервер: {run_meta.get('server', 'FB 5.0.5 HQbird @ localhost:3055')}")
    if "compile_budget_s" in run_meta:
        L.append(f"- Бюджет компиляции корпуса: **{run_meta['compile_budget_s']} с** "
                 f"({run_meta.get('queries_collected', '?')} запросов, prepare+план)")
    if "exec_budget_s" in run_meta:
        L.append(f"- Исполнение: {run_meta.get('queries_executed', '?')} запросов "
                 f"за {run_meta['exec_budget_s']} с")
    if "truth_checked" in run_meta:
        L.append(f"- Валидация истины: проверено {run_meta['truth_checked']}, "
                 f"расхождений {run_meta['truth_mismatches']}")
    L.append("")

    if calibration:
        fast = sum(1 for e in calibration["entries"].values()
                   if e["tier"] == "fast")
        L.append("## Калибровка (8.1)")
        L.append("")
        L.append(f"- Порог fast/heavy: {calibration['heavy_threshold_ms']} мс; "
                 f"fast = {fast}, heavy = "
                 f"{len(calibration['entries']) - fast}")
        L.append(f"- Контрольный набор: **{len(calibration['control_set'])}** "
                 f"запросов, оценка суммы {calibration['control_est_ms']} мс")
        tags_json = json.dumps(calibration["tag_coverage"],
                               ensure_ascii=False, sort_keys=True)
        L.append(f"- Покрытие тегов: {tags_json}")
        L.append("")

    if aa_noise:
        L.append("## A/A-шум (раздел 10)")
        L.append("")
        L.append("| Метрика | p50 | p90 | p99 | max | n |")
        L.append("|---|---|---|---|---|---|")
        for name, d in aa_noise.items():
            if not isinstance(d, dict) or "p50" not in d:
                continue
            L.append(f"| {name} | {d['p50']:.4f} | {d['p90']:.4f} | "
                     f"{d['p99']:.4f} | {d['max']:.4f} | {d.get('n', '')} |")
        for k in ("result_disagreements", "pairs_compared"):
            if k in aa_noise:
                L.append(f"- {k}: {aa_noise[k]}")
        L.append("")

    if gate:
        L.append("## Гейт (раздел 9)")
        L.append("")
        L.append(f"**Статус: `{gate['status']}`**")
        L.append("")
        if gate.get("geomean_r_changed") is not None:
            L.append(f"- Геометрическое среднее r по изменённым запросам: "
                     f"**{gate['geomean_r_changed']:.4f}**")
        c = gate.get("counts", {})
        L.append(f"- Изменённых планов: {c.get('plan_changed', 0)}; "
                 f"wrong_result: {c.get('wrong_result', 0)}; "
                 f"new_timeout: {c.get('new_timeout', 0)}; "
                 f"error: {c.get('error', 0)}")
        for sect, title in (("fail", "FAIL"), ("warn", "WARN"),
                            ("incomplete", "INCOMPLETE")):
            items = gate.get(sect) or []
            if items:
                L.append(f"### {title} ({len(items)})")
                L.append("")
                for it in items[:50]:
                    L.append(f"- `{it['query_id']}`: {it['reason']}")
                if len(items) > 50:
                    L.append(f"- ... и ещё {len(items) - 50}")
                L.append("")

    if phase0_notes:
        L.append("## Замечания фазы 0")
        L.append("")
        for n in phase0_notes:
            L.append(f"- {n}")
        L.append("")

    return "\n".join(L)


def write_status_json(gate: dict, path: str):
    """Машиночитаемый статус для CI-гейта."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(gate, f, indent=2, ensure_ascii=False)
