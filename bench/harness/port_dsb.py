"""Портирование ворклоада DSB (505 запросов, 2 сюиты) под Firebird — §3.2.4.

Источник: bench/queries/dsb-{s2,s1}/ (gen_workload.py — dsqgen, диалект
postgres, дистрибуции normal sigma=2/sigma=1, rngseed 997, 5 инстансов
на шаблон; шаблоны 075/080/083 отсутствуют в s2 — heap-corruption
Win32-сборки dsqgen, 4 ретрая).

Данные: dsb_sf1_fb5.fdb (build_dsb.py), схема create_tables.sql c inline PK.

Правила порта (по живым конструкциям ворклоада):
  1) хвостовой `limit N;` -> `SELECT FIRST N ...` (FIRST перед DISTINCT —
     `SELECT DISTINCT FIRST` в FB невалиден, проверено на 5.0.5; outer
     select = первый select на глубине скобок 0 — у WITH-запросов CTE
     лежит в скобках);
  2) `cast('...' as date) + interval 'N day'` и `col + interval 'N day'`
     -> DATEADD(N DAY TO ...); в ворклоаде только DAY;
  3) `substring(col, a, b)` -> `SUBSTRING(col FROM a FOR b)`;
  4) WITH (CTE), CASE, BETWEEN, IN, EXISTS — FB5 нативно.

Запуск: python bench/harness/port_dsb.py
"""
from __future__ import annotations

import os
import re

from port_tpch import extract_tables, tags_of

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SUITES = ["dsb-s1", "dsb-s2"]
QROOT = os.path.join(ROOT, "bench", "queries")
MANIFEST_DIR = os.path.join(ROOT, "bench", "manifest")


def outer_select_first(sql: str) -> int:
    """Позиция первого `select` на глубине скобок 0 (outer select)."""
    depth = 0
    for m in re.finditer(r"\(|\)|\bselect\b", sql, re.I):
        if m.group(0) == "(":
            depth += 1
        elif m.group(0) == ")":
            depth -= 1
        else:
            if depth == 0:
                return m.start()
    return -1


def dsb_statements(raw: str) -> list[str]:
    """Независимые statements ворклоада (039 — двухблочный TPC-DS q39)."""
    parts = [p.strip().rstrip(";").strip() for p in raw.split(";")]
    return [p for p in parts if p]


class NotTranslatable(Exception):
    def __init__(self, sql: str, token: str):
        super().__init__(token)
        self.sql = sql
        self.token = token


def port_sql(raw: str) -> tuple[str, list[str]]:
    sql = raw.strip()
    notes = []

    # 1) limit N -> SELECT FIRST N (outer select; FIRST перед DISTINCT)
    m = re.search(r"\blimit\s+(\d+)\s*$", sql, re.I)
    if m:
        n = m.group(1)
        sql = sql[:m.start()].rstrip()
        pos = outer_select_first(sql)
        if pos < 0:
            raise ValueError("нет outer select для FIRST")
        end = pos + len("select")
        head = sql[:end] + f" FIRST {n}" + sql[end:]
        sql = head
        notes.append(f"limit {n} -> SELECT FIRST {n}")

    # 2) дата-арифметика с interval (в ворклоаде только DAY; левая часть —
    #    дата-литерал, колонка или cast(колонки); '-' -> отрицательный N)
    def _dateadd(left: str, sign: str, n: str) -> str:
        val = n if sign == "+" else f"-{n}"
        return f"DATEADD({val} DAY TO {left})"

    sql, n1 = re.subn(
        r"cast\s*\(\s*'(\d{4}-\d{1,2}-\d{1,2})'\s+as\s+date\)\s*([+-])\s*"
        r"interval\s*'(\d+)\s+day'",
        lambda m: _dateadd(f"CAST('{m.group(1)}' AS DATE)",
                           m.group(2), m.group(3)), sql, flags=re.I)
    sql, n2 = re.subn(
        r"\b([a-z_][a-z_0-9]*(?:\.[a-z_][a-z_0-9]*)*)\s*([+-])\s*"
        r"interval\s*'(\d+)\s+day'",
        lambda m: _dateadd(m.group(1), m.group(2), m.group(3)),
        sql, flags=re.I)
    if n1 or n2:
        notes.append(f"interval -> DATEADD ({n1}+{n2})")

    # 3) substring(col, a, b) -> TRIM(SUBSTRING(col FROM a FOR b)):
    #    над CHAR-колонкой FB сохраняет паддинг в результате, PG при
    #    bpchar->text срезает хвостовые пробелы (dsb_085: 'Parts
    #    missing<pad>' vs 'Parts missing')
    sql, n3 = re.subn(
        r"\bsubstring\s*\(\s*([a-z_][a-z_0-9]*)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)",
        lambda m: f"TRIM(TRAILING FROM SUBSTRING({m.group(1)} "
                  f"FROM {m.group(2)} FOR {m.group(3)}))", sql, flags=re.I)
    if n3:
        notes.append(f"substring(a,n,m) -> SUBSTRING FROM/FOR ({n3})")

    # 3b) алиасы-резервные слова FB (dsb_075: `AS year`)
    sql, n4 = re.subn(r"\bAS\s+(year|month|day)\b", r'AS "\1"', sql,
                      flags=re.I)
    if n4:
        notes.append(f"AS year/month/day -> кавычки ({n4})")

    # 3c) coalesce(char_col,'') в конкатенации: FB оператор || сохраняет
    #     CHAR-паддинг (SQL-семантика CHAR), PG при bpchar->text его
    #     срезает (dsb_084/085: 'Walters<pad>, Roger' vs 'Walters, Roger')
    sql, n5 = re.subn(
        r"coalesce\s*\(\s*([a-z_][a-z_0-9]*(?:\.[a-z_][a-z_0-9]*)?)\s*,\s*''\s*\)",
        r"coalesce(TRIM(TRAILING FROM \1),'')", sql, flags=re.I)
    if n5:
        notes.append(f"coalesce(col,'') -> TRIM TRAILING ({n5})")

    # 4) непереносимые в FB5 конструкции — исключение с записью
    #    (INTERSECT не реализован; ROLLUP/GROUPING отсутствуют)
    bad = re.search(r"\bintersect\b|\bexcept\b|\brollup\b|\bgrouping\s*\(",
                    sql, re.I)
    if bad:
        raise NotTranslatable(sql, bad.group(0).lower())
    return sql.rstrip().rstrip(";").rstrip() + "\n", notes


