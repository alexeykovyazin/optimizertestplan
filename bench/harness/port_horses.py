r"""Манифест сюиты horses-fdb.

Сюита написана вручную под Firebird: запросы лежат в bench/queries/horses-fdb/
(horses_fdb_NN.sql) и портирования не требуют. Скрипт только строит
bench/manifest/horses-fdb.yaml по этим файлам (формат - как у остальных сюит).

База: horses.fdb (закрытая, публично не распространяется; golden лежит только
на стенде, см. bench/datasets/horses/README.md). В репозиторий идут только
тексты запросов и манифест - без DDL, данных и строк результатов.

Запуск: python bench/harness/port_horses.py
"""
from __future__ import annotations

import glob
import hashlib
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SUITE = "horses-fdb"
QDIR = os.path.join(ROOT, "bench", "queries", SUITE)
MANIFEST = os.path.join(ROOT, "bench", "manifest", SUITE + ".yaml")

# Что проверяет каждый запрос. 01 - запрос из отчёта о дефекте, остальные -
# его варианты: они отделяют конструкцию, на которой план портится.
NOTES = {
    1: "запрос из отчёта: LATERAL с оконной функцией и FETCH FIRST, затем LEFT JOIN COVER",
    2: "контроль: только HORSE LEFT JOIN COVER",
    3: "только LATERAL, без COVER",
    4: "COVER присоединена до LATERAL",
    5: "как 01, но COVER через INNER JOIN",
    6: "LATERAL без оконной функции (первая строка REGISTRATION), затем LEFT JOIN COVER",
    7: "LATERAL с агрегатом MIN без GROUP BY, затем LEFT JOIN COVER",
    8: "обычная производная таблица с GROUP BY вместо LATERAL, затем LEFT JOIN COVER",
}


def extract_tables(sql: str) -> list[str]:
    # "IS DISTINCT FROM x" - не источник строк
    tbls = re.findall(r"(?<!distinct )\b(?:from|join)\s+(\w+)", sql, re.I)
    return sorted({t.lower() for t in tbls if t.lower() not in ("select", "lateral")})


def template_of(sql: str) -> str:
    t = re.sub(r"'[^']*'", "?", sql)
    t = re.sub(r"\b\d+\b", "?", t)
    t = re.sub(r"\s+", " ", t).strip().lower()
    return hashlib.md5(t.encode()).hexdigest()[:8]


def tags_of(sql: str) -> list[str]:
    tags = set()
    if re.search(r"\b(sum|count|avg|min|max)\s*\(", sql, re.I):
        tags.add("aggregate")
    if re.search(r"\bleft\s+(outer\s+)?join\b", sql, re.I):
        tags.add("outer_join")
    if re.search(r"\blateral\b", sql, re.I):
        tags.add("lateral")
    if re.search(r"\bover\s*\(", sql, re.I):
        tags.add("window")
    if re.search(r"\bfetch\s+first\b", sql, re.I):
        tags.add("first_rows")
    if re.search(r"\bgroup\s+by\b", sql, re.I):
        tags.add("group_by")
    if re.search(r"\border\s+by\b", sql, re.I):
        tags.add("order_by")
    return sorted(tags)


def main():
    import yaml
    manifest = []
    for path in sorted(glob.glob(os.path.join(QDIR, "horses_fdb_*.sql"))):
        qid = os.path.splitext(os.path.basename(path))[0]
        n = int(qid.rsplit("_", 1)[1])
        sql = open(path, encoding="utf-8").read()
        tables = extract_tables(sql)
        manifest.append({
            "id": qid,
            "suite": SUITE,
            "db": "horses",
            "index_config": ["pk", "fk"],
            "template": template_of(sql),
            "tables": len(tables),
            "table_list": tables,
            "tags": tags_of(sql),
            "deterministic": True,
            "float_tolerance": None,
            "subplan_scope": None,
            "result": None,
            "port_notes": NOTES.get(n),
        })
    with open(MANIFEST, "w", encoding="utf-8") as f:
        yaml.safe_dump(manifest, f, allow_unicode=True, sort_keys=False)
    print(f"{SUITE}: {len(manifest)} queries -> {MANIFEST}")


if __name__ == "__main__":
    main()
