"""Построение Firebird-копии TPC-H SF1 (функциональная валидация, план §3.2.1).

Источник S0: TPC-H dbgen 2.14 — официальный дистрибутив требует регистрации
на tpc.org, использовано зеркало electrum/tpch-dbgen (тот же исходный код);
EULA TPC — использование исследовательское, перед публикацией сверить §13.
Данные: dbgen -vf -s 1 → 8 .tbl (pipe-delimited, NULL нет, канонические
счётчики SF1: region 5, nation 25, supplier 10000, customer 150000,
part 200000, partsupp 800000, orders 1500000, lineitem 6001215).

S1-сверка (2026-10-10, gen_tpch_data): фактические максимумы строковых
колонок <= 198 байт < 8191 — BLOB-дивергенций НЕ требуется (p_comment 22,
c_comment 116 и т.д.).

Порядок: create -> таблицы (без индексов) -> загрузка .tbl (EXECUTE BLOCK
по 200 строк, 3-4 потока) -> PRIMARY KEY (в т.ч. составные partsupp/
lineitem — как в dss.ddl) -> сверка счётчиков -> manifest.
Вторичные индексы — на S3 на dellg15 (точно как в PG-эталоне; здесь их нет
и не должно быть — функциональная проверка диалекта и счётчиков).

Запуск:
  python bench/datasets/tpch/build_tpch.py --stage create
  python bench/datasets/tpch/build_tpch.py --stage load [--threads 3]
  python bench/datasets/tpch/build_tpch.py --stage finalize
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
import fbenv  # noqa: E402

TBL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sf1_csv")
FDB = os.path.join(ROOT, "db", "tpch", "tpch_sf1_fb5.fdb")
MANIFEST = os.path.join(ROOT, "db", "tpch", "tpch_build_manifest.json")

# (таблица, колонки [(имя, тип)], pk-колонки) — по dss.ddl 2.14
TABLES = {
    "region": (["r_regionkey INTEGER NOT NULL", "r_name CHAR(25) NOT NULL",
                "r_comment VARCHAR(152)"], ["r_regionkey"]),
    "nation": (["n_nationkey INTEGER NOT NULL", "n_name CHAR(25) NOT NULL",
                "n_regionkey INTEGER NOT NULL",
                "n_comment VARCHAR(152)"], ["n_nationkey"]),
    "part": (["p_partkey INTEGER NOT NULL", "p_name VARCHAR(55) NOT NULL",
              "p_mfgr CHAR(25) NOT NULL", "p_brand CHAR(10) NOT NULL",
              "p_type VARCHAR(25) NOT NULL", "p_size INTEGER NOT NULL",
              "p_container CHAR(10) NOT NULL",
              "p_retailprice DECIMAL(15,2) NOT NULL",
              "p_comment VARCHAR(23) NOT NULL"], ["p_partkey"]),
    "supplier": (["s_suppkey INTEGER NOT NULL", "s_name CHAR(25) NOT NULL",
                  "s_address VARCHAR(40) NOT NULL",
                  "s_nationkey INTEGER NOT NULL", "s_phone CHAR(15) NOT NULL",
                  "s_acctbal DECIMAL(15,2) NOT NULL",
                  "s_comment VARCHAR(101) NOT NULL"], ["s_suppkey"]),
    "partsupp": (["ps_partkey INTEGER NOT NULL",
                  "ps_suppkey INTEGER NOT NULL",
                  "ps_availqty INTEGER NOT NULL",
                  "ps_supplycost DECIMAL(15,2) NOT NULL",
                  "ps_comment VARCHAR(199) NOT NULL"],
                 ["ps_partkey", "ps_suppkey"]),
    "customer": (["c_custkey INTEGER NOT NULL", "c_name VARCHAR(25) NOT NULL",
                  "c_address VARCHAR(40) NOT NULL",
                  "c_nationkey INTEGER NOT NULL", "c_phone CHAR(15) NOT NULL",
                  "c_acctbal DECIMAL(15,2) NOT NULL",
                  "c_mktsegment CHAR(10) NOT NULL",
                  "c_comment VARCHAR(117) NOT NULL"], ["c_custkey"]),
    "orders": (["o_orderkey INTEGER NOT NULL",
                "o_custkey INTEGER NOT NULL", "o_orderstatus CHAR(1) NOT NULL",
                "o_totalprice DECIMAL(15,2) NOT NULL",
                "o_orderdate DATE NOT NULL",
                "o_orderpriority CHAR(15) NOT NULL",
                "o_clerk CHAR(15) NOT NULL", "o_shippriority INTEGER NOT NULL",
                "o_comment VARCHAR(79) NOT NULL"], ["o_orderkey"]),
    "lineitem": (["l_orderkey INTEGER NOT NULL", "l_partkey INTEGER NOT NULL",
                  "l_suppkey INTEGER NOT NULL",
                  "l_linenumber INTEGER NOT NULL",
                  "l_quantity DECIMAL(15,2) NOT NULL",
                  "l_extendedprice DECIMAL(15,2) NOT NULL",
                  "l_discount DECIMAL(15,2) NOT NULL",
                  "l_tax DECIMAL(15,2) NOT NULL",
                  "l_returnflag CHAR(1) NOT NULL",
                  "l_linestatus CHAR(1) NOT NULL",
                  "l_shipdate DATE NOT NULL", "l_commitdate DATE NOT NULL",
                  "l_receiptdate DATE NOT NULL",
                  "l_shipinstruct CHAR(25) NOT NULL",
                  "l_shipmode CHAR(10) NOT NULL",
                  "l_comment VARCHAR(44) NOT NULL"],
                 ["l_orderkey", "l_linenumber"]),
}
CANON_COUNTS = {"region": 5, "nation": 25, "supplier": 10000,
                "customer": 150000, "part": 200000, "partsupp": 800000,
                "orders": 1500000, "lineitem": 6001215}
LOAD_ORDER = ["region", "nation", "supplier", "part", "partsupp",
              "customer", "orders", "lineitem"]
ROWS_PER_STMT = 200
STMT_BYTES_CAP = 2_000_000
COMMIT_EVERY = 500_000
EXPECT_COUNTS = True  # счётчик lineitem сверяется только если файл дочитан


def log(msg: str):
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


def col_types(table: str) -> list[str]:
    return [c.split()[0] for c in TABLES[table][0]]


def _lit(kind: str, v: str) -> str:
    if v == "":
        return "NULL"
    if kind == "INTEGER":
        return str(int(v))
    # DECIMAL/DATE/CHAR/VARCHAR — литералом; ISO-дата FB принимает
    if len(v.encode("utf-8")) <= 12000:
        return "'" + v.replace("'", "''") + "'"
    raise ValueError(f"литерал {len(v)} байт превышает лимит: {v[:60]}")


def load_table(table: str) -> dict:
    cols = [c.split()[0].lower() for c in TABLES[table][0]]
    kinds = col_types(table)
    t0 = time.perf_counter()
    db = fbenv.connect_fb(FDB)
    cur = db.cursor()
    cur.execute(f"DELETE FROM {table}")
    db.commit()
    n, batch, bytes_acc = 0, [], 0
    path = os.path.join(TBL_DIR, f"{table}.tbl")

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
                fields.pop()          # хвостовой pipe формата .tbl
            assert len(fields) == len(cols), f"{table}: {fields[:3]}..."
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
    old = {}
    if os.path.exists(MANIFEST):
        old = json.load(open(MANIFEST, encoding="utf-8"))
    results = old.get("tables", {})
    todo = [t for t in LOAD_ORDER
            if (only and t in only) or (not only and t not in results)]
    log(f"loading {len(todo)} tables ({threads} threads): {todo}")
    from concurrent.futures import as_completed
    with ThreadPoolExecutor(max_workers=threads) as ex:
        futs = {ex.submit(load_table, t): t for t in todo}
        for fut in as_completed(futs):
            t = futs[fut]
            results[t] = fut.result()
            old["tables"] = results
            old["source"] = {"tool": "dbgen 2.14 (electrum/tpch-dbgen mirror)",
                             "sf": 1, "dir": "bench/datasets/tpch/sf1_csv",
                             "counts_canonical": CANON_COUNTS}
            json.dump(old, open(MANIFEST, "w", encoding="utf-8"),
                      indent=1, ensure_ascii=False)
    log(f"loaded rows total: {sum(v['rows'] for v in results.values())}")


def stage_finalize():
    for t, (cols, pk) in TABLES.items():
        t0 = time.perf_counter()
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
    old["pk"] = {t: pk for t, (_c, pk) in TABLES.items()}
    old["secondary_indexes"] = "deferred to S3 (dellg15, как в PG-эталоне)"
    json.dump(old, open(MANIFEST, "w", encoding="utf-8"), indent=1,
              ensure_ascii=False)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["create", "load", "finalize"])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--threads", type=int, default=3)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    {"create": lambda: stage_create(a.force), "load": lambda: stage_load(a.threads, a.only),
     "finalize": stage_finalize}[a.stage]()


if __name__ == "__main__":
    main()
