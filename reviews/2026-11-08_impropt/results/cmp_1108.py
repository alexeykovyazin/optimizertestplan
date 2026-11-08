"""Compare regress_1108 JSON with p4, p5, fix-branch CSVs and the 06.11 upstream 7a JSON.
python -I cmp_1108.py NEW.json [SP_DIR]"""
import csv, json, math, os, sys

RES = r"E:\Projects_Big\optimizertestplan\results"
sp = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(sys.argv[1]))


def load_csv(p):
    out = {}
    for r in csv.DictReader(open(p, encoding="utf-8")):
        if r["kind"] == "measured":
            out[r["qid"]] = (r["status"], float(r["exec_ms"]) if r["exec_ms"] else None, r["rows"], r["check"])
    return out


p4 = load_csv(os.path.join(RES, "ceb_full_1027", "ceb_full_1027.csv"))
p5 = load_csv(os.path.join(RES, "ceb_full_1102", "ceb_full_1102.csv"))
fx = load_csv(os.path.join(sp, "ceb_full_1105fix.csv"))
up = json.load(open(os.path.join(sp, "ceb7a_1106up.json"), encoding="utf-8"))
new = json.load(open(sys.argv[1], encoding="utf-8"))


def s(ms):
    return "-" if ms is None else f"{ms/1000:.1f}"


def gm(xs):
    xs = [x for x in xs if x]
    return math.exp(sum(map(math.log, xs)) / len(xs)) if xs else float("nan")


print(f"{'qid':12} {'new':>7} {'p4':>6} {'p5':>6} {'up06':>6} {'fix':>6} {'x/p4':>6} {'x/p5':>6} {'x/up06':>6} bhj rows  ok")
r4, r5, ru = [], [], []
sums = {"new": 0, "p4": 0, "p5": 0, "up": 0, "fix": 0}
for q, rec in new.items():
    reps = rec.get("reps", [])
    ms = rec.get("ms")
    bad = [r.get("err") for r in reps if r.get("err")]
    rows = reps[0].get("rows") if reps else None
    val = reps[0].get("val") if reps else None
    a = p4.get(q, (None, None, None, None))
    b = p5.get(q, (None, None, None, None))
    f = fx.get(q, (None, None, None, None))
    u = up.get(q, {}).get("ms")
    u = float(u) if u else None
    uval = up.get(q, {}).get("reps", [{}])[0].get("val") if q in up else None
    ok = "?"
    if rows is not None and a[2]:
        ok = "ok" if str(rows) == str(a[2]) else f"ROWS {rows}!={a[2]}"
    if uval is not None and val is not None and uval != val:
        ok = f"VAL {val}!={uval}"
    x4 = ms / a[1] if ms and a[1] else None
    x5 = ms / b[1] if ms and b[1] else None
    xu = ms / u if ms and u else None
    if x4: r4.append(x4)
    if x5: r5.append(x5)
    if xu: ru.append(xu)
    if q.startswith("ceb_7a"):
        sums["new"] += ms or 300000; sums["p4"] += a[1] or 0; sums["p5"] += b[1] or 0
        sums["up"] += u or 0; sums["fix"] += f[1] or 0
    bhj = rec.get("dplan", "").count("Batch Hash Join")
    fmt = lambda x: "-" if x is None else f"{x:.2f}"
    print(f"{q[4:]:12} {s(ms):>7} {s(a[1]):>6} {s(b[1]):>6} {s(u):>6} {s(f[1]):>6} {fmt(x4):>6} {fmt(x5):>6} {fmt(xu):>6} {bhj:>3} {str(rows):>4}  {ok}{' ERR '+str(bad[0])[:60] if bad else ''}")
print(f"gm new/p4 {gm(r4):.3f} (n={len(r4)})  new/p5 {gm(r5):.3f}  new/up06 {gm(ru):.3f} (7a)")
print("7a sums s: " + "  ".join(f"{k} {v/1000:.0f}" for k, v in sums.items()))
