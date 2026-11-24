r"""tg_pg.py prep | sum - PostgreSQL side of the job tpchgap.cmd.

prep: makes the plan scripts E:\results\tpchgap_pg\sql\pe_tpch_NN.sql from the reference scripts
      E:\pgdumps\tpchref\pe_tpch_NN.sql: EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) with a 300 s timeout;
      queries 17 and 20 get a plain EXPLAIN (FORMAT JSON), they do not end.
sum:  reads the "Time:" lines of the timing runs and writes E:\results\tpchgap_pg_times.csv.
"""
import csv
import glob
import os
import re
import sys

SRC = r"E:\pgdumps\tpchref"
PGDIR = r"E:\results\tpchgap_pg"
OLD = "EXPLAIN (ANALYZE, FORMAT JSON, TIMING OFF)"


def prep() -> None:
    for f in sorted(glob.glob(os.path.join(SRC, "pe_tpch_*.sql"))):
        name = os.path.basename(f)
        txt = open(f, encoding="utf-8").read()
        if OLD not in txt:
            print("no EXPLAIN marker:", name)
            continue
        slow = name in ("pe_tpch_17.sql", "pe_tpch_20.sql")
        new = "EXPLAIN (FORMAT JSON)" if slow else "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)"
        txt = txt.replace(OLD, new)
        txt = re.sub(r"SET statement_timeout = '\d+s';", "SET statement_timeout = '300s';", txt)
        with open(os.path.join(PGDIR, "sql", name), "w", encoding="utf-8", newline="\n") as out:
            out.write(txt)
    print("prep done")


def summary() -> None:
    time_re = re.compile(r"^Time: ([\d.,]+) ms")
    rows = []
    for d in sorted(glob.glob(os.path.join(PGDIR, "*_r[0-9]"))):
        mode, rnd = os.path.basename(d).rsplit("_r", 1)
        for f in sorted(glob.glob(os.path.join(d, "q_tpch_*.csv"))):
            qid = os.path.basename(f)[2:-4]
            times = []
            nrows = 0
            for ln in open(f, encoding="utf-8", errors="replace"):
                m = time_re.match(ln)
                if m:
                    times.append(float(m.group(1).replace(",", ".")))
                elif ln.strip():
                    nrows += 1
            err = open(f[:-4] + ".err", encoding="utf-8", errors="replace").read().strip()
            for ln in err.splitlines():
                m = time_re.match(ln)
                if m:
                    times.append(float(m.group(1).replace(",", ".")))
            # query 15: create view, the select, drop view - the select is the second statement
            ms = None
            if times:
                ms = times[1] if qid == "tpch_15" and len(times) >= 2 else times[-1]
            bad = [ln for ln in err.splitlines() if "ERROR" in ln]
            rows.append([qid, mode, rnd, ms, nrows, (bad[0][:200] if bad else "")])
    with open(r"E:\results\tpchgap_pg_times.csv", "w", newline="", encoding="utf-8") as out:
        w = csv.writer(out)
        w.writerow(["qid", "mode", "round", "ms", "rows", "error"])
        w.writerows(rows)
    print("sum done:", len(rows))


if __name__ == "__main__":
    prep() if sys.argv[1] == "prep" else summary()
