r"""Сравнение прогона HASH-корпуса (hash_imdb_ab.csv) с бейслином 3055.

Вход: CSV раннера (kind=prepare/measured), baseline_plans.json (план+
медиана бейслина HQbird 5.0.5 3055), expected_imdb.json (чексуммы).
Выход: REPORT.md — валидация, время (ratio к бейслину), смены планов,
HASH-статус планов, монстры.
"""
import csv
import json
import math
import statistics
import sys

CSV = sys.argv[1] if len(sys.argv) > 1 else "results/hash_corpus/hash_imdb_ab.csv"
OUT = sys.argv[2] if len(sys.argv) > 2 else "results/hash_corpus/REPORT.md"

baseline = json.load(open("results/hash_corpus/baseline_plans.json"))
expected = json.load(open("results/hash_corpus/expected_imdb.json"))

prep, meas = {}, {}
for row in csv.DictReader(open(CSV, encoding="utf-8")):
    if row["kind"] == "prepare":
        prep[row["qid"]] = row
    elif row["kind"] == "measured":
        meas[row["qid"]] = row


def norm(p):
    return " ".join((p or "").split())


def hash_status(p):
    return "HASH" if "HASH" in (p or "").upper() else "no-HASH"


report = []
report.append("# HASH-корпус IMDb: v5.0-impr-opt (3056) vs HQbird 5.0.5 бейслин (3055)\n")
report.append("Корпус: 239 запросов с HASH в плане бейслина (ceb-imdb-regen 121, "
              "job-light 21, scale 97). БД: свежая копия голдена + "
              "ALTER DATABASE ADD/REFRESH EXTENDED STATISTICS FULL (228 c), "
              "конфиг: PredicateCorrelation/ExtendedStatistics/SubQueryConversion = true.\n")

# -- валидация
ok = sum(1 for r in meas.values() if r["check"] == "match")
mism = [q for q, r in meas.items() if r["check"] == "MISMATCH"]
fin_to = [q for q, r in meas.items() if r["check"] == "FINISHED-WAS-TIMEOUT"]
to = [q for q, r in meas.items() if r["status"] == "timeout"]
err = [q for q, r in meas.items() if r["status"] == "error"]
nosql = [q for q, r in meas.items() if r["status"] == "no_sql"]
prep_bad = [q for q, r in prep.items() if r["status"] != "ok"]
report.append(f"## Валидация\n- measured: {len(meas)} из {len(expected)}")
report.append(f"- checksum match: {ok}")
report.append(f"- MISMATCH: {len(mism)} {mism[:10]}")
report.append(f"- завершившиеся монстры (был таймаут в бейслине): {len(fin_to)} {fin_to}")
report.append(f"- таймауты (>300 c): {len(to)} {to[:10]}")
report.append(f"- ошибки исполнения: {len(err)} {err[:10]}")
report.append(f"- нет SQL-файла: {len(nosql)} {nosql}")
report.append(f"- ошибки/таймауты prepare: {len(prep_bad)} {prep_bad[:10]}\n")

# -- время по завершившимся в обоих прогонах
rows = []
for q, r in meas.items():
    b = baseline.get(q)
    if not b or b["timed_out"] or r["status"] != "ok" or not r["exec_ms"]:
        continue
    bm = b["median_ms"]
    if not bm:
        continue
    rows.append((q, b["suite"], bm, float(r["exec_ms"]),
                 float(r["exec_ms"]) / bm,
                 norm(b["plan"]) != norm(prep[q]["plan"] if q in prep else "")))

if rows:
    by_suite = {}
    for q, s, bm, nm, ratio, changed in rows:
        by_suite.setdefault(s, []).append(ratio)
    report.append("## Время (ratio к медиане бейслина, меньше=лучше)\n")
    report.append("| сюита | n | геом. среднее | медиана | быстрее (<=0.95) | медленнее (>=1.05) |")
    report.append("|---|---|---|---|---|---|")
    for s, rs in sorted(by_suite.items()):
        gm = math.exp(statistics.fmean(math.log(x) for x in rs))
        faster = sum(1 for x in rs if x <= 0.95)
        slower = sum(1 for x in rs if x >= 1.05)
        report.append(f"| {s} | {len(rs)} | {gm:.3f} | "
                      f"{statistics.median(rs):.3f} | {faster} | {slower} |")
    all_r = [r for rs in by_suite.values() for r in rs]
    gm = math.exp(statistics.fmean(math.log(x) for x in all_r))
    report.append(f"\nВсего: n={len(all_r)}, геом. среднее {gm:.3f}\n")

    report.append("## Топ изменений времени (|ratio|, завершившиеся в обоих)\n")
    report.append("| запрос | сюита | бейслин, с | новый, с | ratio | план сменился |")
    report.append("|---|---|---|---|---|---|")
    for q, s, bm, nm, ratio, changed in sorted(rows, key=lambda r: abs(r[4] - 1),
                                               reverse=True)[:15]:
        report.append(f"| {q} | {s} | {bm/1000:.1f} | {nm/1000:.1f} | "
                      f"{ratio:.2f}x | {'да' if changed else ''} |")

# -- планы
changed = [(q, q) for q in prep
           if q in baseline
           and norm(baseline[q]["plan"]) != norm(prep[q]["plan"])]
report.append(f"\n## Планы\n- смен плоского плана: {len(changed)} из "
              f"{len(prep)} (vs бейслин)")
h_lost = [q for q in prep if q in baseline
          and hash_status(baseline[q]["plan"]) == "HASH"
          and hash_status(prep[q]["plan"]) == "no-HASH"]
h_gain = [q for q in prep if q in baseline
          and hash_status(baseline[q]["plan"]) == "no-HASH"
          and hash_status(prep[q]["plan"]) == "HASH"]
report.append(f"- ушли от HASH: {len(h_lost)} {h_lost[:12]}")
report.append(f"- пришли к HASH: {len(h_gain)} {h_gain[:12]}")
still_hash = sum(1 for q in prep if hash_status(prep[q]["plan"]) == "HASH")
report.append(f"- с HASH в новом плане: {still_hash} из {len(prep)}\n")

if changed:
    report.append("## Запросы со сменой плана (план бейслина -> новый план)\n")
    for q, _ in changed[:25]:
        s = baseline[q]["suite"]
        bm = baseline[q]["median_ms"]
        bmt = f"{bm / 1000:.0f} c" if bm else "таймаут"
        report.append(f"### {q} ({s}, бейслин {bmt}"
                      f"{', был таймаут' if baseline[q]['timed_out'] else ''})")
        report.append("```")
        report.append("было: " + norm(baseline[q]["plan"])[:400])
        report.append("стало: " + norm(prep[q]["plan"])[:400])
        r = meas.get(q)
        if r and r["exec_ms"]:
            report.append(f"время: {float(r['exec_ms'])/1000:.1f} c, "
                          f"{r['check']}")
        report.append("```\n")

open(OUT, "w", encoding="utf-8").write("\n".join(report) + "\n")
print(f"REPORT: {OUT}")
print(f"measured {len(meas)}/{len(expected)}, match {ok}, MISMATCH {len(mism)}, "
      f"timeouts {len(to)}, monsters-finished {len(fin_to)}, "
      f"plan changes {len(changed)}")
