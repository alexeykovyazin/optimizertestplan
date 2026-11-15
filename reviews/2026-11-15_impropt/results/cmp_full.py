"""cmp_full.py <new.csv> <label=old.csv> ...  - compares a full CEB run with earlier runs of the same stand.
Prints: totals, result check (checksum against each older run), the biggest regressions and wins."""
import csv, sys, math

sys.stdout.reconfigure(encoding='utf-8')
csv.field_size_limit(10 ** 9)


def load(p):
    res = {}
    for r in csv.DictReader(open(p, encoding='utf-8')):
        if r['kind'] != 'measured':
            continue
        res[r['qid']] = r          # the last measured row wins
    return res


new = load(sys.argv[1])
olds = [(a.split('=')[0], load(a.split('=')[1])) for a in sys.argv[2:]]
ok = [q for q, r in new.items() if r['status'] == 'ok']
to = [q for q, r in new.items() if r['status'] != 'ok']
print(f"new: measured {len(new)}, ok {len(ok)}, timeout/err {len(to)}: {' '.join(x[4:] for x in sorted(to))}")
print('check vs baseline:', {c: sum(1 for r in new.values() if r['check'] == c) for c in sorted({r['check'] for r in new.values()})})
for label, old in olds:
    both = [q for q in new if q in old]
    same = [q for q in both if new[q]['status'] == 'ok' and old[q]['status'] == 'ok' and new[q]['checksum'] == old[q]['checksum']]
    diff = [q for q in both if new[q]['status'] == 'ok' and old[q]['status'] == 'ok' and new[q]['checksum'] != old[q]['checksum']]
    bo = [q for q in both if new[q]['status'] == 'ok' and old[q]['status'] == 'ok']
    tn = sum(float(new[q]['exec_ms']) for q in bo) / 1000
    tol = sum(float(old[q]['exec_ms']) for q in bo) / 1000
    gm = math.exp(sum(math.log(max(float(new[q]['exec_ms']), 1) / max(float(old[q]['exec_ms']), 1)) for q in bo) / max(len(bo), 1))
    newto = [q for q in both if new[q]['status'] != 'ok' and old[q]['status'] == 'ok']
    oldto = [q for q in both if new[q]['status'] == 'ok' and old[q]['status'] != 'ok']
    print(f"\n== vs {label}: common {len(both)}, both ok {len(bo)}; same checksum {len(same)}, DIFFERENT checksum {len(diff)}: {' '.join(x[4:] for x in sorted(diff))}")
    print(f"   sum of both-ok: new {tn:.0f} s, {label} {tol:.0f} s; geomean new/{label} = {gm:.3f}")
    print(f"   timeout only in new: {' '.join(x[4:] for x in sorted(newto))} | only in {label}: {' '.join(x[4:] for x in sorted(oldto))}")
    rat = sorted(((float(new[q]['exec_ms']) / max(float(old[q]['exec_ms']), 1), q) for q in bo), reverse=True)
    print('   slower x2+ (and >1 s): ' + '; '.join(f"{q[4:]} {float(old[q]['exec_ms'])/1000:.1f}->{float(new[q]['exec_ms'])/1000:.1f}" for r, q in rat if r >= 2 and float(new[q]['exec_ms']) > 1000)[:900])
    print('   faster x2+ (and >1 s): ' + '; '.join(f"{q[4:]} {float(old[q]['exec_ms'])/1000:.1f}->{float(new[q]['exec_ms'])/1000:.1f}" for r, q in reversed(rat) if r <= 0.5 and float(old[q]['exec_ms']) > 1000)[:900])
