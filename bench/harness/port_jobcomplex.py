"""Портирование корпуса JOB-Complex (Wehrstein et al., AIDB'25) под Firebird.

Источник S0: github.com/DataManagementLab/JOB-Complex (репо без LICENSE —
зафиксировано; 30 SQL-запросов, ~6000 планов-эталонов в бенчмарке авторов
в FB не исполняются и не портируются). Данные: тот же IMDb-золотой снимок,
что и JOB — новая загрузка не нужна.

Диалект: запятые-соединения + LIKE/IN(макс. 10)/BETWEEN/OR/!=/IS NULL,
строковые литералы <=27 байт (чанкование не нужно), CAST в SQL нет
('CAST' попадался только в литералах). Правила порта:
  - alias `at` -> "at"            (AT — зарезервированное слово FB; 4 запроса:
                                   5, 13, 15, 18 — алиас aka_title; в строковых
                                   литералах \bat\b не встречается);
  - MIN(<a>.info) по BLOB-колонкам movie_info.info / person_info.info ->
    MIN(SUBSTRING(<a>.info FROM 1 FOR 8000)) — как в JOB (match_truncated);
  - BLOB-предикаты (= / IN / LIKE / !=) по info: prepare на FB5 проходит
    (проверено), если на S7 будет runtime-ошибка IN по BLOB — включить
    правило OR-цепочки равенств;
  - хвостовые ';' снимаются.

Отклонения фиксируются в port_notes манифеста.
"""
from __future__ import annotations

import hashlib
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "third_party", "JOB-Complex", "JOB-Complex.sql")
QDIR = os.path.join(ROOT, "bench", "queries", "job-complex")
MANIFEST_DIR = os.path.join(ROOT, "bench", "manifest")

TRUNC = 8000


def extract_alias_map(sql: str) -> dict[str, str]:
    frm = re.search(r"\bFROM\b(.*?)(?:\bWHERE\b|$)", sql, re.I | re.S).group(1)
    return {a.lower(): t for t, a in
            re.findall(r"\b(\w+)\s+as\s+(\w+)", frm, re.I)}


def port_sql(sql: str, amap: dict) -> tuple[str, list[str]]:
    notes = []
    out = sql.strip()

    # alias `at` -> "at" (AT reserved; в литералах не встречается — проверено)
    out, n1 = re.subn(r"\bat\b", '"at"', out)
    if n1:
        notes.append('at -> "at" (AT reserved word in Firebird)')

    # MIN(blob.info) -> MIN(SUBSTRING(...)) — как в JOB
    def sub_min(m):
        alias, col = m.group(1), m.group(2)
        if (amap or {}).get(alias.lower(), "") in ("movie_info", "person_info"):
            return f"MIN(SUBSTRING({alias}.{col} FROM 1 FOR {TRUNC}))"
        return m.group(0)

    out, n2 = re.subn(r"\bMIN\((\w+)\.(info)\)", sub_min, out)
    if n2:
        notes.append(f"MIN({n2}x blob.info) -> MIN(SUBSTRING(... FROM 1 "
                     f"FOR {TRUNC})) (movie_info/person_info are BLOB TEXT)")

    out = out.rstrip(";").rstrip() + "\n"
    return out, notes


def extract_tables(sql: str) -> list[str]:
    frm = re.search(r"\bFROM\b(.*?)(?:\bWHERE\b|$)", sql, re.I | re.S).group(1)
    return [t for t, _ in re.findall(r"\b(\w+)\s+as\s+(\w+)", frm, re.I)]


def join_pairs_with_tables(sql: str, amap: dict):
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
    tags = {"aggregate"}
    if re.search(r"\b\w+\.\w+\s*(>=|<=|>|<|BETWEEN)\b", sql, re.I):
        tags.add("range_predicate")
    if re.search(r"\bLIKE\b", sql, re.I):
        tags.add("like_predicate")
    if re.search(r"\bOR\b", sql, re.I):
        tags.add("or_predicate")
    has_fk_fk = any(ca.lower() != "id" and cb.lower() != "id"
                    for _, ca, _, cb in join_pairs)
    if has_fk_fk:
        tags.add("fk_fk_join")
    if re.search(r"\b\w+\.(name|title|note|info)\s*=\s*\w+\.", sql, re.I):
        tags.add("string_join")
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
    os.makedirs(QDIR, exist_ok=True)
    text = open(SRC, encoding="utf-8").read()
    queries = [q.strip() for q in text.split(";") if q.strip()]
    assert len(queries) == 30, f"ожидалось 30 запросов, получено {len(queries)}"
    manifest = []
    for i, raw in enumerate(queries, 1):
        qid = f"job_complex_{i:02d}"
        amap = extract_alias_map(raw)
        ported, notes = port_sql(raw, amap)
        with open(os.path.join(QDIR, f"{qid}.sql"), "w",
                  encoding="utf-8") as f:
            f.write(ported)
        # таблицы/джойны — из raw: кавычки "at" в портированном ломают
        # извлечение алиасов регэкспом
        tables = extract_tables(raw)
        joins = join_pairs_with_tables(raw, amap)
        manifest.append({
            "id": qid,
            "suite": "job-complex",
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
    with open(os.path.join(MANIFEST_DIR, "job-complex.yaml"), "w",
              encoding="utf-8") as f:
        yaml.safe_dump(manifest, f, allow_unicode=True, sort_keys=False)
    n_notes = sum(1 for m in manifest if m["port_notes"])
    max_t = max(m["tables"] for m in manifest)
    print(f"job-complex: {len(manifest)} запросов ({n_notes} с port_notes), "
          f"макс. таблиц {max_t} -> {QDIR}")


if __name__ == "__main__":
    main()
