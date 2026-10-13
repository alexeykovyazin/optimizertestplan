"""Создание золотых копий БД stats для конфигураций индексов pk и pk_fk.

Порядок (раздел 4.2 плана):
  загрузка -> SET STATISTICS по всем индексам -> проверка -> gbak-архив ->
  файл БД становится золотой копией (read-only), фиксируется SHA-256.

Запуск:  python bench/datasets/stats/load/build_golden.py
"""
import csv
import datetime as dt
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
import fbenv  # noqa: E402

CSV_DIR = os.path.join(ROOT, "third_party", "STATS-CEB", "datasets", "stats_simplified")
DDL_DIR = os.path.join(ROOT, "bench", "datasets", "stats")
WORK_DIR = os.path.join(ROOT, "db", "work")
GOLD_DIR = os.path.join(ROOT, "db", "golden")
ARCH_DIR = os.path.join(ROOT, "db", "archives")

TABLES = {
    "users": ("Id, Reputation, CreationDate, Views, UpVotes, DownVotes",
              [int, int, "ts", int, int, int]),
    "posts": ("Id, PostTypeId, CreationDate, Score, ViewCount, OwnerUserId, "
              "AnswerCount, CommentCount, FavoriteCount, LastEditorUserId",
              [int, int, "ts", int, int, int, int, int, int, int]),
    "postLinks": ("Id, CreationDate, PostId, RelatedPostId, LinkTypeId",
                  [int, "ts", int, int, int]),
    "postHistory": ("Id, PostHistoryTypeId, PostId, CreationDate, UserId",
                    [int, int, int, "ts", int]),
    "comments": ("Id, PostId, Score, CreationDate, UserId",
                 [int, int, int, "ts", int]),
    "votes": ("Id, PostId, VoteTypeId, CreationDate, UserId, BountyAmount",
              [int, int, int, "ts", int, int]),
    "badges": ("Id, UserId, \"Date\"", [int, int, "ts"]),
    "tags": ("Id, \"Count\", ExcerptPostId", [int, int, int]),
}
BATCH = 10000


def parse(col, v):
    if v is None or v == "":
        return None
    if col == "ts":
        return dt.datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
    return col(v)


def load_table(db, table, cols, convs):
    cur = db.cursor()
    cur.execute(f"DELETE FROM {table}")
    db.commit()
    sql = f"INSERT INTO {table} ({cols}) VALUES ({', '.join('?' * len(convs))})"
    header, batch, n = None, [], 0
    with open(os.path.join(CSV_DIR, f"{table}.csv"), newline="", encoding="utf-8") as f:
        rdr = csv.reader(f)
        header = next(rdr)
        assert len(header) == len(convs), f"{table}: CSV {len(header)} vs DDL {len(convs)} столбцов"
        for row in rdr:
            batch.append([parse(c, v) for c, v in zip(convs, row)])
            if len(batch) >= BATCH:
                cur.executemany(sql, batch)
                n += len(batch)
                batch = []
        if batch:
            cur.executemany(sql, batch)
            n += len(batch)
    db.commit()
    cur.close()
    return n


def verify_counts(db):
    cur = db.cursor()
    counts = {}
    for t in TABLES:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        counts[t] = cur.fetchone()[0]
    cur.close()
    return counts


def set_statistics_all(db_path):
    """SET STATISTICS INDEX по всем пользовательским индексам (4.2)."""
    tmp = os.path.join(WORK_DIR, "_setstat.tmp.fdb")
    if os.path.exists(tmp):
        os.remove(tmp)
    os.replace(db_path, tmp)
    os.replace(tmp, db_path)  # no-op, гарантируем отсутствие соединений
    db = fbenv.connect_fb(db_path)
    cur = db.cursor()
    cur.execute("SELECT TRIM(RDB$INDEX_NAME) FROM RDB$INDICES "
                "WHERE RDB$SYSTEM_FLAG IS DISTINCT FROM 1")
    idx = [r[0].strip() for r in cur.fetchall()]
    cur.close()
    db.close()
    script = "".join(f"SET STATISTICS INDEX {i};\n" for i in idx)
    rc, out = fbenv.isql_script(db_path, script)
    return idx, rc, out


def build(config: str):
    assert config in ("pk", "pk_fk")
    work = os.path.join(WORK_DIR, f"stats_{config}.fdb")
    for p in (work,):
        if os.path.exists(p):
            os.remove(p)

    rc, out = fbenv.isql_script(None,
        f'CREATE DATABASE \'{fbenv.dsn(work)}\' USER {fbenv.FB_USER} '
        f'PASSWORD \'{fbenv.FB_PASSWORD}\' PAGE_SIZE 8192 '
        f'DEFAULT CHARACTER SET UTF8;\n')
    assert rc == 0, f"create database failed:\n{out[-2000:]}"

    ddl = open(os.path.join(DDL_DIR, "ddl_pk.sql"), encoding="utf-8").read()
    rc, out = fbenv.isql_script(work, ddl)
    assert rc == 0, f"ddl_pk failed:\n{out[-3000:]}"
    if config == "pk_fk":
        ddl2 = open(os.path.join(DDL_DIR, "ddl_pk_fk.sql"), encoding="utf-8").read()
        rc, out = fbenv.isql_script(work, ddl2)
        assert rc == 0, f"ddl_pk_fk failed:\n{out[-3000:]}"

    db = fbenv.connect_fb(work)
    tmap_total = {}
    for t, (cols, convs) in TABLES.items():
        n = load_table(db, t, cols, convs)
        tmap_total[t] = n
        print(f"  loaded {t}: {n}")
    counts = verify_counts(db)
    assert counts == tmap_total, f"count mismatch: {counts} vs {tmap_total}"
    db.close()

    idx, rc, out = set_statistics_all(work)
    assert rc == 0, f"SET STATISTICS failed:\n{out[-2000:]}"
    print(f"  SET STATISTICS: {len(idx)} indexes")

    fbk = os.path.join(ARCH_DIR, f"stats_{config}.fbk")
    rc, out = fbenv.gbak_backup(work, fbk)
    assert rc == 0, f"gbak failed:\n{out[-2000:]}"

    golden = os.path.join(GOLD_DIR, f"stats_{config}.fdb")
    if os.path.exists(golden):
        os.remove(golden)
    fbenv.byte_copy(work, golden)          # побайтовая копия, не restore
    sha = fbenv.sha256_file(golden)
    rc, out = fbenv.gfix_set_readonly(golden)
    assert rc == 0, f"read_only failed:\n{out[-1000:]}"

    print(f"  golden {golden} sha256={sha}")
    return {"config": config, "golden": golden, "golden_sha256": sha,
            "archive": fbk, "archive_sha256": fbenv.sha256_file(fbk),
            "row_counts": counts, "indexes_set_statistics": idx}


def main():
    os.makedirs(GOLD_DIR, exist_ok=True)
    os.makedirs(ARCH_DIR, exist_ok=True)
    report = {"dataset": "stats_simplified (End-to-End CardEst Benchmark)",
              "server": "FB 5.0.5 HQbird @ localhost:3055", "builds": []}
    for cfg in ("pk", "pk_fk"):
        print(f"=== building stats_{cfg} ===")
        report["builds"].append(build(cfg))
    out = os.path.join(DDL_DIR, "golden_manifest.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print("written", out)


if __name__ == "__main__":
    main()
