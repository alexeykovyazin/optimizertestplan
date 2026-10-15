"""Портирование 22x2 запросов JCC-H (qgen, seed 42) под Firebird — §3.2.2.

Источник S0: ldbc/dbgen.JCC-H (Boncz & Anadiotis, TPCTC 2017; лицензия
TPC-EULA как у dbgen) — форк TPC-H dbgen 2.17.2 c JCCH_SKEW. Собран
локально MSVC (/DWIN32 /DORACLE /DTPCH /DRNG_TEST /DJCCH_SKEW); фикс
Windows-сборки: skew/phash.{c,h} использовали unsigned long (32 бита на
Windows x64) — умножение PRIME*i переполнялось, init_skew падал; типы
заменены на uint64_t (на Linux авторов long 64-битный, поэтому баг не
проявлялся).

Данные: dbgen -k -vf -s 1 (correlated+skewed SF1) -> bench/datasets/jcch/
skew_csv; счётчики канонические, КРОМЕ lineitem = ровно 6 000 000
(TPC-H SF1 имеет 6 001 215 — JCC-H выравнивает lineitem; PG-эталон
грузится из тех же .tbl, расхождение согласовано).

Запросы: qgen (normal-параметры) и qgen -k (skewed-параметры), seed 42,
SF1 -> queries_out_{norm,skew}/{norm,skew}_N.sql. 21/22 запросов имеют
разные константы между режимами (Q1 без параметров — идентичен). Оба
набора исполняются НА ОДНОЙ skewed-базе.

Правила порта — те же, что port_tpch.py (§2.6):
  1) date 'YYYY-MM-DD' -> CAST('YYYY-MM-DD' AS DATE);
  2) CAST +/- interval 'n' unit -> DATEADD;
  3) хвост qgen "where rownum <= n;" снимается;
  4) Q15 (create view revenue0; select; drop view) -> один запрос с
     производной таблицей; дата окна берётся из raw-запроса каждой
     сюиты (у JCC-H даты параметризованы, в отличие от TPC-H seed 42);
  5) EXTRACT/substring/LIKE/EXISTS/NOT IN/COUNT(DISTINCT) — FB5 нативно.

Запуск: python bench/harness/port_jcch.py
"""
from __future__ import annotations

import hashlib
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
JCCH = os.path.join(ROOT, "third_party", "dbgen.JCC-H")
SUITES = {
    "jcch-norm": os.path.join(JCCH, "queries_out_norm"),
    "jcch-skew": os.path.join(JCCH, "queries_out_skew"),
}
PREFIX = {"jcch-norm": "norm", "jcch-skew": "skew"}
QDIR = os.path.join(ROOT, "bench", "queries")
MANIFEST_DIR = os.path.join(ROOT, "bench", "manifest")

# относительная допуск для запросов с делением (numeric PG vs FB DECIMAL)
FLOAT_TOL = {11: 1e-9, 14: 1e-9}


def split_first_statement(text: str) -> str:
    i = text.find(";")
    assert i > 0, "нет ';'"
    return text[:i].strip().rstrip(";").strip()


def port_sql(suite: str, qnum: str) -> tuple[str, list[str]]:
    raw = open(os.path.join(SUITES[suite],
                            f"{PREFIX[suite]}_{qnum}.sql"),
               encoding="utf-8").read()
    orig = split_first_statement(raw)
    notes = []
    if qnum == "15":
        m = re.search(r"l_shipdate >= date '(\d{4}-\d{2}-\d{2})'", raw, re.I)
        assert m, "Q15: нет даты окна"
        d = m.group(1)
        notes.append(f"create view + drop view -> одиночный запрос "
                     f"(окно с {d}; view -> производная таблица, тело "
                     f"повторено)")
        revenue = f"""select
    l_suppkey as supplier_no,
    sum(l_extendedprice * (1 - l_discount)) as total_revenue
from
    lineitem
where
    l_shipdate >= CAST('{d}' AS DATE)
    and l_shipdate < DATEADD(3 MONTH TO CAST('{d}' AS DATE))
group by
    l_suppkey"""
        sql = f"""select
    s_suppkey,
    s_name,
    s_address,
    s_phone,
    total_revenue
from
    supplier,
    ({revenue}) revenue0
where
    s_suppkey = supplier_no
    and total_revenue = (
        select
            max(total_revenue)
        from ({revenue}) revenue0
    )
order by
    s_suppkey
"""
        return sql, notes

    sql = orig
    sql, n1 = re.subn(
        r"date\s+'(\d{4}-\d{2}-\d{2})'",
        lambda m: f"CAST('{m.group(1)}' AS DATE)", sql, flags=re.I)
    if n1:
        notes.append(f"date '...' -> CAST AS DATE ({n1}x)")

    def sub_int(m):
        date, op, n, unit = m.group(1), m.group(2), m.group(3), m.group(4)
        val = n if op == "+" else f"-{n}"
        return f"DATEADD({val} {unit.upper()} TO CAST('{date}' AS DATE))"

    sql, n2 = re.subn(
        r"CAST\('(\d{4}-\d{2}-\d{2})' AS DATE\)\s*(\+|-)\s*interval\s+"
        r"'(\d+)'\s+(year|month|day)(?:\s*\(\d+\))?",
        sub_int, sql, flags=re.I)
    if n2:
        notes.append(f"interval-арифметика -> DATEADD ({n2}x)")
    sql, n3 = re.subn(r"\bvalue\b", '"value"', sql, flags=re.I)
    if n3:
        notes.append(f'value -> "value" (VALUE reserved word in Firebird, '
                     f'{n3}x)')
    return sql.rstrip(";").rstrip() + "\n", notes


