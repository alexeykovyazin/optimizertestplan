"""mk_table.py <dir with result CSVs> <dir with flat_*.csv> - the timing table of the 22 TPC-H queries."""
import csv
import os
import statistics
import sys

csv.field_size_limit(10**9)
res, flat = sys.argv[1], sys.argv[2]


def fb(path):
    """qid -> (median ms of the measured runs or None, status, rows)"""
    out = {}
    if not os.path.isfile(path):
        return out
    acc = {}
    for r in csv.DictReader(open(path, encoding="utf-8", errors="replace")):
        if r["kind"] != "measured":
            continue
        acc.setdefault(r["qid"], []).append(r)
    for q, rows in acc.items():
        ok = [float(r["exec_ms"]) for r in rows if r["status"] == "ok"]
        if ok:
            out[q] = (statistics.median(ok), "ok", rows[0]["rows"], len(ok), min(ok), max(ok))
        else:
            out[q] = (None, rows[0]["status"], None, 0, None, None)
    return out


def pg(path):
    out = {}
    if not os.path.isfile(path):
        return out
    acc = {}
    for r in csv.DictReader(open(path, encoding="utf-8")):
        if r["ms"] and not r["error"]:
            acc.setdefault((r["qid"], r["mode"]), []).append(float(r["ms"]))
    for k, v in acc.items():
        out[k] = (statistics.median(v), len(v), min(v), max(v))
    return out


nv = fb(os.path.join(res, "tpchgap_nv_orig_tpch.csv"))
nv.update(fb(os.path.join(res, "tpchgap_nv_slow_tpch.csv")))
dp = fb(os.path.join(res, "tpchgap_nv_dp_tpch.csv"))
rel = fb(os.path.join(flat, "flat_rel_tpch.csv"))
new = fb(os.path.join(flat, "flat_new_tpch.csv"))
pgt = pg(os.path.join(res, "tpchgap_pg_times.csv"))


def s(ms):
    return "-" if ms is None else ("%.2f" % (ms / 1000.0))


def cell(d, q):
    if q not in d:
        return "-"
    return s(d[q][0]) if d[q][0] is not None else d[q][1]


tot = {"pgp": 0.0, "pgs": 0.0, "nv": 0.0, "dp": 0.0, "rel": 0.0, "new": 0.0}
print("| Q | PG par | PG ser | FB nv | FB nv DP | FB rel | FB rel+71 | nv/PGpar | nv/PGser | spread nv | spread PGpar |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
for i in range(1, 23):
    q = "tpch_%02d" % i
    pp = pgt.get((q, "par"))
    ps = pgt.get((q, "ser"))
    n = nv.get(q)
    r1 = r2 = "-"
    if n and n[0] is not None:
        if pp:
            r1 = "%.1f" % (n[0] / pp[0])
        if ps:
            r2 = "%.1f" % (n[0] / ps[0])
    sp = "-"
    if n and n[0] is not None and n[3] > 1:
        sp = "%.2f-%.2f" % (n[4] / 1000, n[5] / 1000)
    spp = "%.2f-%.2f" % (pp[2] / 1000, pp[3] / 1000) if pp else "-"
    print("| %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
        i, s(pp[0]) if pp else "-", s(ps[0]) if ps else "-", cell(nv, q), cell(dp, q),
        cell(rel, q), cell(new, q), r1, r2, sp, spp))
    common = pp and ps and n and n[0] is not None
    if common:
        tot["pgp"] += pp[0]
        tot["pgs"] += ps[0]
        tot["nv"] += n[0]
        for name, d in (("dp", dp), ("rel", rel), ("new", new)):
            if q in d and d[q][0] is not None:
                tot[name] += d[q][0]
            else:
                tot[name] = float("nan")
print("totals over queries done by PG and FB nv:", {k: round(v / 1000, 1) for k, v in tot.items()})
