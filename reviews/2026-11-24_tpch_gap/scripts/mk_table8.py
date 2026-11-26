"""mk_table8.py <dir with the results of 24.11> <dir with the tpchgap_par_* results> - the timing table of the 22
TPC-H queries for the run with the PostgreSQL parity settings (DefaultDbCachePages = 128K, UseFileSystemCache = true,
one connection held open), next to the first run (cache 50000 pages)."""
import csv
import os
import statistics
import sys

csv.field_size_limit(10**9)
old, par = sys.argv[1], sys.argv[2]


def fb(path):
    """qid -> dict(ms=median of the measured runs or None, n, lo, hi, status, sum, plan)"""
    acc, plans = {}, {}
    for r in csv.DictReader(open(path, encoding="utf-8", errors="replace")):
        if r["kind"] == "prepare":
            plans[r["qid"]] = r["plan_hash"]
        if r["kind"] == "measured":
            acc.setdefault(r["qid"], []).append(r)
    out = {}
    for q, rows in acc.items():
        ok = [float(r["exec_ms"]) for r in rows if r["status"] == "ok"]
        sums = {r["checksum"] for r in rows if r["status"] == "ok"}
        out[q] = dict(ms=statistics.median(ok) if ok else None, n=len(ok), lo=min(ok) if ok else None,
                      hi=max(ok) if ok else None, status=rows[0]["status"], sum="/".join(sorted(sums)),
                      plan=plans.get(q, ""))
    return out


def pg(path):
    acc = {}
    for r in csv.DictReader(open(path, encoding="utf-8")):
        if r["ms"] and not r["error"]:
            acc.setdefault((r["qid"], r["mode"]), []).append(float(r["ms"]))
    return {k: statistics.median(v) for k, v in acc.items()}


def s(d, q):
    if q not in d:
        return "-"
    return "%.2f" % (d[q]["ms"] / 1000) if d[q]["ms"] is not None else d[q]["status"]


o_nv = fb(os.path.join(old, "tpchgap_nv_orig_tpch.csv"))
o_dp = fb(os.path.join(old, "tpchgap_nv_dp_tpch.csv"))
o_rw = fb(os.path.join(old, "tpchgap_rw_tpch.csv"))
o_rw4 = fb(os.path.join(old, "tpchgap_rw4_tpch.csv"))
o_rel = fb(os.path.join(old, "flat_rel_tpch.csv"))
o_new = fb(os.path.join(old, "flat_new_tpch.csv"))
p_nv = fb(os.path.join(par, "tpchgap_par_nv_tpch.csv"))
p_slow = fb(os.path.join(par, "tpchgap_par_slow_tpch.csv"))
p_dp = fb(os.path.join(par, "tpchgap_par_dp_tpch.csv"))
p_rel = fb(os.path.join(par, "tpchgap_par_rel_tpch.csv"))
p_new = fb(os.path.join(par, "tpchgap_par_new_tpch.csv"))
p_rw = fb(os.path.join(par, "tpchgap_par_rw_tpch.csv"))
p_rw4 = fb(os.path.join(par, "tpchgap_par_rw4_tpch.csv"))
pgt = pg(os.path.join(old, "tpchgap_pg_times.csv"))

tot = {}


def add(name, v):
    tot[name] = tot.get(name, 0.0) + (v if v is not None else float("nan"))


print("| Q | PGpar | PGser | nv old | nv par | dp old | dp par | rel old | rel par | new old | new par | par/PGser |"
      " spread par | n | sum= | plan= | dpplan= |")
for i in range(1, 23):
    q = "tpch_%02d" % i
    pp, ps = pgt.get((q, "par")), pgt.get((q, "ser"))
    n = p_nv.get(q) or p_slow.get(q)
    d = dict(p_nv)
    d.update(p_slow)
    ratio = "%.1f" % (n["ms"] / ps) if n and n["ms"] and ps else "-"
    spread = "%.2f-%.2f" % (n["lo"] / 1000, n["hi"] / 1000) if n and n["ms"] else "-"
    same = (n["sum"] == o_nv[q]["sum"]) if n and q in o_nv and n["ms"] else "-"
    plan = (n["plan"] == o_nv[q]["plan"]) if n and q in o_nv else "-"
    dplan = (p_dp[q]["plan"] == p_nv[q]["plan"]) if q in p_dp and q in p_nv else "-"
    print("| %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
        i, "%.2f" % (pp / 1000) if pp else "-", "%.2f" % (ps / 1000) if ps else "-", s(o_nv, q), s(d, q),
        s(o_dp, q), s(p_dp, q), s(o_rel, q), s(p_rel, q), s(o_new, q), s(p_new, q), ratio, spread,
        n["n"] if n else "-", same, plan, dplan))
    if q in p_nv and p_nv[q]["ms"] is not None and pp and ps:
        add("pgp", pp)
        add("pgs", ps)
        for name, dd in (("nv_old", o_nv), ("nv_par", p_nv), ("dp_old", o_dp), ("dp_par", p_dp), ("rel_old", o_rel),
                         ("rel_par", p_rel), ("new_old", o_new), ("new_par", p_new)):
            add(name, dd[q]["ms"] if q in dd else None)
print("totals:", {k: round(v / 1000, 2) for k, v in tot.items()})

print("\nrewritten queries: qid | old | par | n | spread | checksum equal to the original (par run) | to the old rw run")
after = {}
for name, o, p in (("rw", o_rw, p_rw), ("rw4", o_rw4, p_rw4)):
    for q in sorted(p):
        orig = "tpch_" + q.split("_")[1]
        base = p_nv.get(orig)
        eq = (base["sum"] == p[q]["sum"]) if base and base["ms"] else "n/a"
        eqo = (o[q]["sum"] == p[q]["sum"]) if q in o else "-"
        print("| %s | %s | %s | %s | %.2f-%.2f | %s | %s | orig par %s |" % (
            q, s(o, q), s(p, q), p[q]["n"], p[q]["lo"] / 1000, p[q]["hi"] / 1000, eq, eqo, s(p_nv, orig)))
        after.setdefault(orig, {})[name] = p[q]["ms"]

rw4_ids = sorted(p_rw4)
print("rw4 sum old orig %.2f -> old rw4 %.2f; par orig %.2f -> par rw4 %.2f" % (
    sum(o_nv["tpch_" + q[4:]]["ms"] for q in rw4_ids) / 1000, sum(o_rw4[q]["ms"] for q in rw4_ids) / 1000,
    sum(p_nv["tpch_" + q[4:]]["ms"] for q in rw4_ids) / 1000, sum(p_rw4[q]["ms"] for q in rw4_ids) / 1000))

# the "after" column: the best of the rewritten variants and of JoinOrderDP, per query
best_total = 0.0
print("\nafter column (par): Q | orig | rw | rw4 | dp | best")
for i in range(1, 23):
    q = "tpch_%02d" % i
    if q not in p_nv or p_nv[q]["ms"] is None:
        continue
    cand = {"orig": p_nv[q]["ms"]}
    cand.update(after.get(q, {}))
    if q in p_dp and p_dp[q]["ms"] is not None and p_dp[q]["plan"] != p_nv[q]["plan"]:
        cand["dp"] = p_dp[q]["ms"]
    best = min(cand, key=cand.get)
    best_total += cand[best]
    print("| %d | %s | %s |" % (i, " | ".join("%s %.2f" % (k, v / 1000) for k, v in cand.items()), best))
print("sum of best: %.2f" % (best_total / 1000))
