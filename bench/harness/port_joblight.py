"""Портирование workload'ов learnedcardinalities (Kipf et al. 2018) под
Firebird — job-light (70), scale (500), synthetic (5000), план §3.1.2.

Источник S0: github.com/andreaskipf/learnedcardinalities (MIT), файлы
workloads/{job-light,scale,synthetic}.sql + одноимённые .csv с истинными
кардиньностями (последнее поле строки, формат tables#joins#predicates#card).
Данные: тот же IMDb-золотой снимок, что и JOB — новых загрузок не нужно.
Сверка схемы на S0: используются только 6 таблиц и 10 числовых столбцов,
все присутствуют в gen_ddl.py; алиасы ci/mc/mi/mi_idx/mk/t не зарезервированы.

Диалект PG в этих workload'ах минимальный (запятые-соединения, числовые
предикаты =/>/<, только AND, COUNT(*)), поэтому порт сводится к снятию
хвостовых ';'. Отклонения (зарезервированные слова, нечисловые литералы,
неизвестные таблицы) — жёсткий стоп, чтобы не пропустить молча.

Результат: bench/queries/{job-light,scale,synthetic}/*.sql + манифесты
bench/manifest/{job-light,scale,synthetic}.yaml + sources в
bench/manifest/query-sets-sources.yaml.
"""
from __future__ import annotations

import hashlib
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "third_party", "learnedcardinalities", "workloads")
QBASE = os.path.join(ROOT, "bench", "queries")
MANIFEST_DIR = os.path.join(ROOT, "bench", "manifest")

SUITES = {
    # suite: (файл, шаблон имени qid, паддинг)
    "job-light": ("job-light.sql", "job_light_{:03d}", 3),
    "scale": ("scale.sql", "scale_{:03d}", 3),
    "synthetic": ("synthetic.sql", "synthetic_{:04d}", 4),
}

# Схема IMDb-снимка (gen_ddl.py): допустимые таблицы и столбцы workload'ов
KNOWN_TABLES = {"cast_info", "movie_companies", "movie_info",
                "movie_info_idx", "movie_keyword", "title"}
KNOWN_COLS = {"id", "movie_id", "info_type_id", "company_type_id",
              "production_year", "keyword_id", "role_id", "kind_id",
              "company_id", "person_id"}


def split_queries(text: str) -> list[str]:
    qs = [q.strip() for q in text.split(";") if q.strip()]
    return qs


def port_sql(sql: str) -> tuple[str, list[str]]:
    notes = []
    out = sql.strip().rstrip(";").rstrip() + "\n"
    return out, notes


def check_query(sql: str) -> None:
    frm = re.search(r"\bFROM\b(.*?)(?:\bWHERE\b|$)", sql, re.I | re.S).group(1)
    for tbl, alias in re.findall(r"\b(\w+)\s+(\w+)\b", frm):
        if tbl.lower() not in KNOWN_TABLES:
            raise ValueError(f"неизвестная таблица {tbl!r}: {sql[:120]}")
    for col in re.findall(r"\b\w+\.(\w+)\b", sql):
        if col.lower() not in KNOWN_COLS:
            raise ValueError(f"неизвестный столбец {col!r}: {sql[:120]}")
    if re.search(r"'", sql):
        raise ValueError(f"строковый литерал не ожидался: {sql[:120]}")
    for kw in ("OR", "LIKE", "IN", "BETWEEN", "JOIN", "LIMIT", "GROUP",
               "ORDER", "EXISTS", "NOT", "CAST", "DISTINCT"):
        if re.search(rf"\b{kw}\b", sql, re.I):
            raise ValueError(f"неожиданное ключевое слово {kw}: {sql[:120]}")