def template_of(sql: str) -> str:
    import hashlib
    t = re.sub(r"'[^']*'", "?", sql)
    t = re.sub(r"\b\d+\b", "?", t)
    t = re.sub(r"\s+", " ", t).strip().lower()
    return hashlib.md5(t.encode()).hexdigest()[:8]


def main():
    import yaml
    for suite in SUITES:
        qdir = os.path.join(QROOT, suite)
        if not os.path.isdir(qdir):
            print(f"{suite}: нет каталога — пропущен")
            continue
        # PG-оригиналы для S6 (source_sql) — копируются до перезаписи
        orig_dir = os.path.join(qdir, "orig")
        if not os.path.isdir(orig_dir):
            os.makedirs(orig_dir)
            import shutil
            for f in os.listdir(qdir):
                if f.endswith(".sql"):
                    shutil.copyfile(os.path.join(qdir, f),
                                    os.path.join(orig_dir, f))
        out = []
        excluded = []
        ids = sorted(f[:-4] for f in os.listdir(orig_dir)
                     if f.endswith(".sql"))
        for qid in ids:
            # читаем всегда оригинал (порт идемпотентен), пишем в рабочую
            raw = open(os.path.join(orig_dir, qid + ".sql"),
                       encoding="utf-8").read()
            stmts = dsb_statements(raw)
            root_file = os.path.join(qdir, qid + ".sql")
            suffixes = ([""] if len(stmts) == 1
                        else [f"_{i + 1}" for i in range(len(stmts))])
            if len(stmts) > 1 and os.path.exists(root_file):
                os.remove(root_file)  # стейк от сплита прошлых прогонов
            try:
                entries = []
                for stmt, suf in zip(stmts, suffixes):
                    sql, notes = port_sql(stmt)
                    if len(stmts) > 1:
                        notes = notes + ["multi-statement q39"]
                    out_id = qid + suf
                    with open(os.path.join(qdir, out_id + ".sql"), "w",
                              encoding="utf-8") as f:
                        f.write(sql)
                    tables = extract_tables(sql)
                    entries.append({
                        "id": out_id,
                        "suite": suite,
                        "db": "dsb-sf1",
                        "index_config": ["pk"],
                        "template": template_of(sql),
                        "tables": len(tables),
                        "table_list": tables,
                        "tags": tags_of(sql),
                        "deterministic": True,
                        "float_tolerance": None,
                        "subplan_scope": None,
                        "result": None,
                        "port_notes": "; ".join(notes) if notes else None,
                    })
                out.extend(entries)
            except NotTranslatable as e:
                excluded.append({"id": qid, "reason": e.token})
                # убрать ранее портированные файлы этого инстанса
                for suf in suffixes + [""]:
                    p = os.path.join(qdir, qid + suf + ".sql")
                    if os.path.exists(p):
                        os.remove(p)
        with open(os.path.join(MANIFEST_DIR, f"{suite}.yaml"), "w",
                  encoding="utf-8") as f:
            yaml.safe_dump(out, f, allow_unicode=True, sort_keys=False)
        if excluded:
            with open(os.path.join(MANIFEST_DIR,
                                   f"{suite}-excluded.yaml"), "w",
                      encoding="utf-8") as f:
                yaml.safe_dump(excluded, f, allow_unicode=True,
                               sort_keys=False)
        n_notes = sum(1 for m in out if m["port_notes"])
        print(f"{suite}: {len(out)} запросов, {len(excluded)} исключено "
              f"({n_notes} с port_notes)")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
