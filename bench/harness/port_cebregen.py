"""Портирование восстановленного корпуса CEB-IMDb (ceb-imdb-regen) под FB.

Источник S0: learnedsystems/CEB (MIT) — оригинальные pickle'ы CEB-IMDb
недоступны (все Dropbox-ссылки мертвы, 404, проверено 2026-10-11), запросы
восстановлены штатным генератором репо из выложенных toml-шаблонов
(8 групп IMDb-шаблонов: 3b 7a 8a 9a 9b 10a 11a 11b; параметры — заново,
seed 2112+i; генерация: bench/harness/gen_ceb_imdb.py через PG-эталон
dellg15). ЭТО НЕ опубликованный CEB-IMDb: побайтового совпадения с ним нет,
истина по подпланам оригинала недоступна; корпус валидируется своим
PG-эталоном как все сюиты.

Диалект (по факту генерации): запятые-соединения, ILIKE на строках,
IN-списки строк (<=8), GROUP BY + ORDER BY COUNT(*) DESC, литералы <=21 байт,
только `=`. Правила порта:
  - x ILIKE 'y' -> UPPER(x) LIKE UPPER('y')  — PG-эталон в коллации C
    (ASCII-folding), FB UPPER по ASCII — семантика совпадает на IMDb-данных;
  - хвостовые ';' снимаются, однострочник;
  - BLOB-ключи GROUP BY (главная ловушка FB 5.0.5, 2026-10-11): сортировка
    для группировки ключует BLOB по blob-ID — контентно-равные строки
    несмежны и группы расщепляются (ceb_10a_001: 36 строк вместо 15;
    ceb_10a_002: ненадёжно даже blob-вторым-ключом). Фикс — скрытый первый
    ключ HASH(SUBSTRING(k1) || '#' || SUBSTRING(k2)...) по содержимому ВСЕХ
    ключей + позиционные ссылки (сверено с PG: 10a_001/002, 9a_001 exact).
    SELECT остаётся с голым blob.info (вывод = PG байт-в-байт; максимумы
    movie_info 19 793 / person_info 55 656 байт — SUBSTRING резал бы вывод).

Determinism: ORDER BY COUNT(*) DESC с ничьими даёт разный ПОРЯДОК строк в
PG/FB — canon-сравнение в job_validate сортирует мультимножество, так что
это не мешает; состав строк детерминирован.

Запуск: python bench/harness/port_cebregen.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_JSON = os.path.join(ROOT, "third_party", "CEB", "ceb-imdb-regen.json")
QDIR = os.path.join(ROOT, "bench", "queries", "ceb-imdb-regen")
MANIFEST_DIR = os.path.join(ROOT, "bench", "manifest")

TRUNC = 8000


def extract_alias_map(sql: str) -> dict[str, str]:
    frm = re.search(r"\bFROM\b(.*?)(?:\bWHERE\b|\bGROUP\b|\bORDER\b|$)",
                    sql, re.I | re.S).group(1)
    return {a.lower(): t for t, a in
            re.findall(r"\b(\w+)\s+as\s+(\w+)", frm, re.I)}


def blob_tables(amap: dict) -> set[str]:
    return {"movie_info", "person_info"}


def port_sql(sql: str, amap: dict) -> tuple[str, list[str]]:
    notes = []
    out = " ".join(sql.split()).rstrip(";").strip()

    def blob_aliases():
        return {a.lower() for a, t in (amap or {}).items()
                if t in ("movie_info", "person_info")}

    # MIN(blob.info) -> SUBSTRING (на случай шаблонов с MIN по info)
    def sub_min(m):
        alias, col = m.group(1), m.group(2)
        if (amap or {}).get(alias.lower(), "") in ("movie_info",
                                                   "person_info"):
            return f"MIN(SUBSTRING({alias}.{col} FROM 1 FOR {TRUNC}))"
        return m.group(0)

    out, n0 = re.subn(r"\bMIN\((\w+)\.(info)\)", sub_min, out)
    if n0:
        notes.append(f"MIN({n0}x blob.info) -> MIN(SUBSTRING(...)) "
                     f"(movie_info/person_info are BLOB TEXT; усечение >8000 "
                     f"байт даёт match_truncated)")

    # SELECT остаётся с ГОЛЫМ blob.info: FB читает содержимое целиком,
    # вывод совпадает с PG байт-в-байт (максимумы: movie_info 19 793,
    # person_info 55 656 байт — SUBSTRING порезал бы вывод).

    # GROUP BY поверх BLOB-ключей — ловушка FB 5.0.5 (2026-10-11,
    # ceb_10a_001: 36 строк вместо 15): сортировка для группировки ключует
    # BLOB по blob-ID, контентно-равные строки становятся несмежными и
    # группировка распадается. Группировка корректна, только если ПЕРВЫЙ
    # ключ не blob-производный:
    #   - смешанные ключи: не-blob позиции первыми, blob-позиции после;
    #   - все ключи blob (9a/9b): скрытый первый ключ HASH(SUBSTRING(k1)
    #     || '#' || SUBSTRING(k2)) — сортировка по содержимому; сверено
    #     с PG-эталоном (ceb_9a_001: 10810 = PG).
    # Позиционная форма GROUP BY n обязательна: явное выражение-первый-ключ
    # (даже SUBSTRING) тоже даёт blob-ID сортировку.
    m_sel = re.search(r"\bSELECT\b(.*?)(?=\bFROM\s+[A-Za-z_])", out,
                      re.I | re.S)
    m_gb = re.search(r"\bGROUP BY\b(.*?)(?:\bORDER BY\b|\Z)", out, re.I | re.S)
    if m_sel and m_gb:
        def split_top(s):
            items, depth, cur = [], 0, []
            for ch in s:
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                if ch == "," and depth == 0:
                    items.append("".join(cur).strip())
                    cur = []
                else:
                    cur.append(ch)
            if cur:
                items.append("".join(cur).strip())
            return [i for i in items if i]

        sel_items = split_top(m_sel.group(1))
        gb_items = split_top(m_gb.group(1))
        bl = blob_aliases()

        def is_blob_item(item):
            return any(m.group(1).lower() in bl
                       for m in re.finditer(r"\b(\w+)\.info\b", item))

        positions, all_mapped = [], True
        for it in gb_items:
            pos = next((i + 1 for i, s in enumerate(sel_items)
                        if s.lower() == it.lower()), None)
            if pos is None:
                all_mapped = False
                break
            positions.append(pos)
        if all_mapped and positions:
            blob_flags = [is_blob_item(sel_items[p - 1]) for p in positions]
            if any(blob_flags):
                # единый надёжный фикс (10a_002: reorder недостаточен —
                # FB расщепляет и blob-вторым-ключом): скрытый первый ключ
                # HASH по содержимому ВСЕХ ключей (и не-blob тоже! — иначе
                # все строки с равным blob-значением получают один hash и
                # blob-ID снова разупорядочивает их внутри серии). Парa
                # (hash, ключи): одинаковые ключи -> один hash -> смежная
                # серия только из равных пар -> слияние корректно.
                sub_exps = []
                for p, b in zip(positions, blob_flags):
                    if b:
                        ref = re.search(r"\b(\w+)\.info\b",
                                        sel_items[p - 1]).group(0)
                        sub_exps.append(f"SUBSTRING({ref} FROM 1 FOR {TRUNC})")
                    else:
                        sub_exps.append(f"SUBSTRING({sel_items[p - 1]} "
                                        f"FROM 1 FOR {TRUNC})")
                hidden = "HASH(" + " || '#' || ".join(sub_exps) + ")"
                out = (out[:m_gb.start(1)] + " " + hidden + ", " +
                       ", ".join(str(p) for p in positions) + " " +
                       out[m_gb.end(1):])
                notes.append("GROUP BY c blob-ключами -> скрытый HASH-ключ "
                             "первым (FB 5.0.5: blob ключуется в сортировке "
                             "по blob-ID и расщепляет контентно-равные "
                             "группы даже не первым ключом; HASH по "
                             "содержимому всех ключей восстанавливает "
                             "смежность; сверено с PG)")
            else:
                out = (out[:m_gb.start(1)] + " " +
                       ", ".join(str(p) for p in positions) + " " +
                       out[m_gb.end(1):])
                notes.append("GROUP BY expr -> позиционные ссылки")

    # ILIKE -> UPPER(x) LIKE UPPER(y) — включая перечисления с OR внутри
    out, n1 = re.subn(
        r"(\w+\.\w+)\s+ILIKE\s+('[^']*')",
        lambda m: f"UPPER({m.group(1)}) LIKE UPPER({m.group(2)})",
        out, flags=re.I)
    if n1:
        notes.append(f"ILIKE -> UPPER/LIKE ({n1}x) — PG в коллации C "
                     f"(ASCII folding), эквивалентно FB UPPER на ASCII")

    # alias `at` -> "at" (на случай шаблонов с aka_title)
    out, n2 = re.subn(r"\bat\b", '"at"', out)
    if n2:
        notes.append('at -> "at" (AT reserved word in Firebird)')

    # PG-regex "info — число" (шаблон 7a): x ~ '^(?:[1-9]\d*|0)?(?:\.\d+)?$'
    # -> (x = '' OR x SIMILAR TO '(0|[1-9][0-9]*)([.][0-9]+)?').
    # Семантика совпадает на данных (в movie_info.info нет пустых строк,
    # проверено на PG-эталоне 2026-10-11); NULL ведёт себя одинаково.
    def sub_tilde(m):
        col, pat = m.group(1), m.group(2)
        if "[1-9]" in pat and r"\d" in pat:      # известный числовой паттерн
            return (f"({col} = '' OR {col} SIMILAR TO "
                    f"'(0|[1-9][0-9]*)([.][0-9]+)?')")
        return m.group(0)

    out, n3 = re.subn(r"(\w+\.info)\s*~\s*'([^']*)'", sub_tilde, out)
    if n3:
        notes.append(f"info ~ numeric-regex -> SIMILAR TO ({n3}x; пустые "
                     f"строки в info отсутствуют — семантика совпадает)")
    # ::тип -> CAST (шаблон 7a: mii.info::float). BLOB TEXT кастится в FB;
    # runtime-ошибка на нечисловой строке — как в PG (см. тест 2026-10-11).
    TYPEMAP = {"float": "DOUBLE PRECISION", "double precision": "DOUBLE PRECISION",
               "int": "INTEGER", "integer": "INTEGER", "bigint": "BIGINT",
               "numeric": "NUMERIC(18,6)", "text": "VARCHAR(8191)"}
    def sub_cast(m):
        col, typ = m.group(1), m.group(2).lower()
        return f"CAST({col} AS {TYPEMAP[typ]})"
    out, n4 = re.subn(
        r"(\w+\.\w+)::(float|integer|int|bigint|numeric|text)\b", sub_cast,
        out, flags=re.I)
    if n4:
        notes.append(f"::тип -> CAST ({n4}x; FB: ошибка конверсии на "
                     f"нечисловой строке — как в PG)")

    # прочие PG-regex остаются — увидим в prepare-тесте и пометим
    rest = sorted({m.group(1) for m in
                   re.finditer(r"(\w+\.\w+)\s*~\s*'[^']*'", out)})
    if rest:
        notes.append("UNSUPPORTED PG regex on: " + ",".join(rest))

    unexpected = sorted({kw for kw in
                         ("OR", "EXISTS", "NOT", "CAST", "::", "EXTRACT",
                          "INTERSECT", "EXCEPT", "UNION", "JOIN", "LIMIT",
                          "CASE", "BETWEEN", "DISTINCT")
                         if re.search(rf"\b{kw}\b", out, re.I)})
    if unexpected:
        notes.append("unexpected constructs: " + ",".join(unexpected) +
                     " (проверить вручную)")
    return out + "\n", notes


def extract_tables(sql: str) -> list[str]:
    frm = re.search(r"\bFROM\b(.*?)(?:\bWHERE\b|\bGROUP\b|\bORDER\b|$)",
                    sql, re.I | re.S).group(1)
    tbls = [t for t, _ in re.findall(r"\b(\w+)\s+as\s+(\w+)", frm, re.I)]
    if not tbls:  # алиасы без AS
        frm2 = re.sub(r"^[Ff][Rr][Oo][Mm]\s*", "", frm)
        parts = [p.strip() for p in frm2.split(",")]
        tbls = [p.split()[0] for p in parts if p.split()]
    return sorted({t.lower() for t in tbls})


def template_of(sql: str) -> str:
    t = re.sub(r"'[^']*'", "?", sql)
    t = re.sub(r"\b\d+\b", "?", t)
    t = re.sub(r"\s+", " ", t).strip().lower()
    return hashlib.md5(t.encode()).hexdigest()[:8]


def tags_of(sql: str) -> list[str]:
    tags = set()
    if re.search(r"\bCOUNT\s*\(", sql, re.I):
        tags.add("aggregate")
    if re.search(r"\bLIKE\b", sql, re.I):
        tags.add("like_predicate")
    if re.search(r"\bIN\s*\(", sql, re.I):
        tags.add("in_list")
    if re.search(r"\bGROUP\s+BY\b", sql, re.I):
        tags.add("group_by")
    if re.search(r"\bORDER\s+BY\b", sql, re.I):
        tags.add("order_by")
    if re.search(r"\bHAVING\b", sql, re.I):
        tags.add("having")
    if re.search(r"\b(>=|<=|>|<|BETWEEN)\b", sql, re.I):
        tags.add("range_predicate")
    return sorted(tags)


def main():
    import yaml
    data = json.load(open(SRC_JSON, encoding="utf-8"))
    os.makedirs(QDIR, exist_ok=True)
    manifest = []
    for tpl, sqls in sorted(data.items()):
        for i, raw in enumerate(sqls, 1):
            qid = f"ceb_{tpl}_{i:03d}"
            amap = extract_alias_map(raw)
            ported, notes = port_sql(raw, amap)
            with open(os.path.join(QDIR, f"{qid}.sql"), "w",
                      encoding="utf-8") as f:
                f.write(ported)
            tables = extract_tables(ported)
            manifest.append({
                "id": qid,
                "suite": "ceb-imdb-regen",
                "db": "imdb",
                "index_config": ["pk"],
                "template": template_of(ported),
                "tables": len(tables),
                "table_list": tables,
                "tags": tags_of(ported),
                "deterministic": True,
                "float_tolerance": None,
                "subplan_scope": None,
                "result": None,
                "port_notes": "; ".join(notes) if notes else None,
                "ceb_template": tpl,
            })
    with open(os.path.join(MANIFEST_DIR, "ceb-imdb-regen.yaml"), "w",
              encoding="utf-8") as f:
        yaml.safe_dump(manifest, f, allow_unicode=True, sort_keys=False)
    n_notes = sum(1 for m in manifest if m["port_notes"])
    max_t = max(m["tables"] for m in manifest)
    print(f"ceb-imdb-regen: {len(manifest)} запросов ({n_notes} с "
          f"port_notes), макс. таблиц {max_t} -> {QDIR}")


if __name__ == "__main__":
    main()
