"""Построение Firebird-копии IMDb (JOB) на инстансе 3055.

Порядок (раздел 4.2/4.5 плана):
  create -> таблицы (без индексов) -> загрузка CSV (параллельно, executemany)
  -> PRIMARY KEY -> вторичные индексы (как в PG, fkindexes.sql)
  -> SET STATISTICS -> сверка счётчиков -> manifest.

CSV выгружены с dellg15 (COPY ... FORMAT csv); NULL = пустое поле
(проверено: пустых строк '' в данных PG нет — textlen).

Запуск:
  python bench/datasets/imdb/build_imdb.py --stage load
  python bench/datasets/imdb/build_imdb.py --stage finalize
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
import fbenv  # noqa: E402

GEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated")
CSV_DIR = os.path.join(ROOT, "db", "imdb", "csv")
FDB = os.path.join(ROOT, "db", "imdb", "imdb_fb5.fdb")
MANIFEST = os.path.join(ROOT, "db", "imdb", "imdb_build_manifest.json")

# порядок загрузки: справочники -> факты; большие последними для баланса потоков
LOAD_ORDER = ["kind_type", "comp_cast_type", "company_type", "info_type",
              "link_type", "role_type", "complete_cast", "movie_link",
              "aka_name", "aka_title", "keyword", "company_name",
              "movie_companies", "movie_info_idx", "char_name", "movie_keyword",
              "name", "title", "person_info", "movie_info", "cast_info"]
ROWS_PER_STMT = 200      # строк на EXECUTE BLOCK (лимит FB: 256 контекстов)
STMT_BYTES_CAP = 2_000_000  # страховка от гигантских текстов в литералах
COMMIT_EVERY = 500_000


def log(msg: str):
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


def stage_create(force: bool):
    if os.path.exists(FDB):
        if not force:
            raise SystemExit(f"{FDB} уже существует (—force для пересоздания)")
        os.remove(FDB)
    rc, out = fbenv.isql_script(None, (
        f"CREATE DATABASE '{fbenv.dsn(FDB)}' USER {fbenv.FB_USER} "
        f"PASSWORD '{fbenv.FB_PASSWORD}' PAGE_SIZE 16384 "
        f"DEFAULT CHARACTER SET UTF8;\n"))
    assert rc == 0, f"create failed:\n{out[-2000:]}"
    ddl = open(os.path.join(GEN, "ddl_tables.sql"), encoding="utf-8").read()
    rc, out = fbenv.isql_script(FDB, ddl)
    assert rc == 0, f"ddl_tables failed:\n{out[-3000:]}"
    log(f"created {FDB} (page 16384) + 21 tables")


def _lit(c: str, v: str):
    if v == "":
        return "NULL"
    if c == "int":
        return v
    if len(v.encode("utf-8")) <= 12000:
        return "'" + v.replace("'", "''") + "'"
    # лимит литерала FB: 16383 байта UTF8 — длинные тексты чанкуем через ||
    parts, chars, nbytes = [], [], 0
    for ch in v:
        cb = len(ch.encode("utf-8"))
        if chars and nbytes + cb > 12000:
            parts.append("".join(chars))
            chars, nbytes = [], 0
        chars.append(ch)
        nbytes += cb
    if chars:
        parts.append("".join(chars))
    return " || ".join("'" + p.replace("'", "''") + "'" for p in parts)


def load_table(table: str, ctypes: dict) -> dict:
    cols = list(ctypes)
    t0 = time.perf_counter()
    db = fbenv.connect_fb(FDB)
    cur = db.cursor()
    cur.execute(f"DELETE FROM {table}")   # очистка частичных загрузок
    db.commit()
    n, batch, bytes_acc = 0, [], 0
    path = os.path.join(CSV_DIR, f"{table}.csv")

    def flush():
        # FB не принимает INSERT ... VALUES (...),(...): пачка -> EXECUTE BLOCK
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

    with open(path, newline="", encoding="utf-8") as f:
        rdr = csv.reader(f)
        for row in rdr:
            lit = "(" + ", ".join(
                _lit(c, v) for c, v in zip(ctypes.values(), row)) + ")"
            batch.append(lit)
            bytes_acc += len(lit)
            if len(batch) >= ROWS_PER_STMT or bytes_acc >= STMT_BYTES_CAP:
                flush()
        flush()
    try:
        db.commit()   # после flush-коммита ровно на границе _tra уже None
    except AttributeError:
        pass
    cur.close()
    db.close()
    secs = time.perf_counter() - t0
    log(f"{table}: DONE {n} rows in {secs:.0f}s ({n/max(secs,1e-9):.0f} r/s)")
    return {"rows": n, "seconds": round(secs, 1)}


def stage_load(threads: int, only: list[str] | None):
    ctypes = json.load(open(os.path.join(GEN, "column_types.json"),
                            encoding="utf-8"))
    tables = LOAD_ORDER if not only else [t for t in LOAD_ORDER if t in only]
    old = {}
    if os.path.exists(MANIFEST):
        old = json.load(open(MANIFEST, encoding="utf-8"))
    results = old.get("tables", {})
    todo = [t for t in tables if t not in results]
    log(f"loading {len(todo)} tables ({threads} threads): {todo}")
    from concurrent.futures import as_completed
    with ThreadPoolExecutor(max_workers=threads) as ex:
        futs = {ex.submit(load_table, t, ctypes[t]): t for t in todo}
        for fut in as_completed(futs):
            t = futs[fut]
            results[t] = fut.result()
            old["tables"] = results
            json.dump(old, open(MANIFEST, "w", encoding="utf-8"), indent=1)
    log(f"loaded rows total: {sum(v['rows'] for v in results.values())}")


def _isql_file(sql: str, label: str):
    rc, out = fbenv.isql_script(FDB, sql)
    assert rc == 0, f"{label} failed:\n{out[-3000:]}"


def stage_constraints():
    # по одному ALTER на таблицу: сборка PK-индекса большой таблицы
    # укладывается в таймаут инструмента, прогресс виден
    for t in LOAD_ORDER:
        t0 = time.perf_counter()
        _isql_file(f"ALTER TABLE {t} ADD CONSTRAINT {t}_pk PRIMARY KEY (id);\n",
                   f"pk:{t}")
        log(f"PK {t}: {time.perf_counter()-t0:.0f}s")


def stage_indexes():
    import gen_ddl  # тот же каталог: список индексов — единственный источник
    for name, t, col in gen_ddl.INDEXES:
        t0 = time.perf_counter()
        _isql_file(f"CREATE INDEX {name.upper()} ON {t} ({col});\n", f"idx:{name}")
        log(f"index {name}: {time.perf_counter()-t0:.0f}s")
    # SET STATISTICS по всем индексам (4.2)
    db = fbenv.connect_fb(FDB)
    cur = db.cursor()
    cur.execute("SELECT TRIM(RDB$INDEX_NAME) FROM RDB$INDICES "
                "WHERE RDB$SYSTEM_FLAG IS DISTINCT FROM 1")
    idx = [r[0].strip() for r in cur.fetchall()]
    cur.close()
    db.close()
    script = "".join(f"SET STATISTICS INDEX {i};\n" for i in idx)
    _isql_file(script, "set statistics")
    log(f"SET STATISTICS: {len(idx)} indexes")


def stage_verify():
    man = json.load(open(MANIFEST, encoding="utf-8"))
    db = fbenv.connect_fb(FDB)
    cur = db.cursor()
    counts, ok = {}, True
    for t in LOAD_ORDER:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        c = cur.fetchone()[0]
        counts[t] = c
        if c != man["tables"][t]["rows"]:
            ok = False
            log(f"MISMATCH {t}: db={c} loaded={man['tables'][t]['rows']}")
    cur.close()
    db.close()
    man["verify_counts"] = counts
    man["verify_ok"] = ok
    json.dump(man, open(MANIFEST, "w", encoding="utf-8"), indent=1)
    log(f"verify: {'OK' if ok else 'FAILED'} "
        f"(total {sum(counts.values())} rows)")
    assert ok


def stage_finalize():
    """gbak-архив + золотая копия (read-only) + SHA-256 (4.2)."""
    gold_dir = os.path.join(ROOT, "db", "golden")
    arch_dir = os.path.join(ROOT, "db", "archives")
    os.makedirs(gold_dir, exist_ok=True)
    os.makedirs(arch_dir, exist_ok=True)
    fbk = os.path.join(arch_dir, "imdb_fb5.fbk")
    t0 = time.perf_counter()
    rc, out = fbenv.gbak_backup(FDB, fbk)
    assert rc == 0, f"gbak failed:\n{out[-2000:]}"
    log(f"gbak: {os.path.getsize(fbk)/2**30:.1f} GiB in {time.perf_counter()-t0:.0f}s")
    golden = os.path.join(gold_dir, "imdb_fb5.fdb")
    if os.path.exists(golden):
        os.remove(golden)
    sha = fbenv.byte_copy(FDB, golden)
    rc, out = fbenv.gfix_set_readonly(golden)
    assert rc == 0, f"read_only failed:\n{out[-1000:]}"
    man = json.load(open(MANIFEST, encoding="utf-8"))
    man.update({"golden": golden, "golden_sha256": sha, "archive": fbk,
                "archive_sha256": fbenv.sha256_file(fbk),
                "page_size": 16384,
                "charset": "UTF8",
                "finished_at": dt.datetime.now().isoformat(timespec="seconds")})
    json.dump(man, open(MANIFEST, "w", encoding="utf-8"), indent=1)
    log(f"golden {golden} sha256={sha}")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="load",
                    choices=["create", "load", "constraints", "indexes",
                             "verify", "finalize", "all"])
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--only", nargs="*", help="таблицы для --stage load")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    t0 = time.perf_counter()
    if a.stage in ("create", "all"):
        stage_create(a.force)
    if a.stage in ("load", "all"):
        stage_load(a.threads, a.only)
    if a.stage in ("constraints", "all"):
        stage_constraints()
    if a.stage in ("indexes", "all"):
        stage_indexes()
    if a.stage in ("verify", "all"):
        stage_verify()
    if a.stage in ("finalize", "all"):
        stage_finalize()
    log(f"stage '{a.stage}' done in {time.perf_counter()-t0:.0f}s")


if __name__ == "__main__":
    main()
