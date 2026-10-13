"""Портирование 22 шаблонов TPC-H (qgen, seed 42) под Firebird — §3.2.1.

Источник S0: dbgen 2.14 (зеркало electrum/tpch-dbgen; официальный дистрибутив
требует регистрации на tpc.org), queries/*.tpl → qgen -s 1 -r 42.
Данные: SF1 в bench/datasets/tpch/sf1_csv (канонические счётчики dbgen).

Правила порта (§2.6, ожидаемые для TPC-H):
  1) date 'YYYY-MM-DD' -> CAST('YYYY-MM-DD' AS DATE)   (FB не знает
     DATE-literal префикса);
  2) CAST(...) +/- interval 'n' unit -> DATEADD(n UNIT TO / -n UNIT FROM ...);
  3) хвост qgen "where rownum <= n;" (после первого ';') снимается —
     батч-вариант TPC-H, стандартная практика портов;
  4) Q15 (create view revenue0; select; drop view) -> один запрос c
     производной таблицей (view референсится дважды, тело повторено —
     семантика эквивалентна); PG-эталон считается по ОРИГИНАЛЬНОЙ
     трёхстатейной форме (psql -f исполняет все три стейтмента);
  5) EXTRACT(year FROM x), substring(x FROM a FOR b), LIKE/NOT LIKE,
     EXISTS/NOT EXISTS, NOT IN (subquery), COUNT(DISTINCT) — FB5
     поддерживает нативно, не переписываются.

Дивергенции результатов: Q11/Q14 содержат деление (numeric PG против
FB DECIMAL) — float_tolerance в манифесте; сверить на S7.

Запуск: python bench/harness/port_tpch.py
"""
from __future__ import annotations

import hashlib
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "third_party", "tpch-dbgen", "queries_out")
QDIR = os.path.join(ROOT, "bench", "queries", "tpch")
MANIFEST_DIR = os.path.join(ROOT, "bench", "manifest")

# относительная допуск для запросов с делением (numeric PG vs FB DECIMAL)
FLOAT_TOL = {11: 1e-9, 14: 1e-9}


def split_first_statement(text: str) -> str:
    """Запрос до первого ';' (хвост qgen "where rownum <= n;" снимается)."""
    i = text.find(";")
    assert i > 0, "нет ';'"
    return text[:i].strip().rstrip(";").strip()


Q15_REVENUE = """select
    l_suppkey as supplier_no,
    sum(l_extendedprice * (1 - l_discount)) as total_revenue
from
    lineitem
where
    l_shipdate >= CAST('1994-03-01' AS DATE)
    and l_shipdate < DATEADD(3 MONTH TO CAST('1994-03-01' AS DATE))
group by
    l_suppkey"""


def port_sql(qnum: str) -> tuple[str, list[str]]:
    raw = open(os.path.join(SRC, f"{qnum}.sql"), encoding="utf-8").read()
    orig = split_first_statement(raw)
    notes = []
    if qnum == "15":
        notes.append("create view + drop view -> одиночный запрос "
                     "(view -> производная таблица, тело повторено)")
        sql = f"""select
    s_suppkey,
    s_name,
    s_address,
    s_phone,
    total_revenue
from
    supplier,
    ({Q15_REVENUE}) revenue0
where
    s_suppkey = supplier_no
    and total_revenue = (
        select
            max(total_revenue)
        from ({Q15_REVENUE}) revenue0
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
        # FB DATEADD: всегда TO, вычитание — отрицательным n
        val = n if op == "+" else f"-{n}"
        return f"DATEADD({val} {unit.upper()} TO CAST('{date}' AS DATE))"

    sql, n2 = re.subn(
        r"CAST\('(\d{4}-\d{2}-\d{2})' AS DATE\)\s*(\+|-)\s*interval\s+"
        r"'(\d+)'\s+(year|month|day)(?:\s*\(\d+\))?",
        sub_int, sql, flags=re.I)
    if n2:
        notes.append(f"interval-арифметика -> DATEADD ({n2}x)")
    # VALUE — зарезервированное слово FB (Q11: as value + order by value)
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
    os.makedirs(QDIR, exist_ok=True)
    manifest = []
    for i in range(1, 23):
        qid = f"tpch_{i:02d}"
        sql, notes = port_sql(str(i))
        with open(os.path.join(QDIR, f"{qid}.sql"), "w",
                  encoding="utf-8") as f:
            f.write(sql)
        tables = extract_tables(sql)
        manifest.append({
            "id": qid,
            "suite": "tpch",
            "db": "tpch-sf1",
            "index_config": ["pk"],
            "template": template_of(sql),
            "tables": len(tables),
            "table_list": tables,
            "tags": tags_of(sql),
            # Q18: ties в numwait — строки могут отличаться порядком при
            # равных counts; канон-сравнение мультимножества строк это
            # прощает, но дубликат s_name с равным count не различим —
            # считаем детерминированным по мультимножеству
            "deterministic": True,
            "float_tolerance": FLOAT_TOL.get(i),
            "subplan_scope": None,
            "result": None,
            "port_notes": "; ".join(notes) if notes else None,
        })
    with open(os.path.join(MANIFEST_DIR, "tpch.yaml"), "w",
              encoding="utf-8") as f:
        yaml.safe_dump(manifest, f, allow_unicode=True, sort_keys=False)
    n_notes = sum(1 for m in manifest if m["port_notes"])
    print(f"tpch: {len(manifest)} запросов ({n_notes} с port_notes) -> {QDIR}")


if __name__ == "__main__":
    main()
