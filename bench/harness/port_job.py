"""Портирование корпуса JOB (113 запросов IMDb) под Firebird — раздел 4.5.

Диалект PG в JOB минимальный (запятые-соединения, LIKE/IN/BETWEEN), поэтому
правил немного:
  - псевдоним `at` -> "at"        (AT — зарезервированное слово FB,
                                   встречается в 15a–15d как alias aka_title);
  - `AS character` -> `AS "character"` (CHARACTER — зарезервированное слово,
                                   выходной псевдоним в 10b/10c);
  - MIN(<a>.info) по BLOB-колонкам movie_info.info / person_info.info ->
    MIN(SUBSTRING(<a>.info FROM 1 FOR 8000))
    (обе колонки длиннее максимума FB VARCHAR UTF8 (8191), поэтому в FB это
    BLOB SUB_TYPE TEXT; сравнения LIKE/= на BLOB допустимы, а MIN — нет;
    усечение влияет только на выводимое значение, не на план);
  - хвостовые ';' снимаются.

Примечание: `rt.role` (ROLE) НЕ требует кавычек — ROLE в FB 5 не-reserved
для ссылок на столбцы; нецитированный идентификатор складывается в верхний
регистр и совпадает со столбцом ROLE (проверено prepare на FB).

Отклонения фиксируются в port_notes манифеста.
Оригиналы сохраняются в queries/job/original/.
"""
from __future__ import annotations

import hashlib
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "third_party", "JOB-queries")
QDIR = os.path.join(ROOT, "bench", "queries", "job")
MANIFEST_DIR = os.path.join(ROOT, "bench", "manifest")

# JOB: у всех таблиц PK — id
TABLES_PK = {t: "id" for t in [
    "aka_name", "aka_title", "cast_info", "char_name", "comp_cast_type",
    "company_name", "company_type", "complete_cast", "info_type", "keyword",
    "kind_type", "link_type", "movie_companies", "movie_info",
    "movie_info_idx", "movie_keyword", "movie_link", "name", "person_info",
    "role_type", "title"]}

BLOB_INFO_COLS = {"mi": "movie_info", "miidx": "movie_info_idx",
                  "pi": "person_info"}  # alias -> таблица (проверяется ниже)
TRUNC = 8000


def port_sql(sql: str, alias_map: dict) -> tuple[str, list[str]]:
    notes = []
    out = sql.strip()
    # alias `at` -> "at" (AT reserved); в строковых литералах 'at' не
    # встречается (проверено по корпусу), \b не задевает часть слова
    out, n1 = re.subn(r"\bat\b", '"at"', out)
    if n1:
        notes.append("at -> \"at\" (AT reserved word in Firebird)")
    out, n2 = re.subn(r"\bAS character\b", 'AS "character"', out,
                      flags=re.I)
    if n2:
        notes.append('AS character -> AS "character" (reserved word)')

    def sub_min(m):
        alias, col = m.group(1), m.group(2)
        tbl = (alias_map or {}).get(alias.lower(), "")
        if tbl in ("movie_info", "person_info"):
            return f"MIN(SUBSTRING({alias}.{col} FROM 1 FOR {TRUNC}))"
        return m.group(0)

    out, n3 = re.subn(r"\bMIN\((\w+)\.(info)\)", sub_min, out)
    if n3:
        notes.append(f"MIN({n3}x blob.info) -> MIN(SUBSTRING(... FROM 1 "
                     f"FOR {TRUNC})) (movie_info/person_info are BLOB TEXT)")
    out = out.rstrip(";").rstrip() + "\n"
    return out, notes


def extract_alias_map(sql: str) -> dict[str, str]:
    frm = re.search(r"\bFROM\b(.*?)(?:\bWHERE\b|$)", sql, re.I | re.S).group(1)
    return {a.lower(): t for t, a in re.findall(r"\b(\w+)\s+as\s+(\w+)", frm, re.I)}


def extract_tables(sql: str) -> list[str]:
    frm = re.search(r"\bFROM\b(.*?)(?:\bWHERE\b|$)", sql, re.I | re.S).group(1)
    return [t for t, _ in re.findall(r"\b(\w+)\s+as\s+(\w+)", frm, re.I)]


def join_pairs_with_tables(sql: str, amap: dict) -> list[tuple[str, str, str, str]]:
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
    tags = {"aggregate"}  # JOB: все запросы с агрегатами (MIN/COUNT)
    if re.search(r"\b\w+\.\w+\s*(>=|<=|>|<|BETWEEN)\b", sql, re.I):
        tags.add("range_predicate")
    has_fk_fk = False
    for ta, ca, tb, cb in join_pairs:
        a_pk = ca.lower() == "id"
        b_pk = cb.lower() == "id"
        if not a_pk and not b_pk:
            has_fk_fk = True
    if has_fk_fk:
        tags.add("fk_fk_join")
    if len(tables) >= 8:
        tags.add("many_tables")
    edges = [(ta.lower(), tb.lower()) for ta, ca, tb, cb in join_pairs]
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


def main():
    import yaml
    os.makedirs(os.path.join(QDIR, "original"), exist_ok=True)
    os.makedirs(MANIFEST_DIR, exist_ok=True)
    qids = sorted(f[:-4] for f in os.listdir(SRC)
                  if re.fullmatch(r"\d+[a-z]\.sql", f))
    manifest = []
    for qid in qids:
        raw = open(os.path.join(SRC, f"{qid}.sql"), encoding="utf-8").read()
        amap = extract_alias_map(raw)
        ported, notes = port_sql(raw, amap)
        with open(os.path.join(QDIR, "original", f"{qid}.sql"), "w",
                  encoding="utf-8") as f:
            f.write(raw)
        with open(os.path.join(QDIR, f"{qid}.sql"), "w", encoding="utf-8") as f:
            f.write(ported)
        tables = extract_tables(ported)
        joins = join_pairs_with_tables(ported, amap)
        manifest.append({
            "id": f"job_{qid}",
            "suite": "job",
            "db": "imdb",
            "index_config": ["pk"],
            "template": template_of(ported),
            "tables": len(tables),
            "table_list": sorted(set(tables)),
            "tags": tags_of(ported, tables, joins),
            "deterministic": True,
            "float_tolerance": None,
            "subplan_scope": None,
            "result": None,
            "port_notes": "; ".join(notes) if notes else None,
        })
    with open(os.path.join(MANIFEST_DIR, "job.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(manifest, f, allow_unicode=True, sort_keys=False)
    n_ported = sum(1 for m in manifest if m["port_notes"])
    print(f"job: {len(manifest)} queries ({n_ported} with port_notes) -> "
          f"{QDIR}")


if __name__ == "__main__":
    main()
