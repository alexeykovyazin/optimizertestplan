r"""Кандидаты на многоколоночные (расширенные) статистики из SQL-корпуса.

Идея: расширенная статистика (совместный MCV пары колонок) помогает, когда
в запросе таблица ФИЛЬТРУЕТСЯ по одной колонке, а СОЕДИНЯЕТСЯ по другой —
селективность соединения зависит от корреляции. Анализатор достаёт из
каждого запроса алиасы, join-рёбра (a.x = b.y) и фильтры (a.c <op> literal,
LIKE, IN, BETWEEN, IS [NOT] NULL) и агрегирует пары
(таблица, join-колонка, фильтр-колонка) по числу запросов.

Запуск: python bench/harness/ext_stats_candidates.py
Вывод: отчёт results/ext_stats_job/REPORT.md + DDL candidates.sql.
"""
import glob
import os
import re
import sys
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
SUITES = {"JOB": os.path.join(REPO, "bench", "queries", "job"),
          "JOB-light": os.path.join(REPO, "bench", "queries", "job-light")}
SCHEMA = r"E:\tmp\imdb_schema.tsv"  # table<TAB>column<TAB>type
OUT_DIR = os.path.join(REPO, "results", "ext_stats_job")

TYPES = {}
for ln in open(SCHEMA, encoding="utf-8"):
    parts = ln.rstrip("\n").split("\t")
    if len(parts) == 3:
        TYPES.setdefault(parts[0].lower(), {})[parts[1].lower()] = parts[2]

ALIAS_RE = re.compile(
    r"(?:\bfrom\b|\bjoin\b|,)\s*([a-z_][a-z_0-9]*)"
    r"(?:\s+(?:as\s+)?([a-z_][a-z_0-9]*))?(?![a-z_0-9.])", re.I)
EDGE_RE = re.compile(
    r"([a-z_][a-z_0-9]*)\.([a-z_][a-z_0-9]*)\s*=\s*"
    r"([a-z_][a-z_0-9]*)\.([a-z_][a-z_0-9]*)", re.I)
FILTER_RE = re.compile(
    r"([a-z_][a-z_0-9]*)\.([a-z_][a-z_0-9]*)\s*"
    r"(=|<>|!=|>|<|>=|<=|\blike\b|\bnot\s+like\b|\bbetween\b|\bin\b|"
    r"\bis\s+not\s+null\b|\bis\s+null\b)", re.I)
SQLKW = {"select", "from", "where", "join", "inner", "left", "outer", "on",
         "and", "or", "not", "as", "group", "order", "by", "having", "min",
         "max", "count", "like", "between", "is", "in", "distinct", "as"}


def parse(sql: str):
    al = {}
    for tab, alias in ALIAS_RE.findall(sql):
        alias = (alias or tab).lower()
        if alias in SQLKW:
            continue
        tab = tab.lower()
        if tab in TYPES:
            al[alias] = tab
    edges, ecols, filters = set(), set(), set()
    for a1, c1, a2, c2 in EDGE_RE.findall(sql):
        if a1.lower() in al and a2.lower() in al:
            t1, t2 = al[a1.lower()], al[a2.lower()]
            edges.add(((t1, c1.lower()), (t2, c2.lower())))
            ecols.add((t1, c1.lower()))
            ecols.add((t2, c2.lower()))
    for a, c, op in FILTER_RE.findall(sql):
        t = al.get(a.lower())
        if t and (t, c.lower()) not in ecols:
            filters.add((t, c.lower(), op.lower()))
    return al, edges, filters


def main():
    per_suite = {}
    for suite, qdir in SUITES.items():
        # (table, joincol, filtercol) -> {qid: is_range_on_filtercol}
        cand = defaultdict(dict)
        for f in sorted(glob.glob(os.path.join(qdir, "*.sql"))):
            qid = os.path.basename(f)[:-4]
            sql = open(f, encoding="utf-8").read()
            _al, edges, filters = parse(sql)
            jcols = defaultdict(set)   # table -> {join cols}
            for (t1, c1), (t2, _c2) in edges:
                jcols[t1].add(c1)
                jcols[t2].add(_c2)
            fcols = defaultdict(dict)  # table -> {filter col: is_range}
            for t, c, op in filters:
                if c != "id":
                    fcols[t][c] = op in (">", "<", ">=", "<=", "between")
            for t in jcols:
                for jc in jcols[t]:
                    for fc, rng in fcols.get(t, {}).items():
                        cand[(t, jc, fc)][qid] = rng
            for t, fcm in fcols.items():  # несколько фильтр-колонок в таблице
                fcs = sorted(fcm)
                for i in range(len(fcs)):
                    for j in range(i + 1, len(fcs)):
                        cand[(t, None, f"{fcs[i]}+{fcs[j]}")][qid] = \
                            fcm[fcs[i]] or fcm[fcs[j]]
        per_suite[suite] = cand

    os.makedirs(OUT_DIR, exist_ok=True)
    rep = ["# Кандидаты многоколоночных статистик: JOB + JOB-light\n"]
    ddl, seen = [], set()
    for suite, cand in per_suite.items():
        rep.append(f"\n## {suite}\n")
        rows = sorted(cand.items(),
                      key=lambda kv: (-len(kv[1]), kv[0][0], kv[0][1] or ""))
        rep.append("| таблица | join-колонка | фильтр | запросов | из них диапазон |")
        rep.append("|---|---|---|---|---|")
        for (t, jc, fc), qs in rows[:45]:
            nrng = sum(1 for r in qs.values() if r)
            blob = " **BLOB**" if TYPES.get(t, {}).get(fc) == "blob(subtype 1)" else ""
            rep.append(f"| {t} | {jc or '—'} | {fc}{blob} | {len(qs)} | {nrng} |")
        for (t, jc, fc), _qs in rows[:45]:
            cols = ([c for c in (jc, fc) if c] if jc else fc.split("+"))
            cols = [c for c in cols if TYPES.get(t, {}).get(c) != "blob(subtype 1)"]
            if len(cols) < 2:
                continue
            nm = f"STAT_{t.upper()}_{'_'.join(c.upper() for c in cols)}"
            nm = nm[:31]
            while nm in seen:
                nm = nm[:28] + f"_{len(seen):02d}"
            seen.add(nm)
            ddl.append(f"CREATE EXTENDED STATISTICS {nm} ON "
                       f"{t.upper()}({', '.join(c.upper() for c in cols)});")
    open(os.path.join(OUT_DIR, "REPORT.md"), "w", encoding="utf-8").write(
        "\n".join(rep) + "\n")
    open(os.path.join(OUT_DIR, "candidates.sql"), "w", encoding="utf-8").write(
        "\n".join(ddl) + "\n")
    print("\n".join(rep))
    print(f"\nDDL ({len(ddl)}):\n" + "\n".join(ddl))


if __name__ == "__main__":
    main()