def extract_tables(sql: str) -> list[str]:
    frm = re.search(r"\bFROM\b(.*?)(?:\bWHERE\b|$)", sql, re.I | re.S).group(1)
    return [t for t, _ in re.findall(r"\b(\w+)\s+(\w+)\b", frm, re.I)]


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
    tags = {"aggregate"}  # все запросы workload'а — SELECT COUNT(*)
    if re.search(r"\b\w+\.\w+\s*(>=|<=|>|<)\b", sql, re.I):
        tags.add("range_predicate")
    has_fk_fk = any(ca.lower() != "id" and cb.lower() != "id"
                    for _, ca, _, cb in join_pairs)
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


def true_cardinality(card_lines: list[str], idx: int) -> int:
    return int(card_lines[idx - 1].strip().rsplit("#", 1)[-1])


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def main(suites: list[str] | None = None):
    import yaml
    sources = []
    src_yaml = os.path.join(MANIFEST_DIR, "query-sets-sources.yaml")
    if os.path.exists(src_yaml):
        sources = yaml.safe_load(open(src_yaml, encoding="utf-8")) or []
    for suite, (fname, qid_tpl, _pad) in SUITES.items():
        if suites and suite not in suites:
            continue
        src_path = os.path.join(SRC, fname)
        text = open(src_path, encoding="utf-8").read()
        queries = split_queries(text)
        csv_path = src_path.replace(".sql", ".csv")
        n_csv = sum(1 for _ in open(csv_path, encoding="utf-8"))
        assert len(queries) == n_csv, \
            f"{suite}: {len(queries)} запросов, но {n_csv} строк CSV"
        qdir = os.path.join(QBASE, suite)
        os.makedirs(qdir, exist_ok=True)
        card_lines = open(csv_path, encoding="utf-8").read().splitlines()
        manifest = []
        n_notes = 0
        t_compile = 0
        for i, raw in enumerate(queries, 1):
            check_query(raw)
            ported, notes = port_sql(raw)
            qid = qid_tpl.format(i)
            with open(os.path.join(qdir, f"{qid}.sql"), "w",
                      encoding="utf-8") as f:
                f.write(ported)
            amap = {a.lower(): t for t, a in re.findall(
                r"\b(\w+)\s+(\w+)\b",
                re.search(r"\bFROM\b(.*?)(?:\bWHERE\b|$)", ported,
                          re.I | re.S).group(1), re.I)}
            tables = extract_tables(ported)
            joins = join_pairs_with_tables(ported, amap)
            manifest.append({
                "id": qid,
                "suite": suite,
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
                "true_cardinality": true_cardinality(card_lines, i),
            })
            n_notes += 1 if notes else 0
        with open(os.path.join(MANIFEST_DIR, f"{suite}.yaml"), "w",
                  encoding="utf-8") as f:
            yaml.safe_dump(manifest, f, allow_unicode=True, sort_keys=False)
        max_tables = max(m["tables"] for m in manifest)
        n_templates = len({m["template"] for m in manifest})
        print(f"{suite}: {len(manifest)} запросов, шаблонов {n_templates}, "
              f"макс. таблиц {max_tables}, port_notes {n_notes} -> {qdir}")
        src_rec = {"set": suite, "source_url":
                   "https://github.com/andreaskipf/learnedcardinalities "
                   "(workloads/)", "license": "MIT",
                   "paper": "Kipf et al., Learned Cardinalities: Estimating "
                            "Correlated Joins with Deep Learning, 2018 "
                            "(arXiv:1809.00677)",
                   "files": {fname: file_sha256(src_path),
                             os.path.basename(csv_path):
                                 file_sha256(csv_path)},
                   "queries": len(manifest),
                   "downloaded_at": "2026-10-10",
                   "db": "imdb (golden imdb_fb5.fdb — существующий снимок, "
                         "загрузка не требуется)"}
        sources = [s for s in sources if s.get("set") != suite] + [src_rec]
        with open(src_yaml, "w", encoding="utf-8") as f:
            yaml.safe_dump(sources, f, allow_unicode=True, sort_keys=False)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
