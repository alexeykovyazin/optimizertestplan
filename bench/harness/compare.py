"""compare: сравнение кандидата с эталоном + гейт (разделы 5, 6, 9 плана).

r = значение кандидата / значение эталона; r < 1 — улучшение.
Классы: improved, regressed, neutral, plan_changed_no_effect, new_timeout,
wrong_result, error, not_executed.
Статусы гейта: PASS / WARN / FAIL / INCOMPLETE. Нет ложного PASS (принцип 7).
"""
from __future__ import annotations

import json
import math
import os


def _num(v):
    return v if isinstance(v, (int, float)) else None


def compare_run(baseline_rows: list[dict], candidate_rows: list[dict],
                accepted: dict | None = None,
                counters_gate: float = 1.05,
                plan_changed_counters_warn: float = 1.2,
                time_gate_r: float = 1.5, time_gate_abs_ms: float = 100.0,
                prepare_gate_r: float = 2.0, prepare_gate_abs_ms: float = 50.0):
    """Вернуть (per_query, summary, gate). accepted: {query_id: {"max_r": x, ...}}."""
    accepted = accepted or {}
    base = {r["query_id"]: r for r in baseline_rows}
    cand = {r["query_id"]: r for r in candidate_rows}
    per_query = []
    fail, warn, incomplete = [], [], []
    ratios = []          # r по времени изменённых планов
    timeouts_new, wrong, errors, not_executed = [], [], [], []

    for qid, c in cand.items():
        b = base.get(qid)
        row = {"query_id": qid, "cls": None, "r_time": None,
               "r_fetches": None, "r_record_reads": None,
               "plan_changed": None, "notes": []}
        if b is None:
            row["cls"] = "new"
            incomplete.append((qid, "нет в эталоне"))
            per_query.append(row)
            continue
        if c.get("error"):
            row["cls"] = "error"
            errors.append(qid)
            fail.append((qid, f"error: {c['error'][:120]}"))
            per_query.append(row)
            continue
        if c.get("timed_out") and not b.get("timed_out"):
            row["cls"] = "new_timeout"
            timeouts_new.append(qid)
            fail.append((qid, "новый таймаут"))
            per_query.append(row)
            continue
        if c.get("timed_out") and b.get("timed_out"):
            row["cls"] = "not_executed"
            not_executed.append(qid)
            per_query.append(row)
            continue
        # корректность результата
        if c.get("checksum") != b.get("checksum"):
            row["cls"] = "wrong_result"
            wrong.append(qid)
            fail.append((qid, "checksum/число строк отличается"))
            per_query.append(row)
            continue
        # план
        plan_changed = c.get("detailed_plan_hash") != b.get("detailed_plan_hash")
        row["plan_changed"] = plan_changed
        # счётчики
        bf = _num(b.get("fetches")); cf = _num(c.get("fetches"))
        br = _num(b.get("record_reads")); cr = _num(c.get("record_reads"))
        r_fetch = (cf / bf) if bf else None
        r_reads = (cr / br) if br else None
        row["r_fetches"] = round(r_fetch, 4) if r_fetch else None
        row["r_record_reads"] = round(r_reads, 4) if r_reads else None
        rt = None
        if not plan_changed:
            # гейт для неизменённых планов: счётчики
            if (r_fetch and r_fetch > counters_gate) or \
               (r_reads and r_reads > counters_gate):
                row["cls"] = "regressed_counters_same_plan"
                fail.append((qid, f"план не изменился, счётчики выросли "
                                  f"(fetch r={r_fetch}, reads r={r_reads})"))
            else:
                row["cls"] = "neutral"
            if c.get("prepare_ms") and b.get("prepare_ms"):
                rp = c["prepare_ms"] / b["prepare_ms"]
                if rp > prepare_gate_r and \
                   (c["prepare_ms"] - b["prepare_ms"]) > prepare_gate_abs_ms:
                    fail.append((qid, f"prepare r={rp:.2f} "
                                      f"({b['prepare_ms']:.1f}->{c['prepare_ms']:.1f} мс)"))
        else:
            # изменённый план: время — решение, счётчики — сигнал
            bm = _num(b.get("median_ms")); cm = _num(c.get("median_ms"))
            if bm and cm:
                rt = cm / bm
                row["r_time"] = round(rt, 4)
                ratios.append(rt)
            acc = accepted.get(qid)
            if rt and rt > time_gate_r and (cm - bm) > time_gate_abs_ms:
                if acc and rt <= acc.get("max_r", math.inf):
                    row["cls"] = "accepted_regression"
                    row["notes"].append(f"accepted до {acc.get('expires')}, "
                                        f"обоснование: {acc.get('reason')}")
                else:
                    row["cls"] = "regressed"
                    fail.append((qid, f"время r={rt:.2f} "
                                      f"({bm:.1f}->{cm:.1f} мс), подтверждение A/B"))
            elif (r_fetch and r_fetch > plan_changed_counters_warn) or \
                 (r_reads and r_reads > plan_changed_counters_warn):
                row["cls"] = "plan_changed_no_effect" if rt and rt <= 1.05 \
                    else "improved"
                warn.append((qid, f"счётчики r> {plan_changed_counters_warn} при "
                                  f"изменённом плане (сигнал)"))
            elif rt and rt < 0.95:
                row["cls"] = "improved"
            else:
                row["cls"] = "plan_changed_no_effect"
        per_query.append(row)

    for qid in sorted(set(base) - set(cand)):
        incomplete.append((qid, "нет в прогоне кандидата"))

    geomean = math.exp(sum(math.log(r) for r in ratios) / len(ratios)) \
        if ratios else None
    if geomean and geomean > 1.0 and not fail:
        warn.append(("__geomean__", f"геометрическое среднее r по изменённым "
                                    f"запросам = {geomean:.4f} > 1.0"))

    if fail:
        status = "FAIL"
    elif incomplete:
        status = "INCOMPLETE"
    elif warn:
        status = "WARN"
    else:
        status = "PASS"

    gate = {
        "status": status,
        "fail": [{"query_id": q, "reason": r} for q, r in fail],
        "warn": [{"query_id": q, "reason": r} for q, r in warn],
        "incomplete": [{"query_id": q, "reason": r} for q, r in incomplete],
        "geomean_r_changed": geomean,
        "counts": {
            "wrong_result": len(wrong), "new_timeout": len(timeouts_new),
            "error": len(errors), "not_executed": len(not_executed),
            "plan_changed": sum(1 for r in per_query if r["plan_changed"]),
        },
    }
    return per_query, gate


def load_accepted() -> dict:
    """accepted/*.json -> {query_id: {...}}"""
    root = os.path.join(os.path.dirname(__file__), "..", "accepted")
    out = {}
    if os.path.isdir(root):
        for f in os.listdir(root):
            if f.endswith(".json"):
                with open(os.path.join(root, f), encoding="utf-8") as fh:
                    data = json.load(fh)
                for entry in (data if isinstance(data, list) else [data]):
                    out[entry["query_id"]] = entry
    return out
