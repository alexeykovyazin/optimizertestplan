"""Построение Firebird-копии DSB SF1 — §3.2.4.

Источник S0: microsoft/dsb, scripts/create_tables.sql (схема TPC-DS v2.11.0rc2
с inline PRIMARY KEY — конвенция DSB; FK нет, вторичные индексы — DTA-конфиг
dsb_index_pg.sql в бейслайн НЕ входит, консистентно с остальными сюитами).
Данные: dsdgen /scale 1 -> bench/datasets/dsb/sf1_csv/*.dat (pipe + хвостовой
'|'; ПУСТОЕ ПОЛЕ = NULL: customer 100% строк, item 9043, store_sales 259831 —
в PG COPY грузится с NULL '', здесь _lit("") -> NULL как в build_tpch).

Типы: integer / decimal(7,2) / char(n) / varchar(n) / date / time — все
FB5-нативные; prepare-тест ловит reserved words.

Запуск: python bench/datasets/dsb/build_dsb.py --stage create|load|finalize
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
import fbenv  # noqa: E402

TBL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sf1_csv")
FDB = os.path.join(ROOT, "db", "dsb", "dsb_sf1_fb5.fdb")
MANIFEST = os.path.join(ROOT, "db", "dsb", "dsb_build_manifest.json")
SOURCE_SQL = os.path.join(ROOT, "third_party", "dsb", "scripts",
                          "create_tables.sql")

TABLES: dict[str, tuple[list[str], list[str]]] = {}
COL_KINDS: dict[str, list[str]] = {}


def parse_source() -> None:
    txt = open(SOURCE_SQL, encoding="utf-8").read()
    for m in re.finditer(
            r"create table (\w+)\s*\((.*?)\n\)", txt, re.S | re.I):
        name = m.group(1).lower()
        body = m.group(2)
        cols, kinds, pk = [], [], []
        for line in body.splitlines():
            line = line.strip().rstrip(",")
            if not line:
                continue
            pm = re.match(r"primary key \(([^)]+)\)", line, re.I)
            if pm:
                pk = [c.strip().lower() for c in pm.group(1).split(",")]
                continue
            cm = re.match(r"([a-z_0-9]+)\s+([a-z]+(?:\s*\([^)]*\))?)",
                          line, re.I)
            if not cm:
                raise ValueError(f"{name}: неразобранная строка: {line}")
            col, typ = cm.group(1).lower(), re.sub(r"\s+", "", cm.group(2))
            cols.append(f"{col.upper()} {typ.upper()}")
            kind = ("INTEGER" if typ == "integer"
                    else "DECIMAL" if typ.startswith("decimal")
                    else "DATE" if typ == "date"
                    else "TIME" if typ == "time"
                    else "CHAR/VARCHAR")
            kinds.append(kind)
        TABLES[name] = (cols, pk)
        COL_KINDS[name] = kinds


# TPC-DS SF1 канонические счётчики (dsdgen; сверяются на finalize)
CANON_COUNTS = {
    "call_center": 6, "catalog_page": 11718, "catalog_returns": 215301,
    "catalog_sales": 1438815, "customer": 100000, "customer_address": 50000,
    "customer_demographics": 1920800, "date_dim": 73049,
    "dbgen_version": 1, "household_demographics": 7200, "income_band": 20,
    "inventory": 11745000, "item": 18000, "promotion": 300, "reason": 35,
    "ship_mode": 20, "store": 12, "store_returns": 720039,
    "store_sales": 2880404, "time_dim": 86400, "warehouse": 5,
    "web_page": 60, "web_returns": 144042, "web_sales": 719384,
    "web_site": 30,
}
# инвентарь и dbgen_version без PK в схеме (dbgen_version — метаданные)
NO_PK = {"dbgen_version"}
LOAD_ORDER = ["dbgen_version", "date_dim", "time_dim", "income_band",
              "warehouse", "ship_mode", "reason", "promotion", "store",
              "call_center", "web_site", "web_page", "catalog_page",
              "customer_demographics", "household_demographics",
              "customer_address", "customer", "item",
              "store_returns", "store_sales",
              "catalog_returns", "catalog_sales",
              "web_returns", "web_sales", "inventory"]
ROWS_PER_STMT = 200
STMT_BYTES_CAP = 2_000_000
COMMIT_EVERY = 500_000


def log(msg: str):
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


def _lit(kind: str, v: str) -> str:
    if v == "":
        return "NULL"
    if kind == "INTEGER":
        return str(int(v))
    if kind == "TIME":
        return f"'{v}'"
    if len(v.encode("utf-8")) <= 12000:
        return "'" + v.replace("'", "''") + "'"
    raise ValueError(f"литерал {len(v)} байт превышает лимит: {v[:60]}")


def load_table(table: str) -> dict:
    cols = [c.split()[0].lower() for c in TABLES[table][0]]
    kinds = COL_KINDS[table]
    t0 = time.perf_counter()
    db = fbenv.connect_fb(FDB)
    cur = db.cursor()
    cur.execute(f"DELETE FROM {table}")
    db.commit()
    n, batch, bytes_acc = 0, [], 0
    path = os.path.join(TBL_DIR, f"{table}.dat")

    def flush():
        nonlocal n, batch, bytes_acc
        if batch:
            body = "".join(f"INSERT INTO {table} ({', '.join(cols)}) "
                           f"VALUES {r};\n" for r in batch)
            cur.execute("EXECUTE BLOCK AS BEGIN\n" + body + "\nEND")
            n += len(batch)
            batch, bytes_acc = [], 0
            if n % COMMIT_EVERY < ROWS_PER_STMT:
                db.commit()
                log(f"  {table}: {n} rows, {time.perf_counter()-t0:.0f}s")

    with open(path, encoding="utf-8", newline="\n") as f:
        for ln in f:
            ln = ln.rstrip("\r\n")
            if not ln:
                continue
            fields = ln.split("|")
            if fields and fields[-1] == "":
                fields.pop()
            assert len(fields) == len(cols), \
                f"{table}: {len(fields)} != {len(cols)}: {fields[:3]}"
            lit = "(" + ", ".join(_lit(k, v) for k, v in
                                  zip(kinds, fields)) + ")"
            batch.append(lit)
            bytes_acc += len(lit)
            if len(batch) >= ROWS_PER_STMT or bytes_acc >= STMT_BYTES_CAP:
                flush()
        flush()
    try:
        db.commit()
    except Exception:
        pass
    cur.close()
    db.close()
    secs = time.perf_counter() - t0
    log(f"{table}: DONE {n} rows in {secs:.0f}s ({n/max(secs,1e-9):.0f} r/s)")
    return {"rows": n, "seconds": round(secs, 1)}


def stage_create(force: bool = False):
    parse_source()
    if os.path.exists(FDB):
        if not force:
            raise SystemExit(f"{FDB} уже существует (--force для пересоздания)")
        os.remove(FDB)
    os.makedirs(os.path.dirname(FDB), exist_ok=True)
    rc, out = fbenv.isql_script(None, (
        f"CREATE DATABASE '{fbenv.dsn(FDB)}' USER {fbenv.FB_USER} "
        f"PASSWORD '{fbenv.FB_PASSWORD}' PAGE_SIZE 16384 "
        f"DEFAULT CHARACTER SET UTF8;\n"))
    assert rc == 0, f"create failed:\n{out[-2000:]}"
    ddl = "".join(
        f"CREATE TABLE {t} ({', '.join(cols)});\n"
        for t, (cols, _pk) in TABLES.items())
    rc, out = fbenv.isql_script(FDB, ddl)
    assert rc == 0, f"ddl failed:\n{out[-3000:]}"
    log(f"created {FDB} (page 16384) + {len(TABLES)} tables")


def stage_load(threads: int = 3, only: list[str] | None = None):
    parse_source()
    old = {}
    if os.path.exists(MANIFEST):
        old = json.load(open(MANIFEST, encoding="utf-8"))
    results = old.get("tables", {})
    todo = [t for t in LOAD_ORDER
            if (only and t in only) or (not only and t not in results)]
    log(f"loading {len(todo)} tables ({threads} threads): {todo}")
    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=threads) as ex:
        futs = {ex.submit(load_table, t): t for t in todo}
        for fut in as_completed(futs):
            t = futs[fut]
            results[t] = fut.result()
            old["tables"] = results
            old["source"] = {
                "tool": "dsdgen 2.11.0rc2 DSB (microsoft/dsb, msbuild "
                        "Release|Win32 v142)",
                "sf": 1, "dir": "bench/datasets/dsb/sf1_csv",
                "counts_canonical": CANON_COUNTS,
            }
            json.dump(old, open(MANIFEST, "w", encoding="utf-8"),
                      indent=1, ensure_ascii=False)
    log(f"loaded rows total: {sum(v['rows'] for v in results.values())}")


def stage_finalize():
    parse_source()
    for t, (cols, pk) in TABLES.items():
        if not pk or t in NO_PK:
            continue
        t0 = time.perf_counter()
        # FB требует NOT NULL для PK (PG ставит неявно при ADD PK);
        # суррогатные ключи в данных не NULL — SET NOT NULL безопасен
        for c in pk:
            rc, out = fbenv.isql_script(
                FDB, f"ALTER TABLE {t} ALTER COLUMN {c.upper()} "
                     f"SET NOT NULL;\n")
            assert rc == 0, f"notnull:{t}.{c} failed:\n{out[-2000:]}"
        rc, out = fbenv.isql_script(
            FDB, f"ALTER TABLE {t} ADD CONSTRAINT {t}_pk "
                 f"PRIMARY KEY ({', '.join(pk)});\n")
        assert rc == 0, f"pk:{t} failed:\n{out[-2000:]}"
        log(f"PK {t}: {time.perf_counter()-t0:.0f}s")
    db = fbenv.connect_fb(FDB)
    cur = db.cursor()
    counts = {}
    for t in LOAD_ORDER:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        counts[t] = cur.fetchone()[0]
    cur.close()
    db.close()
    ok = all(counts[t] == CANON_COUNTS[t] for t in LOAD_ORDER)
    log(f"counts: {counts} -> {'OK' if ok else 'MISMATCH'}")
    assert ok, f"счётчики не совпали с каноном SF1: {counts} vs {CANON_COUNTS}"
    old = json.load(open(MANIFEST, encoding="utf-8"))
    old["counts"] = counts
    old["pk"] = {t: pk for t, (_c, pk) in TABLES.items() if pk}
    old["secondary_indexes"] = "нет (PK-only, консистентно с остальными сюитами)"
    json.dump(old, open(MANIFEST, "w", encoding="utf-8"), indent=1,
              ensure_ascii=False)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["create", "load", "finalize"])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--threads", type=int, default=3)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    {"create": lambda: stage_create(a.force),
     "load": lambda: stage_load(a.threads, a.only),
     "finalize": stage_finalize}[a.stage]()
