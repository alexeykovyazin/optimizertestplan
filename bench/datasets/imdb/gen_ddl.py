"""Генерация Firebird DDL для IMDb (JOB) из схемы PG + фактических длин текста.

Правила типов:
  - integer -> INTEGER;
  - character varying(n) -> VARCHAR(n)  (данные <= n гарантированы схемой PG);
  - text -> VARCHAR(округлённый фактический максимум) — по textlen с dellg15;
  - text длиннее максимума Firebird VARCHAR UTF8 (8191 символов):
    movie_info.info (19793) и person_info.info (55656) -> BLOB SUB_TYPE TEXT
    (в JOB-запросах используются только в LIKE / = / IS NOT NULL и в
    выходных агрегатах MIN(); агрегаты портируются через SUBSTRING).

PRIMARY KEY и вторичные индексы (fkindexes.sql — точная конфигурация PG)
создаются ПОСЛЕ загрузки отдельными скриптами: массовая сборка индекса
быстрее пошагового сопровождения при вставке 70 млн строк.

Выход: ddl_tables.sql, ddl_constraints.sql, ddl_indexes.sql, column_types.json
"""
from __future__ import annotations

import json
import math
import os

HERE = os.path.abspath(os.path.dirname(__file__))
OUT = os.path.join(HERE, "generated")

TABLES = {  # порядок: маленькие справочники -> большие факты (для загрузки)
    "kind_type": ["id INTEGER NOT NULL", "kind VARCHAR(15) NOT NULL"],
    "comp_cast_type": ["id INTEGER NOT NULL", "kind VARCHAR(32) NOT NULL"],
    "company_type": ["id INTEGER NOT NULL", "kind VARCHAR(32) NOT NULL"],
    "info_type": ["id INTEGER NOT NULL", "info VARCHAR(32) NOT NULL"],
    "link_type": ["id INTEGER NOT NULL", "link VARCHAR(32) NOT NULL"],
    "role_type": ["id INTEGER NOT NULL", "role VARCHAR(32) NOT NULL"],
    "keyword": ["id INTEGER NOT NULL", "keyword VARCHAR(96) NOT NULL",
                "phonetic_code VARCHAR(5)"],
    "aka_name": ["id INTEGER NOT NULL", "person_id INTEGER NOT NULL",
                 "name VARCHAR(256) NOT NULL", "imdb_index VARCHAR(12)",
                 "name_pcode_cf VARCHAR(5)", "name_pcode_nf VARCHAR(5)",
                 "surname_pcode VARCHAR(5)", "md5sum VARCHAR(32)"],
    "aka_title": ["id INTEGER NOT NULL", "movie_id INTEGER NOT NULL",
                  "title VARCHAR(640) NOT NULL", "imdb_index VARCHAR(12)",
                  "kind_id INTEGER NOT NULL", "production_year INTEGER",
                  "phonetic_code VARCHAR(5)", "episode_of_id INTEGER",
                  "season_nr INTEGER", "episode_nr INTEGER",
                  "note VARCHAR(96)", "md5sum VARCHAR(32)"],
    "cast_info": ["id INTEGER NOT NULL", "person_id INTEGER NOT NULL",
                  "movie_id INTEGER NOT NULL", "person_role_id INTEGER",
                  "note VARCHAR(1024)", "nr_order INTEGER",
                  "role_id INTEGER NOT NULL"],
    "char_name": ["id INTEGER NOT NULL", "name VARCHAR(512) NOT NULL",
                  "imdb_index VARCHAR(12)", "imdb_id INTEGER",
                  "name_pcode_nf VARCHAR(5)", "surname_pcode VARCHAR(5)",
                  "md5sum VARCHAR(32)"],
    "company_name": ["id INTEGER NOT NULL", "name VARCHAR(192) NOT NULL",
                     "country_code VARCHAR(255)", "imdb_id INTEGER",
                     "name_pcode_nf VARCHAR(5)", "name_pcode_sf VARCHAR(5)",
                     "md5sum VARCHAR(32)"],
    "complete_cast": ["id INTEGER NOT NULL", "movie_id INTEGER",
                      "subject_id INTEGER NOT NULL", "status_id INTEGER NOT NULL"],
    "movie_companies": ["id INTEGER NOT NULL", "movie_id INTEGER NOT NULL",
                        "company_id INTEGER NOT NULL",
                        "company_type_id INTEGER NOT NULL",
                        "note VARCHAR(256)"],
    "movie_info": ["id INTEGER NOT NULL", "movie_id INTEGER NOT NULL",
                   "info_type_id INTEGER NOT NULL",
                   "info BLOB SUB_TYPE TEXT NOT NULL", "note VARCHAR(512)"],
    "movie_info_idx": ["id INTEGER NOT NULL", "movie_id INTEGER NOT NULL",
                       "info_type_id INTEGER NOT NULL",
                       "info VARCHAR(16) NOT NULL", "note VARCHAR(64)"],
    "movie_keyword": ["id INTEGER NOT NULL", "movie_id INTEGER NOT NULL",
                      "keyword_id INTEGER NOT NULL"],
    "movie_link": ["id INTEGER NOT NULL", "movie_id INTEGER NOT NULL",
                   "linked_movie_id INTEGER NOT NULL",
                   "link_type_id INTEGER NOT NULL"],
    "name": ["id INTEGER NOT NULL", "name VARCHAR(128) NOT NULL",
             "imdb_index VARCHAR(12)", "imdb_id INTEGER", "gender VARCHAR(1)",
             "name_pcode_cf VARCHAR(5)", "name_pcode_nf VARCHAR(5)",
             "surname_pcode VARCHAR(5)", "md5sum VARCHAR(32)"],
    "person_info": ["id INTEGER NOT NULL", "person_id INTEGER NOT NULL",
                    "info_type_id INTEGER NOT NULL",
                    "info BLOB SUB_TYPE TEXT NOT NULL", "note VARCHAR(512)"],
    "title": ["id INTEGER NOT NULL", "title VARCHAR(384) NOT NULL",
              "imdb_index VARCHAR(12)", "kind_id INTEGER NOT NULL",
              "production_year INTEGER", "imdb_id INTEGER",
              "phonetic_code VARCHAR(5)", "episode_of_id INTEGER",
              "season_nr INTEGER", "episode_nr INTEGER",
              "series_years VARCHAR(49)", "md5sum VARCHAR(32)"],
}

