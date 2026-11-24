"""dump_pg2.py <dir with pe_tpch_NN.json (raw psql output)> <out.txt> - compact text of EXPLAIN (ANALYZE) JSON plans
with the inclusive time of every node (ms, all loops)."""
import glob
import json
import os
import sys

src, dst = sys.argv[1], sys.argv[2]
KEYS = ["Hash Cond", "Merge Cond", "Index Cond", "Join Filter", "Filter", "Group Key", "Sort Key", "Sort Method",
        "Subplan Name"]


def walk(p, depth, out):
    name = p["Node Type"]
    for k in ("Strategy", "Partial Mode", "Join Type"):
        if k in p and p[k] not in ("Plain", "Simple"):
            name += " " + str(p[k])
    if p.get("Parallel Aware"):
        name = "Parallel " + name
    if "Relation Name" in p:
        name += " on " + p["Relation Name"]
        if p.get("Alias") and p["Alias"] != p["Relation Name"]:
            name += " " + p["Alias"]
    if "Index Name" in p:
        name += " using " + p["Index Name"]
    extra = ""
    if "Workers Planned" in p:
        extra += " workers=%s/%s" % (p.get("Workers Launched"), p["Workers Planned"])
    if "Parent Relationship" in p and p["Parent Relationship"] not in ("Outer", "Inner"):
        extra += " [" + p["Parent Relationship"] + "]"
    tm = ""
    if "Actual Total Time" in p:
        tm = " t=%.0fms" % (p["Actual Total Time"] * p.get("Actual Loops", 1))
    out.write("%s-> %s  (est=%s act=%s loops=%s%s)%s\n" % (
        "  " * depth, name, p.get("Plan Rows"), p.get("Actual Rows"), p.get("Actual Loops"), tm, extra))
    for k in KEYS:
        if k in p:
            v = p[k]
            if isinstance(v, list):
                v = ", ".join(v)
            out.write("%s     %s: %s\n" % ("  " * depth, k, str(v)[:230]))
    if "Rows Removed by Filter" in p:
        out.write("%s     removed by filter: %s\n" % ("  " * depth, p["Rows Removed by Filter"]))
    if p.get("Peak Memory Usage"):
        out.write("%s     memory: %s kB, batches: %s\n" % ("  " * depth, p["Peak Memory Usage"], p.get("Hash Batches")))
    for c in p.get("Plans", []):
        walk(c, depth + 1, out)


with open(dst, "w", encoding="utf-8") as out:
    for f in sorted(glob.glob(os.path.join(src, "pe_tpch_*.json"))):
        raw = open(f, encoding="utf-8", errors="replace").read()
        qid = os.path.basename(f)[3:-5]
        a, b = raw.find("["), raw.rfind("]")
        if a < 0 or b < 0:
            out.write("##### %s NO PLAN: %s\n" % (qid, raw[:200].replace("\n", " ")))
            continue
        d = json.loads(raw[a:b + 1])[0]
        jit = d.get("JIT")
        out.write("##### %s exec_ms=%s planning_ms=%s jit=%s\n" % (
            qid, d.get("Execution Time"), d.get("Planning Time"),
            ("functions=%s total=%.0fms" % (jit["Functions"], jit["Timing"]["Total"])) if jit else None))
        walk(d["Plan"], 0, out)
print("ok")
