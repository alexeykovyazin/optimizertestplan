r"""Сводная таблица: PG / HQbird 5.0.5 бейслин / N сборок v5.0-impr-opt.

Запуск:
  python gen_table2.py --out TABLE.md \
      --run "3b7c7174ec=hash_imdb_ab.csv" --run "021a31bf8e=hash_imdb_ab2.csv"

Колонки на прогон: время, ratio к HQbird, план (смена vs бейслин), чекс.
Время PG и бейслин — общие. PG-колонка: из results/<suite>_pg_reference.
"""
import argparse
import csv
import json
import math
import statistics

ap = argparse.ArgumentParser()
ap.add_argument("--out", default="results/hash_corpus/TABLE.md")
ap.add_argument("--run", action="append", required=True,
                help="метка=путь/к/csv (метка — голова ветки)")
ap.add_argument("--expected", default="results/hash_corpus/expected_imdb.json")
ap.add_argument("--baseline", default="results/hash_corpus/baseline_plans.json")
a = ap.parse_args()

expected = json.load(open(a.expected))
baseline = json.load(open(a.baseline))
runs = []  # (label, {qid: row}, {qid: prep})
for spec in a.run:
    label, path = spec.split("=", 1)
    meas, prep = {}, {}
    for r in csv.DictReader(open(path, encoding="utf-8")):
        if r["kind"] == "measured" and r["status"] in ("ok", "timeout",
                                                       "error"):
            meas[r["qid"]] = r
        elif r["kind"] == "prepare" and r["status"] == "ok":
            prep[r["qid"]] = r
    runs.append((label, meas, prep))

pg_cache = {}


def pg_ms(qid, suite):
    if qid not in pg_cache:
        d = json.load(open(f"results/{suite}_pg_reference/{qid}.json",
                           encoding="utf-8"))
        ms = d.get("pg_execution_ms")
        if ms is None and d.get("seconds"):
            ms = d["seconds"] * 1000.0
        pg_cache[qid] = (ms, bool(d.get("error")))
    return pg_cache[qid]


def norm(p):
    return " ".join((p or "").split())


def fmt_s(ms):
    return "—" if ms is None else (f"{ms / 1000:.2f}" if ms < 60000
                                   else f"{ms / 1000:.0f}")


hdr = ["запрос", "PG, с", "HQbird 5, с"]
sep = ["---", "---", "---"]
for label, _m, _p in runs:
    hdr += [f"новая {label}, с", "к HQbird"]
    sep += ["---", "---"]

lines = ["| " + " | ".join(hdr) + " |", "|" + "|".join(sep) + "|"]
suites = {}
allq = sorted(set().union(*[set(m) for _l, m, _p in runs]),
              key=lambda q: (expected[q]["suite"], q))
for qid in allq:
    e = expected[qid]
    b = baseline[qid]
    pgm, pgerr = pg_ms(qid, e["suite"])
    cells = [qid, "ошибка" if pgerr else fmt_s(pgm),
             "таймаут" if b["timed_out"] else fmt_s(b["median_ms"])]
    ratios = []
    for label, m, p in runs:
        r = m.get(qid)
        if not r:
            cells += ["—", "—"]
            continue
        nm = float(r["exec_ms"]) if r["exec_ms"] else None
        bm = b["median_ms"]
        rt = f"{nm / bm:.2f}" if (nm and bm) else "—"
        if nm and bm:
            ratios.append(nm / bm)
        chg = (qid in p and norm(b["plan"]) != norm(p[qid]["plan"]))
        st = ("таймаут" if r["status"] == "timeout"
              else ("ошибка" if r["status"] != "ok" else fmt_s(nm)))
        chk = {"match": "✓", "MISMATCH": "✗б",
               "FINISHED-WAS-TIMEOUT": "монстр"}.get(r["check"], "")
        cells += [f"{st}{' ⚠' if chg else ''} {chk}".strip(), rt]
    lines.append("| " + " | ".join(cells) + " |")
    suites.setdefault(e["suite"], []).append((qid, ratios))

lines.append("")
lines.append("## Сводка (геом. среднее ratio к бейслину, "
             "завершённые в обоих)\n")
lines.append("| сюита | n | " +
             " | ".join(f"{l}" for l, _m, _p in runs) + " |")
lines.append("|---|---|" + "---|" * len(runs))
for s, qs in sorted(suites.items()):
    row = [s, str(len(qs))]
    for i in range(len(runs)):
        rs = [rts[i] for _q, rts in qs if len(rts) > i]
        rs = [x for x in rs if x]
        row.append(f"{math.exp(statistics.fmean(math.log(x) for x in rs)):.3f}"
                   if rs else "—")
    lines.append("| " + " | ".join(row) + " |")

open(a.out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print(f"written {a.out}: {len(allq)} queries, {len(runs)} runs")
