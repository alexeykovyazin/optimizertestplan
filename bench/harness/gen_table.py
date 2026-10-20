r"""Таблица сравнения PG / HQbird 5.0.5 (бейслин 3055) / новая сборка
v5.0-impr-opt (3056) по уже измеренным запросам HASH-корпуса.

Вход: свежий CSV прогона, baseline_plans.json, PG-эталоны (results/*_pg_reference).
Выход: markdown-таблица в stdout.
"""
import csv
import json
import math
import statistics
import sys

CSVP = sys.argv[1] if len(sys.argv) > 1 else "results/hash_corpus/hash_imdb_ab.csv"

baseline = json.load(open("results/hash_corpus/baseline_plans.json"))
expected = json.load(open("results/hash_corpus/expected_imdb.json"))

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


meas, prep = {}, {}
for row in csv.DictReader(open(CSVP, encoding="utf-8")):
    if row["kind"] == "measured" and row["status"] in ("ok", "timeout", "error"):
        meas[row["qid"]] = row  # последний measured по qid
    elif row["kind"] == "prepare" and row["status"] == "ok":
        prep[row["qid"]] = row

suites = {}
rows_out = []
for qid in sorted(meas, key=lambda q: (expected[q]["suite"], q)):
    r = meas[qid]
    e = expected[qid]
    s = e["suite"]
    b = baseline[qid]
    pgm, pgerr = pg_ms(qid, s)
    nm = float(r["exec_ms"]) if r["exec_ms"] else None
    bm = b["median_ms"]
    changed = (qid in prep and norm(b["plan"]) != norm(prep[qid]["plan"]))
    rows_out.append((qid, s, pgm, pgerr, bm, b["timed_out"], nm, r["status"],
                     r["check"], changed))
    suites.setdefault(s, []).append(rows_out[-1])


def fmt_s(ms):
    if ms is None:
        return "—"
    return f"{ms / 1000:.2f}" if ms < 60000 else f"{ms / 1000:.0f}"


print(f"| запрос | PG, с | HQbird 5, с | новая, с | новая/HQbird | новая/PG | план | чекс |")
print(f"|---|---|---|---|---|---|---|---|")
for qid, s, pgm, pgerr, bm, bto, nm, st, chk, ch in rows_out:
    r_hq = f"{nm / bm:.2f}" if (nm and bm) else "—"
    r_pg = f"{nm / pgm:.1f}" if (nm and pgm) else "—"
    hq_cell = "таймаут" if bto else fmt_s(bm)
    pg_cell = "ошибка" if pgerr else fmt_s(pgm)
    new_cell = ("таймаут" if st == "timeout"
                else ("ошибка" if st != "ok" else fmt_s(nm)))
    plan_cell = "⚠ сменился" if ch else ""
    # PG-арбитраж 20.10.2026: все MISMATCH (30/30) построчно совпали с PG
    chk_cell = {"match": "✓",
                "MISMATCH": "бейслин✗ ✓PG",
                "FINISHED-WAS-TIMEOUT": "монстр → дошёл"}.get(chk, chk)
    print(f"| {qid} | {pg_cell} | {hq_cell} | {new_cell} | {r_hq} | {r_pg} | "
          f"{plan_cell} | {chk_cell} |")

print()
print("Сводка по сюитам (геом. среднее отношение, только запросы, "
      "завершённые в обоих прогонах с числами PG):")
for s, rs in sorted(suites.items()):
    rh = [nm / bm for _q, _su, _pg, _pe, bm, bto, nm, st, _c, _ch
          in rs if nm and bm and not bto]
    rp = [nm / pg for _q, _su, pg, pe, _bm, _bto, nm, st, _c, _ch
          in rs if nm and pg and not pe]
    gmh = (math.exp(statistics.fmean(math.log(x) for x in rh))
           if rh else None)
    gmp = (math.exp(statistics.fmean(math.log(x) for x in rp))
           if rp else None)
    print(f"- {s}: n={len(rs)}, новая/HQbird {gmh:.3f}"
          if gmh else f"- {s}: n={len(rs)}", end="")
    print(f", новая/PG {gmp:.1f}" if gmp else "")
