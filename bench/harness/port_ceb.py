"""Портирование корпуса STATS-CEB под Firebird (раздел 4.5 плана).

Правила переписывания, применяемые здесь:
  - '...'::timestamp  -> CAST('...' AS TIMESTAMP)
  - <alias>.Date      -> <alias>."Date"      (DATE — зарезервированное слово FB;
                          в оригинале функции над столбцом не было, форма
                          предиката сохраняется)
  - <alias>.Count     -> <alias>."Count"     (COUNT — зарезервированное слово FB)
  - LIMIT / ILIKE / INTERVAL / STRING_AGG в корпусе не встречаются
    (все запросы — COUNT(*) с равенствами и диапазонами).

Главное правило: переписывание не меняет то, что видит оптимизатор —
форма предикатов (диапазон остаётся диапазоном) и функции над столбцами
сохраняются; отклонения фиксируются в port_notes манифеста.

Оригиналы сохраняются в queries/<suite>/original/.
"""
from __future__ import annotations

import hashlib
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "third_party", "STATS-CEB", "workloads", "stats_CEB")
QDIR = os.path.join(ROOT, "bench", "queries")
MANIFEST_DIR = os.path.join(ROOT, "bench", "manifest")

TABLES_PK = {"users": "Id", "posts": "Id", "postLinks": "Id", "postHistory": "Id",
             "comments": "Id", "votes": "Id", "badges": "Id", "tags": "Id"}


def port_sql(sql: str) -> tuple[str, list[str]]:
    """Вернуть (портированный текст, [port_notes])."""
    notes = []
    out = sql
    if "::timestamp" in out or "::date" in out.lower():
        out = re.sub(r"'([^']*)'::timestamp",
                     r"CAST('\1' AS TIMESTAMP)", out, flags=re.I)
        notes.append("'...'::timestamp -> CAST('...' AS TIMESTAMP)")
    out, n1 = re.subn(r"\b(\w+)\.Date\b", r'\1."Date"', out)
    if n1:
        notes.append('Date -> "Date" (reserved word in Firebird)')
    out, n2 = re.subn(r"\b(\w+)\.Count\b", r'\1."Count"', out)
    if n2:
        notes.append('Count -> "Count" (reserved word in Firebird)')
    out = out.strip().rstrip(";").strip()
    return out, notes


def extract_tables(sql: str) -> list[str]:
    frm = re.search(r"\bFROM\b(.*?)(?:\bWHERE\b|$)", sql, re.I | re.S).group(1)
    tables = re.findall(r"\b(\w+)\s+as\s+\w+", frm, re.I)
    return [t for t in tables if t.lower() in {k.lower() for k in TABLES_PK}]


def extract_join_pairs(sql: str) -> list[tuple[str, str, str, str]]:
    """Равенственные предикаты соединений: (таблица, столбец, таблица, столбец)."""
    pairs = []
    for m in re.finditer(r"\b(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)", sql):
        pairs.append((m.group(1), m.group(2), m.group(3), m.group(4)))
    return pairs


def extract_alias_map(sql: str) -> dict[str, str]:
    """alias.lower() -> имя таблицы (как в FROM)."""
    frm = re.search(r"\bFROM\b(.*?)(?:\bWHERE\b|$)", sql, re.I | re.S).group(1)
    return {a.lower(): t for t, a in re.findall(r"\b(\w+)\s+as\s+(\w+)", frm, re.I)}


def join_pairs_with_tables(sql: str, amap: dict[str, str]) -> list[tuple[str, str, str, str]]:
    """Равенственные предикаты, переведённые в (таблица, столбец, таблица, столбец)."""
    out = []
    for m in re.finditer(r"\b(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)", sql):
        ta, tb = amap.get(m.group(1).lower()), amap.get(m.group(3).lower())
        if ta and tb:
            out.append((ta, m.group(2), tb, m.group(4)))
    return out


def template_of(sql: str) -> str:
    t = re.sub(r"'[^']*'", "?", sql)
    t = re.sub(r"\b\d+\b", "?", t)
    t = re.sub(r"\s+", " ", t).strip().lower()
    return hashlib.md5(t.encode()).hexdigest()[:8]


