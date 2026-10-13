"""Исполнение портированных JOB-запросов на Firebird и сверка с PG-эталоном.

Для каждого qid:
  1) prepare (клиентский сторож, prepare_with_watchdog) -> план, prepare_ms;
  2) исполнение с statement timeout + клиентским сторожем (_Worker);
  3) сравнение мультимножества строк с эталоном results/job_pg_reference.
Для запросов с усечённым MIN(blob.info) допускается префиксное совпадение
(match_truncated) — усечение задано правилом портирования.

Результат: results/job_validation/{qid}.json (инкрементально) + report.json.
Запуск:
  python bench/harness/job_validate.py --fdb db/imdb/work/imdb_work.fdb
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
import fbenv  # noqa: E402
from runner import _Worker  # noqa: E402

QDIR = os.path.join(ROOT, "bench", "queries", "job")
PGREF = os.path.join(ROOT, "results", "job_pg_reference")
OUTDIR = os.path.join(ROOT, "results", "job_validation")
TRUNC = 8000


def canon_cell(v):
    if v is None:
        return None
    if isinstance(v, int):
        return v
    s = str(v).strip()
    if s == "":
        # PG-CSV не различает NULL и пустую строку (psql COPY), а FB даёт
        # None для NULL и '' для пустой строки — канонизируем оба в None
        return None
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    return s


def canon_rows(rows):
    """PG-эталон: пустая строка CSV [] — строка из NULL (агрегат по 0 строк).
    Нормализуем такие строки с обеих сторон в ()."""
    out = []
    for r in rows:
        cells = tuple(canon_cell(c) for c in r)
        if all(c is None for c in cells) or len(cells) == 0:
            cells = ()
        out.append(repr(cells))
    return sorted(out)


def prefix_compatible(fb_rows, pg_rows) -> bool:
    """Все значения FB — префиксы соответствующих значений PG (усечение)."""
    if len(fb_rows) != len(pg_rows):
        return False
    for fr, pr in zip(sorted(fb_rows, key=repr), sorted(pg_rows, key=repr)):
        if len(fr) != len(pr):
            return False
        for a, b in zip(fr, pr):
            sa = "" if a is None else str(a)
            sb = None if b is None else str(b)
            if sb is None or not sb.startswith(sa):
                return False
    return True


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--fdb", required=True)
    ap.add_argument("--timeout-s", type=float, default=600.0)
    ap.add_argument("--prepare-timeout-s", type=float, default=180.0)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--suite", default="job",
                    help="имя сюиты (каталог в bench/queries); по умолчанию "
                         "job — старое поведение")
    ap.add_argument("--pgref", default=None,
                    help="каталог PG-эталона (по умолчанию "
                         "results/<suite>_pg_reference)")
    ap.add_argument("--outdir", default=None,
                    help="каталог результата (по умолчанию "
                         "results/<suite>_validation)")
    a = ap.parse_args()

    qdir = (QDIR if a.suite == "job"
            else os.path.join(ROOT, "bench", "queries", a.suite))
    pgref = a.pgref or os.path.join(ROOT, "results",
                                    f"{a.suite}_pg_reference")
    outdir = a.outdir or os.path.join(ROOT, "results",
                                      f"{a.suite}_validation")
    os.makedirs(outdir, exist_ok=True)
    ids = sorted(f[:-4] for f in os.listdir(qdir) if f.endswith(".sql"))
    if a.only:
        ids = [i for i in ids if i in set(a.only)]

    worker = _Worker(a.fdb)
    summary = []
    try:
        for i, qid in enumerate(ids, 1):
            rec = {"query_id": qid, "status": None, "prepare_ms": None,
                   "exec_ms": None, "rows_count": None, "checksum": None,
                   "plan": None, "error": None}
            t0 = time.perf_counter()
            sql = open(os.path.join(qdir, qid + ".sql"),
                       encoding="utf-8").read()
            try:
                pg = json.load(open(os.path.join(pgref, f"{qid}.json"),
                                    encoding="utf-8"))
                pg_rows = pg.get("rows")
                pg_checksum = pg.get("checksum")
            except FileNotFoundError:
                pg_rows = pg_checksum = None

            prep = fbenv.prepare_with_watchdog(a.fdb, sql, a.prepare_timeout_s)
            rec["prepare_ms"] = prep["prepare_ms"]
            rec["plan"] = prep["plan"]
            if prep["timed_out"]:
                rec["status"] = "prepare_timeout"
            elif prep["error"]:
                rec["status"] = "error"
                rec["error"] = prep["error"]
            else:
                r = worker.run(sql, a.timeout_s)
                if r["timed_out"]:
                    rec["status"] = "exec_timeout"
                elif r["err"]:
                    rec["status"] = "error"
                    rec["error"] = f"{type(r['err']).__name__}: {r['err']}"
                else:
                    res = r["res"]
                    rec["exec_ms"] = res["ms"]
                    rec["rows_count"] = len(res["rows"])
                    from runner import rows_checksum
                    rec["checksum"] = rows_checksum(res["rows"])
                    if pg_rows is None:
                        rec["status"] = "no_pg_reference"
                    else:
                        fb_c = canon_rows(res["rows"])
                        pg_c = canon_rows(pg_rows)
                        if fb_c == pg_c:
                            rec["status"] = "match"
                        elif pg_rows and prefix_compatible(
                                res["rows"], [list(map(str, x)) for x in pg_rows]):
                            rec["status"] = "match_truncated"
                        else:
                            rec["status"] = "mismatch"
            rec["wall_s"] = round(time.perf_counter() - t0, 1)
            summary.append(rec)
            with open(os.path.join(outdir, f"{qid}.json"), "w",
                      encoding="utf-8") as f:
                json.dump(rec, f, ensure_ascii=False, indent=1)
            print(f"[{i}/{len(ids)}] {qid}: {rec['status']} "
                  f"(prep={rec['prepare_ms'] and round(rec['prepare_ms'])}ms, "
                  f"exec={rec['exec_ms'] and round(rec['exec_ms'])}ms)",
                  flush=True)
    finally:
        worker.close()
        from collections import Counter
        cnt = Counter(r["status"] for r in summary)
        report = {"suite": a.suite, "statuses": dict(cnt), "total": len(summary),
                  "results": summary}
        with open(os.path.join(outdir, "report.json"), "w",
                  encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
        print("SUMMARY:", dict(cnt))


if __name__ == "__main__":
    main()