def extract_tables(sql: str) -> list[str]:
    frm = re.search(r"\bfrom\b(.*?)(?:\bwhere\b|\bgroup\b|\border\b|$)",
                    sql, re.I | re.S).group(1)
    tbls = re.findall(r"\b(?:from|join)\s+(\w+)", frm, re.I)
    return sorted({t.lower() for t in tbls
                   if t.lower() not in ("select", "lateral")})


def template_of(sql: str) -> str:
    t = re.sub(r"'[^']*'", "?", sql)
    t = re.sub(r"\b\d+\b", "?", t)
    t = re.sub(r"\s+", " ", t).strip().lower()
    return hashlib.md5(t.encode()).hexdigest()[:8]


def tags_of(sql: str) -> list[str]:
    tags = set()
    if re.search(r"\b(sum|count|avg|min|max)\s*\(", sql, re.I):
        tags.add("aggregate")
    if re.search(r"\b(exists|not exists)\b", sql, re.I):
        tags.add("subquery_exists")
    if re.search(r"\bnot in\s*\(\s*select\b", sql, re.I):
        tags.add("not_in_subquery")
    if re.search(r"\bin\s*\(\s*select\b", sql, re.I):
        tags.add("in_subquery")
    if re.search(r"\blike\b", sql, re.I):
        tags.add("like_predicate")
    if re.search(r"\bhaving\b", sql, re.I):
        tags.add("having")
    if re.search(r"\bgroup\s+by\b", sql, re.I):
        tags.add("group_by")
    if re.search(r"\border\s+by\b", sql, re.I):
        tags.add("order_by")
    if re.search(r"DATEADD", sql, re.I):
        tags.add("date_arith")
    if re.search(r"\bleft\s+(outer\s+)?join\b|\bouter\s+join\b", sql, re.I):
        tags.add("outer_join")
    if re.search(r"\bcase\b", sql, re.I):
        tags.add("case_expr")
    return sorted(tags)


def main():
    import yaml
    for suite, qdir in SUITES.items():
        out = os.path.join(QDIR, suite)
        os.makedirs(out, exist_ok=True)
        manifest = []
        for i in range(1, 23):
            qid = f"{suite.replace('-', '_')}_{i:02d}"
            sql, notes = port_sql(suite, str(i))
            with open(os.path.join(out, f"{qid}.sql"), "w",
                      encoding="utf-8") as f:
                f.write(sql)
            tables = extract_tables(sql)
            manifest.append({
                "id": qid,
                "suite": suite,
                "db": "jcch-sf1",
                "index_config": ["pk"],
                "template": template_of(sql),
                "tables": len(tables),
                "table_list": tables,
                "tags": tags_of(sql),
                "deterministic": True,
                "float_tolerance": FLOAT_TOL.get(i),
                "subplan_scope": None,
                "result": None,
                "port_notes": "; ".join(notes) if notes else None,
            })
        with open(os.path.join(MANIFEST_DIR, f"{suite}.yaml"), "w",
                  encoding="utf-8") as f:
            yaml.safe_dump(manifest, f, allow_unicode=True, sort_keys=False)
        n_notes = sum(1 for m in manifest if m["port_notes"])
        print(f"{suite}: {len(manifest)} запросов "
              f"({n_notes} с port_notes) -> {out}")


if __name__ == "__main__":
    main()
