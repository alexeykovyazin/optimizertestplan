"""Человекочитаемый список JOB-запросов и их планов:
SQL + базовый план (HQbird 5.0.5) + corr-план (v5.0-impr-opt, rows=).

Запуск: python bench/harness/job_plans_md.py [--all-stats]
Выход:  results/dedicated_dellg15/impropt_matrix/PLANS.md
        (полный JOB 113 + изменившие план stats-ceb; --all-stats добавляет
        весь контроль stats-ceb/stats-ceb-single)
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
import pandas as pd  # noqa: E402

QDIR = os.path.join(ROOT, "bench", "queries")
REPORT = os.path.join(ROOT, "results", "dedicated_dellg15", "impropt_matrix",
                      "impropt_report.json")
OUT = os.path.join(ROOT, "results", "dedicated_dellg15", "impropt_matrix",
                   "PLANS.md")
BASE_COLLECTED = os.path.join(ROOT, "results", "dedicated_dellg15",
                              "optimize_matrix", "first_rows",
                              "collected.parquet")
CORR_COLLECTED = os.path.join(ROOT, "results", "dedicated_dellg15",
                              "impropt_matrix", "corr", "collected.parquet")


def natkey(qid):
    m = re.match(r"(\d+)([a-z]*)", qid)
    return (int(m.group(1)) if m else 10**9, m.group(2) if m else qid)


def load(path):
    df = pd.read_parquet(path)
    out = {}
    for r in df.itertuples():
        out.setdefault(r.suite, {})[r.query_id] = r
    return out


def section(title, sql, base, corr, f):
    f.write(f"### {title}\n\n```sql\n{sql.strip()}\n```\n\n")
    for name, rec, col in (("Базовый план (HQbird 5.0.5, first_rows)", base,
                            "plan"),
                           ("corr (v5.0-impr-opt, PredicateCorrelation, rows=)",
                            corr, "detailed_plan")):
        f.write(f"**{name}:**\n```\n"
                f"{(getattr(rec, col) if rec is not None else '— нет —')}\n"
                f"```\n\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all-stats", action="store_true",
                    help="включить весь stats-контроль, а не только сменившие план")
    a = ap.parse_args()

    base = load(BASE_COLLECTED)
    corr = load(CORR_COLLECTED)
    changed = set(json.load(open(REPORT, encoding="utf-8"))
                  ["corr"]["changed_ids"])

    job_changed = sorted(q for q in changed if not q.startswith("stats"))
    stats_changed = sorted(q for q in changed if q.startswith("stats"))

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("# JOB: запросы и планы (HQbird 5.0.5 vs v5.0-impr-opt corr)\n\n")
        f.write("- Базовый план — простой PLAN, corr — EXPLAIN-план с "
                "оценками кардинальности (ShowExplainCardinality=true, "
                "rows=).\n")
        f.write(f"- Сменили план: {len(job_changed)} JOB + "
                f"{len(stats_changed)} stats-ceb (помечены ⚠).\n\n")
        f.write("## Сменившие план (JOB)\n\n")
        f.write(", ".join(job_changed) + "\n\n")
        for qid in job_changed:
            sql = open(os.path.join(QDIR, "job", qid + ".sql"),
                       encoding="utf-8").read()
            section(f"{qid} ⚠ СМЕНА ПЛАНА", sql,
                    base.get("job", {}).get(qid),
                    corr.get("job", {}).get(qid), f)
        f.write("## Сменившие план (stats-ceb)\n\n")
        for qid in stats_changed:
            sql = open(os.path.join(QDIR, "stats-ceb", qid + ".sql"),
                       encoding="utf-8").read()
            section(qid + " ⚠ СМЕНА ПЛАНА", sql,
                    base.get("stats-ceb", {}).get(qid),
                    corr.get("stats-ceb", {}).get(qid), f)
        f.write("## Все JOB-запросы (план совпадает с базой, если нет ⚠)\n\n")
        for qid in sorted(base["job"], key=natkey):
            mark = " ⚠" if qid in changed else ""
            sql = open(os.path.join(QDIR, "job", qid + ".sql"),
                       encoding="utf-8").read()
            section(qid + mark, sql, base["job"][qid], corr["job"][qid], f)
        if a.all_stats:
            for suite in ("stats-ceb", "stats-ceb-single"):
                f.write(f"## Все {suite}\n\n")
                for qid in sorted(base.get(suite, {}), key=natkey):
                    mark = " ⚠" if qid in changed else ""
                    p = os.path.join(QDIR, suite, qid + ".sql")
                    sql = open(p, encoding="utf-8").read()
                    section(qid + mark, sql, base[suite][qid],
                            corr.get(suite, {}).get(qid), f)
    n = sum(1 for _ in open(OUT, encoding="utf-8"))
    print(f"written {OUT} ({n} lines)")


if __name__ == "__main__":
    main()