def tags_of(sql: str, tables: list[str], join_pairs) -> list[str]:
    """join_pairs: (таблица, столбец, таблица, столбец) — уже с именами таблиц."""
    tags = {"aggregate"}  # COUNT(*) во всех запросах корпуса
    if re.search(r"\b\w+\.\s*\"?\w+\"?\s*(>=|<=|>|<)\s*[?'0-9]", sql):
        tags.add("range_predicate")
    # типы соединений
    aliased = {t.lower(): t for t in tables}
    has_fk_fk = False
    for ta, ca, tb, cb in join_pairs:
        la, lb = ta.lower(), tb.lower()
        if la not in aliased or lb not in aliased:
            continue
        a_pk = (ca.strip('"').lower() == TABLES_PK[aliased[la]].lower())
        b_pk = (cb.strip('"').lower() == TABLES_PK[aliased[lb]].lower())
        if not a_pk and not b_pk:
            has_fk_fk = True
    if has_fk_fk:
        tags.add("fk_fk_join")
    if len(tables) >= 8:
        tags.add("many_tables")
    # цикл в графе соединений
    edges = [(ta.lower(), tb.lower()) for ta, ca, tb, cb in join_pairs
             if ta.lower() in aliased and tb.lower() in aliased]
    parent = {t.lower(): t.lower() for t in tables}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    cyclic = False
    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra == rb:
            cyclic = True
        else:
            parent[ra] = rb
    if cyclic:
        tags.add("cyclic_join")
    return sorted(tags)


def load_main_queries():
    """146 запросов: true_card||query (истина полного дампа, не нашего снимка)."""
    path = os.path.join(SRC, "stats_CEB.sql")
    out = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            card, q = line.split("||", 1)
            out.append({"lineno": i, "truth_full_dump": int(card), "sql": q})
    return out


def load_subplan_queries():
    """2603 подплановых запроса: query;||id."""
    path = os.path.join(SRC, "sub_plan_queries", "stats_CEB_sub_queries.sql")
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            q, sid = line.rsplit("||", 1)
            out.append({"subplan_id": int(sid), "sql": q})
    return out


def load_single_table_queries():
    """632 одно-табличных: query;||template_id||truth_full_dump."""
    path = os.path.join(SRC, "sub_plan_queries", "stats_CEB_single_table_sub_query.sql")
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            q, tpl, card = line.rsplit("||", 2)
            out.append({"template_id": int(tpl), "truth_full_dump": int(card),
                        "sql": q})
    return out


def write_suite(suite: str, items: list[dict]):
    """items: dict(id, sql, manifest_extra...). Пишет original/, ported/, манифест."""
    odir = os.path.join(QDIR, suite, "original")
    os.makedirs(odir, exist_ok=True)
    manifest = []
    for it in items:
        qid = it["id"]
        with open(os.path.join(odir, f"{qid}.sql"), "w", encoding="utf-8") as f:
            f.write(it["sql_orig"])
        ported, notes = port_sql(it["sql_orig"])
        with open(os.path.join(QDIR, suite, f"{qid}.sql"), "w",
                  encoding="utf-8") as f:
            f.write(ported + "\n")
        tables = extract_tables(ported)
        amap = extract_alias_map(ported)
        joins = join_pairs_with_tables(ported, amap)
        entry = {
            "id": qid,
            "suite": suite,
            "db": "stats",
            "index_config": ["pk", "pk_fk"],
            "template": it.get("template") or template_of(ported),
            "tables": len(tables),
            "table_list": sorted(tables),
            "tags": tags_of(ported, tables, joins),
            "deterministic": True,
            "float_tolerance": None,
            "subplan_scope": "inner_only",
            "result": it.get("result"),
            "port_notes": "; ".join(notes) if notes else None,
        }
        entry.update({k: v for k, v in it.items() if k.startswith("truth_")})
        manifest.append(entry)
    os.makedirs(MANIFEST_DIR, exist_ok=True)
    import yaml
    path = os.path.join(MANIFEST_DIR, f"{suite}.yaml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(manifest, f, allow_unicode=True, sort_keys=False)
    print(f"{suite}: {len(manifest)} queries -> {path}")
    return manifest


def main():
    mains = load_main_queries()
    subs = load_subplan_queries()
    singles = load_single_table_queries()
    print(f"main={len(mains)} subplans={len(subs)} singles={len(singles)}")

    write_suite("stats-ceb", [{
        "id": f"stats_ceb_{m['lineno']:03d}",
        "sql_orig": m["sql"],
        "truth_full_dump": m["truth_full_dump"],
    } for m in mains])

    write_suite("stats-ceb-subplans", [{
        "id": f"sp_{i:04d}",           # id в файле циклически повторяется по группам
        "subplan_id": s["subplan_id"],  # исходный индекс внутри группы
        "sql_orig": s["sql"],
    } for i, s in enumerate(subs)])

    write_suite("stats-ceb-single", [{
        "id": f"st_{t['template_id']:03d}_{i:03d}",
        "sql_orig": t["sql"],
        "template": f"single_{t['template_id']:03d}",
        "truth_full_dump": t["truth_full_dump"],
    } for i, t in enumerate(singles)])


if __name__ == "__main__":
    main()
