"""Истинные кардинальности корпуса stats-ceb (раздел 4.6 плана).

Правило «истина считается один раз»: COUNT(*) по всем корневым запросам,
подпланам и одно-табличным запросам выполняется в DuckDB на CSV снимка
stats_simplified. Выборочная сверка с Firebird — отдельным шагом (verify_fb).

Результат: bench/truth/stats-ceb/<suite>.parquet (query_id, true_rows).
"""
from __future__ import annotations

import os
import sys

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CSV_DIR = os.path.join(ROOT, "third_party", "STATS-CEB", "datasets", "stats_simplified")
QDIR = os.path.join(ROOT, "bench", "queries")
TRUTH_DIR = os.path.join(ROOT, "bench", "truth", "stats-ceb")

SCHEMA = {
    "users": ("Id BIGINT, Reputation BIGINT, CreationDate TIMESTAMP, Views BIGINT,"
              " UpVotes BIGINT, DownVotes BIGINT"),
    "posts": ("Id BIGINT, PostTypeId SMALLINT, CreationDate TIMESTAMP, Score BIGINT,"
              " ViewCount BIGINT, OwnerUserId BIGINT, AnswerCount BIGINT,"
              " CommentCount BIGINT, FavoriteCount BIGINT, LastEditorUserId BIGINT"),
    "postLinks": ("Id BIGINT, CreationDate TIMESTAMP, PostId BIGINT,"
                  " RelatedPostId BIGINT, LinkTypeId SMALLINT"),
    "postHistory": ("Id BIGINT, PostHistoryTypeId SMALLINT, PostId BIGINT,"
                    " CreationDate TIMESTAMP, UserId BIGINT"),
    "comments": ("Id BIGINT, PostId BIGINT, Score SMALLINT, CreationDate TIMESTAMP,"
                 " UserId BIGINT"),
    "votes": ("Id BIGINT, PostId BIGINT, VoteTypeId SMALLINT, CreationDate TIMESTAMP,"
              " UserId BIGINT, BountyAmount SMALLINT"),
    "badges": "Id BIGINT, UserId BIGINT, \"Date\" TIMESTAMP",
    "tags": "Id BIGINT, \"Count\" BIGINT, ExcerptPostId BIGINT",
}


def fb_to_duck(sql: str) -> str:
    """Firebird-порт -> DuckDB: снять квотирование зарезервированных слов
    (в DuckDB имена совпадают с заголовками CSV без учёта регистра)."""
    return sql.replace('"Date"', "Date").replace('"Count"', "Count")


def register_tables(con: duckdb.DuckDBPyConnection):
    for t, schema in SCHEMA.items():
        cols = ", ".join(
            "%s: '%s'" % (name.strip('"'), typ)
            for name, typ in (pair.strip().split(None, 1)
                              for pair in schema.split(",") if pair.strip()))
        con.execute(f"""
            CREATE TABLE {t} AS SELECT * FROM read_csv(
                '{os.path.join(CSV_DIR, t + ".csv").replace(os.sep, "/")}',
                header=true, columns={{{cols}}},
                nullstr='', timestampformat='%Y-%m-%d %H:%M:%S')
        """)


def compute_suite(con, suite: str, per_query_budget_s: float | None = None,
                  progress_every: int = 25) -> dict[str, int]:
    """per_query_budget_s: бюджет одного COUNT (DuckDB con.interrupt());
    превышение даёт true_rows=None — недостающее досчитывает ночной контур,
    покрытие фиксируется в отчёте (4.6)."""
    import threading
    qdir = os.path.join(ROOT, "bench", "queries", suite)
    ids = sorted(f[:-4] for f in os.listdir(qdir) if f.endswith(".sql"))
    truth = {}
    for i, qid in enumerate(ids, 1):
        sql = open(os.path.join(qdir, qid + ".sql"), encoding="utf-8").read()
        timer = None
        if per_query_budget_s:
            timer = threading.Timer(per_query_budget_s, con.interrupt)
            timer.start()
        try:
            n = con.execute(fb_to_duck(sql)).fetchone()[0]
        except Exception as e:  # noqa: BLE001
            msg = str(e).strip().replace("\n", " ")[:100]
            kind = "BUDGET" if per_query_budget_s and timer else "FAIL"
            print(f"  {suite}/{qid}: {kind} ({msg})", file=sys.stderr)
            n = None
        finally:
            if timer:
                timer.cancel()
        truth[qid] = n
        if progress_every and i % progress_every == 0:
            line = f"  {suite}: {i}/{len(ids)}"
            print(line, flush=True)
            try:
                with open(os.path.join(ROOT, "results", "runs",
                                       "truth_progress.log"), "a") as lf:
                    lf.write(line + "\n")
            except OSError:
                pass
    return truth


def save(suite: str, truth: dict[str, int]):
    os.makedirs(TRUTH_DIR, exist_ok=True)
    ids = list(truth.keys())
    tbl = pa.table({
        "query_id": pa.array(ids, pa.string()),
        "true_rows": pa.array([truth[i] for i in ids], pa.int64()),
    })
    pq.write_table(tbl, os.path.join(TRUTH_DIR, f"{suite}.parquet"))


def main():
    con = duckdb.connect()
    con.execute("SET threads TO 4")
    con.execute("SET memory_limit='6GB'")
    con.execute("SET temp_directory='" +
                os.path.join(ROOT, "results", "runs", "duckdb_tmp").replace(os.sep, "/") +
                "'")
    register_tables(con)
    # корневые и одно-табличные — полная истина
    for suite in ("stats-ceb", "stats-ceb-single"):
        truth = compute_suite(con, suite)
        fails = [k for k, v in truth.items() if v is None]
        save(suite, truth)
        print(f"{suite}: {len(truth)} computed, {len(fails)} failed")
        if fails:
            print("  failed ids:", fails[:10])
    # подпланы: бюджет на запрос (4.6: недостающее досчитывает ночь)
    truth = compute_suite(con, "stats-ceb-subplans",
                          per_query_budget_s=float(
                              os.environ.get("BENCH_SUBPLAN_BUDGET_S", "30")),
                          progress_every=100)
    save("stats-ceb-subplans", truth)
    have = sum(1 for v in truth.values() if v is not None)
    print(f"stats-ceb-subplans: coverage {have}/{len(truth)} "
          f"({100.0 * have / len(truth):.1f}%)")


if __name__ == "__main__":
    main()
