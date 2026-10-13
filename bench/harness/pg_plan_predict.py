"""Может ли PG-план предсказать скорость Firebird?

Для каждого JOB-запроса извлекаем признаки из PG EXPLAIN-плана
(results/job_pg_reference) и из FB EXPLAIN-плана базовой матрицы
(collected.parquet), затем меряем, насколько расхождение планов
предсказывает время FB/PG (spearman, групповые медианы).

Признаки:
  pg_big_seq      — число больших таблиц (>1M строк), к которым PG идёт
                    последовательным сканом
  div_scan        — большие таблицы, где PG читает ПО ИНДЕКСУ, а FB —
                    Full Scan (главный сигнал расхождения доступа)
  div_join        — множества алгоритмов джоинов PG и FB не совпадают
  pg_root_rows    — Actual Rows корневого узла PG (log10)
  fb_record_reads — record_reads базового FB (log10; контроль — счётчик
                    сам по себе должен предсказывать время FB)

Выход: results/job_plan_predict/{analysis.csv, REPORT.md}
"""
import json
import math
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
import pandas as pd  # noqa: E402

PG_DIR = os.path.join(ROOT, "results", "job_pg_reference")
OUT = os.path.join(ROOT, "results", "job_plan_predict")
BASE_EXEC = os.path.join(ROOT, "results", "dedicated_dellg15",
                         "optimize_matrix", "first_rows", "executed.parquet")
BASE_COLL = os.path.join(ROOT, "results", "dedicated_dellg15",
                         "optimize_matrix", "first_rows", "collected.parquet")
MANIFEST = os.path.join(ROOT, "db", "imdb", "imdb_build_manifest.json")
BIG_ROWS = 1_000_000

JOIN_PAT = re.compile(r"(Nested Loop Join|Hash Join|Merge Join)")
FB_FULL_PAT = re.compile(r'Table "([A-Z0-9_$]+)"[^\n]*Full Scan')


def pg_walk(node, acc):
    """Собрать из узла PG: доступы к таблицам, алгоритмы джоинов."""
    nt = node.get("Node Type", "")
    ar = node.get("Actual Rows")
    if ar is not None:
        acc["max_rows"] = max(acc["max_rows"], ar)
    rel = node.get("Relation Name")
    if rel:
        kind = ("seq" if nt == "Seq Scan" else
                "idx" if "Index" in nt or nt == "Bitmap Heap Scan" else
                "other")
        acc["rel"].setdefault(rel.lower(), set()).add(kind)
    for jn in ("Nested Loop", "Hash Join", "Merge Join"):
        if nt == jn:
            acc["joins"].add(jn)
    for c in node.get("Plans", []):
        pg_walk(c, acc)
    return acc


def fb_features(plan_text: str, big: set[str]):
    joins = set(JOIN_PAT.findall(plan_text or ""))
    full = set(FB_FULL_PAT.findall(plan_text or ""))
    div_scan = sorted(t for t in full if t in big)
    return joins, full, div_scan