# вторичные индексы — дословно fkindexes.sql (конфигурация индексов PG)
INDEXES = [
    ("company_id_movie_companies", "movie_companies", "company_id"),
    ("company_type_id_movie_companies", "movie_companies", "company_type_id"),
    ("info_type_id_movie_info_idx", "movie_info_idx", "info_type_id"),
    ("info_type_id_movie_info", "movie_info", "info_type_id"),
    ("info_type_id_person_info", "person_info", "info_type_id"),
    ("keyword_id_movie_keyword", "movie_keyword", "keyword_id"),
    ("kind_id_aka_title", "aka_title", "kind_id"),
    ("kind_id_title", "title", "kind_id"),
    ("linked_movie_id_movie_link", "movie_link", "linked_movie_id"),
    ("link_type_id_movie_link", "movie_link", "link_type_id"),
    ("movie_id_aka_title", "aka_title", "movie_id"),
    ("movie_id_cast_info", "cast_info", "movie_id"),
    ("movie_id_complete_cast", "complete_cast", "movie_id"),
    ("movie_id_movie_companies", "movie_companies", "movie_id"),
    ("movie_id_movie_info_idx", "movie_info_idx", "movie_id"),
    ("movie_id_movie_keyword", "movie_keyword", "movie_id"),
    ("movie_id_movie_link", "movie_link", "movie_id"),
    ("movie_id_movie_info", "movie_info", "movie_id"),
    ("person_id_aka_name", "aka_name", "person_id"),
    ("person_id_cast_info", "cast_info", "person_id"),
    ("person_id_person_info", "person_info", "person_id"),
    ("person_role_id_cast_info", "cast_info", "person_role_id"),
    ("role_id_cast_info", "cast_info", "role_id"),
]


def verify_against_textlen():
    """Сверить объявленные VARCHAR с фактическими максимумами textlen."""
    path = os.path.join(HERE, os.pardir, os.pardir, "third_party", "imdb-port",
                        "out", "textlen_parsed.json")
    if not os.path.exists(path):
        return  # textlen недоступен — DDL зафиксирован константами выше
    sizes = json.load(open(path, encoding="utf-8"))
    bad = []
    for t, cols in TABLES.items():
        for cdef in cols:
            name, typ = cdef.split(" ", 1)
            if name in sizes.get(t, {}):
                ml, _ = sizes[t][name]
                if typ.startswith("VARCHAR(") and ml:
                    declared = int(typ[len("VARCHAR("):-1])
                    if ml > declared:
                        bad.append((t, name, ml, declared))
    if bad:
        raise SystemExit(f"VARCHAR меньше фактических данных: {bad}")


def main():
    os.makedirs(OUT, exist_ok=True)
    verify_against_textlen()

    with open(os.path.join(OUT, "ddl_tables.sql"), "w", encoding="utf-8") as f:
        for t, cols in TABLES.items():
            f.write(f"CREATE TABLE {t} (\n  " + ",\n  ".join(cols) + "\n);\n\n")

    with open(os.path.join(OUT, "ddl_constraints.sql"), "w", encoding="utf-8") as f:
        for t in TABLES:
            f.write(f"ALTER TABLE {t} ADD CONSTRAINT {t}_pk PRIMARY KEY (id);\n")

    with open(os.path.join(OUT, "ddl_indexes.sql"), "w", encoding="utf-8") as f:
        for name, t, col in INDEXES:
            f.write(f"CREATE INDEX {name.upper()} ON {t} ({col});\n")
        f.write("\n")
        for name, t, _col in INDEXES:
            f.write(f"SET STATISTICS INDEX {name.upper()};\n")

    ctypes = {}
    for t, cols in TABLES.items():
        d = {}
        for cdef in cols:
            name, typ = cdef.split(" ", 1)
            base = typ.split()[0].split(" NOT")[0]
            if base.startswith("BLOB"):
                d[name] = "blob"
            elif base == "INTEGER":
                d[name] = "int"
            else:
                d[name] = "str"
        ctypes[t] = d
    with open(os.path.join(OUT, "column_types.json"), "w", encoding="utf-8") as f:
        json.dump(ctypes, f, indent=1)

    n = sum(len(v) for v in TABLES.values())
    print(f"tables={len(TABLES)} columns={n} indexes={len(INDEXES)} -> {OUT}")


if __name__ == "__main__":
    main()
