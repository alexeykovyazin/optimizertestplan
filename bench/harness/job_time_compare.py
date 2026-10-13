"""Сводная таблица времени JOB: PostgreSQL (эталон) vs Firebird.

Источники (оба прогона — на dellg15):
  - PG:  results/job_pg_reference/plans_summary.json — Execution Time из
         EXPLAIN ANALYZE FORMAT JSON (серверное время, один прогон, строки
         клиенту не отгружаются); планирование отдельно (planning_ms).
  - FB:  results/dedicated_dellg15/optimize_matrix/<mode>/executed.parquet —
         median_ms по 3 прогонам, замер по часам вокруг execute+fetch
         (строк у JOB-агрегатов мало, накладные расходы пренебрежимы).

Выход: results/job_time_compare/times_pg_vs_fb.csv + REPORT.md.
"""
import argparse
import json
import math
import os

import pandas as pd

BASE = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))


def load_extra(parquet: str, col: str) -> pd.DataFrame:
    """JOB-строки из executed.parquet как колонка col (qid, median_ms)."""
    x = pd.read_parquet(parquet)
    x = x[x.suite == "job"].rename(columns={"query_id": "qid"})
    return x[["qid", "median_ms"]].rename(columns={"median_ms": col})


def load(pg_dir: str, fb_parquet: str) -> pd.DataFrame:
    ps = json.load(open(os.path.join(pg_dir, "plans_summary.json"),
                        encoding="utf-8"))
    pg = pd.DataFrame([
        {"qid": qid, "pg_ms": v["execution_ms"], "pg_planning_ms": v["planning_ms"],
         "pg_top_rows": v["top_actual_rows"]}
        for qid, v in ps.items()])
    fb = pd.read_parquet(fb_parquet)
    fb = fb[fb.suite == "job"].rename(columns={"query_id": "qid"})[
        ["qid", "median_ms", "runs_ms", "rows_count", "fetches", "record_reads",
         "timed_out", "error"]]
    df = pg.merge(fb, on="qid", how="outer")
    df["ratio_fb_pg"] = df["median_ms"] / df["pg_ms"]
    return df.sort_values("ratio_fb_pg", ascending=False).reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pg-dir",
                    default=os.path.join(BASE, "results", "job_pg_reference"))
    ap.add_argument("--fb-parquet",
                    default=os.path.join(BASE, "results", "dedicated_dellg15",
                                         "optimize_matrix", "first_rows",
                                         "executed.parquet"))
    ap.add_argument("--out", default=os.path.join(BASE, "results",
                                                  "job_time_compare"))
    ap.add_argument("--extra", action="append", default=[],
                    metavar="NAME=PATH",
                    help="доп. колонка: executed.parquet impr-opt-прогона")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    df = load(a.pg_dir, a.fb_parquet)
    extras = {}
    for spec in a.extra:
        name, path = spec.split("=", 1)
        extras[name] = path
        df = df.merge(load_extra(path, name), on="qid", how="left")
    missing = df[df.pg_ms.isna() | df.median_ms.isna()]
    if len(missing):
        print(f"WARNING: нет одной из сторон для {len(missing)}: "
              f"{missing.qid.tolist()}")

    ok = df.dropna(subset=["pg_ms", "median_ms"]).copy()
    ok = ok.rename(columns={"median_ms": "fb_ms", "runs_ms": "fb_runs_ms"})
    geo = math.exp(float(ok.ratio_fb_pg.map(math.log).mean()))
    med = ok.ratio_fb_pg.median()
    slower = ok[ok.ratio_fb_pg > 1.5].qid.tolist()
    faster = ok[ok.ratio_fb_pg < 1 / 1.5].qid.tolist()

    cols = ["qid", "pg_ms", "fb_ms", "ratio_fb_pg", "pg_top_rows",
            "pg_planning_ms", "fb_runs_ms", "fetches", "record_reads"]
    cols += [c for c in extras if c in ok.columns]
    out = ok[cols]
    out.to_csv(os.path.join(a.out, "times_pg_vs_fb.csv"), index=False,
               float_format="%.1f")

    # сводка по доп. колонкам: отношение к PG и к базовому FB
    extra_lines = []
    for name in extras:
        if name not in ok.columns:
            continue
        e = ok.dropna(subset=[name])
        if not len(e):
            extra_lines.append(f"- {name}: нет данных")
            continue
        g_pg = math.exp(float((e[name] / e.pg_ms).map(math.log).mean()))
        g_fb = math.exp(float((e[name] / e.fb_ms).map(math.log).mean()))
        n = len(e)
        better = int((e[name] < e.fb_ms * 0.95).sum())
        worse = int((e[name] > e.fb_ms * 1.05).sum())
        same = n - better - worse
        extra_lines.append(
            f"- {name}: n={n}, геом. среднее к PG **{g_pg:.2f}x**, "
            f"к базовому FB **{g_fb:.2f}x**; времени меньше, чем у базового "
            f"FB (>5%): {better}, больше: {worse}, в пределах ±5%: {same}")

    def top(d, n=10):
        return d.head(n)[["qid", "pg_ms", "fb_ms", "ratio_fb_pg"]].to_string(
            index=False, float_format=lambda x: f"{x:,.1f}")

    lines = [
        "# JOB: время PostgreSQL vs Firebird (dellg15)",
        "",
        f"- PG: EXPLAIN ANALYZE Execution Time, один прогон (PG 17.5, imdb, "
        f"конфиг из reference_engine.yaml); строки клиенту не отгружаются.",
        f"- FB: median 3 прогонов по wall clock, execute+fetch (FB 5.0.5 HQbird, "
        f"imdb_fb5 golden, OptimizeForFirstRows=true).",
        f"- Один и тот же хост (dellg15), кэш FB прогрет повторами, PG мерился "
        f"первым прогоном после restore+ANALYZE.",
        "",
        f"Запросов сопоставлено: {len(ok)}",
        f"Геометрическое среднее FB/PG: **{geo:.2f}x**, медиана: {med:.2f}x",
        f"FB медленнее PG более чем в 1.5x: {len(slower)} "
        f"({', '.join(slower[:15])}{'…' if len(slower) > 15 else ''})",
        f"FB быстрее PG более чем в 1.5x: {len(faster)} "
        f"({', '.join(faster[:15])}{'…' if len(faster) > 15 else ''})",
        "",
    ]
    if extras:
        lines.append("## Дополнительные сборки")
        lines += extra_lines
        lines.append("")
    lines += [
        "## Топ-10: FB медленнее PG",
        "```", top(ok), "```",
        "",
        "## Топ-10: FB быстрее PG",
        "```", top(ok.sort_values("ratio_fb_pg"), 10), "```",
        "",
        "## Полная таблица (по убыванию FB/PG)",
        "",
        "| qid | PG ms | FB ms | FB/PG |" +
        "".join(f" {name} ms |" for name in extras if name in ok.columns),
        "|---|---:|---:|---:|" +
        "---:|" * len([n for n in extras if n in ok.columns]),
    ]
    for r in ok.itertuples():
        extra_cells = "".join(
            f" {getattr(r, name):,.1f} |" if getattr(r, name) == getattr(r, name)
            else " — |"
            for name in extras if name in ok.columns)
        lines.append(f"| {r.qid} | {r.pg_ms:,.1f} | {r.fb_ms:,.1f} | "
                     f"{r.ratio_fb_pg:.2f} |" + extra_cells)
    with open(os.path.join(a.out, "REPORT.md"), "w", encoding="utf-8",
              newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"geomean FB/PG = {geo:.2f}x, median = {med:.2f}, "
          f"slower>1.5x: {len(slower)}, faster>1.5x: {len(faster)}")
    print("saved:", a.out)


if __name__ == "__main__":
    main()