def main():
    os.makedirs(OUT, exist_ok=True)
    manifest = json.load(open(MANIFEST, encoding="utf-8"))
    big = {t.upper() for t, v in manifest["tables"].items()
           if v.get("rows", 0) > BIG_ROWS}
    print("big tables:", sorted(big))

    coll = pd.read_parquet(BASE_COLL)
    coll = coll[coll.suite == "job"]
    fb_plans = {r.query_id: r.detailed_plan for r in coll.itertuples()}
    exec_ = pd.read_parquet(BASE_EXEC)
    exec_ = exec_[exec_.suite == "job"]
    fb_ms = {r.query_id: r.median_ms for r in exec_.itertuples()}
    fb_reads = {r.query_id: r.record_reads for r in exec_.itertuples()}

    rows = []
    for r in coll.itertuples():
        qid = r.query_id
        pj = json.load(open(os.path.join(PG_DIR, qid + ".json"),
                            encoding="utf-8"))
        proot = pj["plan"][0]["Plan"]
        pg = pg_walk(proot, {"rel": {}, "joins": set(), "max_rows": 0})
        # PG называет "Nested Loop", FB — "Nested Loop Join"
        pg_joins = {("Nested Loop Join" if j == "Nested Loop" else j)
                    for j in pg["joins"]}
        pg_idx_only_big = {t.upper() for t, kinds in pg["rel"].items()
                           if "seq" not in kinds and t.upper() in big}
        fb_joins, fb_full, div_scan = fb_features(fb_plans[qid], big)
        div_scan = set(div_scan) & pg_idx_only_big
        pg_ms = pj["plan"][0]["Execution Time"]
        rows.append({
            "qid": qid,
            "pg_ms": pg_ms, "fb_ms": fb_ms.get(qid),
            "ratio_fb_pg": fb_ms.get(qid, float("nan")) / pg_ms
            if pg_ms else None,
            "pg_big_seq": sum(1 for t, k in pg["rel"].items()
                              if "seq" in k and t.upper() in big),
            "div_scan": len(div_scan),
            "div_scan_tables": ",".join(sorted(div_scan)),
            "div_join": int(pg_joins != fb_joins),
            "pg_max_rows": pg["max_rows"],
            "fb_record_reads": fb_reads.get(qid),
        })
    df = pd.DataFrame(rows)
    for c in ("ratio_fb_pg", "pg_max_rows", "fb_record_reads"):
        df[c + "_log"] = df[c].map(lambda x: math.log10(x)
                                   if x and x > 0 else None)
    df.to_csv(os.path.join(OUT, "analysis.csv"), index=False)

    feats = {"div_scan": "PG индекс vs FB Full Scan (большие табл.)",
             "pg_big_seq": "число seq-сканов PG по большим табл.",
             "div_join": "разные алгоритмы джоинов PG/FB",
             "pg_max_rows_log": "log10 макс. Actual Rows узла PG",
             "fb_record_reads_log": "log10 record_reads FB (контроль)"}
    lines = ["# Предсказательная сила PG-планов для времени Firebird (JOB, n=113)",
             "",
             "Целевая переменная — log10(FB_ms / PG_ms), базовый FB 5.0.5",
             "(HQbird, first_rows) против PG 17.5, обе на dellg15.", "",
             "## Спирмен-корреляции признаков с log10(отношение времени)",
             "", "| признак | rho | p-подобное |", "|---|---:|---:|"]
    tgt = "ratio_fb_pg_log"
    for f, desc in feats.items():
        rho = df[[f, tgt]].corr(method="spearman").iloc[0, 1]
        lines.append(f"| {f} ({desc}) | {rho:+.2f} | |")
    lines.append("")
    slow = df.ratio_fb_pg >= 10
    pred = df.div_scan >= 1
    tp = int((slow & pred).sum()); fp = int((~slow & pred).sum())
    fn = int((slow & ~pred).sum())
    lines.append("## Прогноз «FB будет >=10x медленнее PG» по правилу "
                 "div_scan>=1")
    lines.append("")
    lines.append(f"- верно {tp}, ложных тревог {fp}, пропусков {fn} "
                 f"(из {int(slow.sum())} медленных); точность "
                 f"{tp/max(tp+fp,1):.0%}, полнота {tp/max(tp+fn,1):.0%}")
    lines.append("")
    d1 = df[df.div_scan == 0]
    d2 = df[df.div_scan >= 1]
    lines.append("## Группы по div_scan (PG идёт по индексу, FB — Full Scan)")
    lines.append("")
    lines.append(f"- div_scan = 0: n={len(d1)}, медиана FB/PG = "
                 f"{d1.ratio_fb_pg.median():.1f}x")
    lines.append(f"- div_scan >= 1: n={len(d2)}, медиана FB/PG = "
                 f"{d2.ratio_fb_pg.median():.1f}x, медиана PG ms = "
                 f"{d2.pg_ms.median():.0f}, медиана FB ms = "
                 f"{d2.fb_ms.median():,.0f}")
    lines.append(f"- таблицы-виновники чаще прочих: " +
                 ", ".join(sorted(
                     ",".join(df[df.div_scan >= 1].div_scan_tables)
                     .split(",")))[:120])
    dj1 = df[df.div_join == 0]
    dj2 = df[df.div_join == 1]
    lines.append("")
    lines.append("## Группы по div_join (алгоритмы джоинов различаются)")
    lines.append("")
    lines.append(f"- совпадают: n={len(dj1)}, медиана FB/PG = "
                 f"{dj1.ratio_fb_pg.median():.1f}x")
    lines.append(f"- различаются: n={len(dj2)}, медиана FB/PG = "
                 f"{dj2.ratio_fb_pg.median():.1f}x")
    lines.append("")
    lines.append("## Топ-10 расхождений по div_scan (с отношением времени)")
    lines.append("")
    lines.append("| qid | div_scan | таблицы | FB/PG | PG ms | FB ms |")
    lines.append("|---|---:|---|---:|---:|---:|")
    for r in df[df.div_scan > 0].sort_values(
            "ratio_fb_pg", ascending=False).head(10).itertuples():
        lines.append(f"| {r.qid} | {r.div_scan} | {r.div_scan_tables} | "
                     f"{r.ratio_fb_pg:,.1f} | {r.pg_ms:,.0f} | "
                     f"{r.fb_ms:,.0f} |")
    with open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8",
              newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("written", OUT)


if __name__ == "__main__":
    main()
