"""Compare the running/finished 15.11 probe (log or json) with the 08.11 results.
usage: python -I cmp_probe.py <regress_1115_up.log | .json> <regress_1108_all.json>
"""
import json, sys, re, ast

sys.stdout.reconfigure(encoding='utf-8')
new_path, old_path = sys.argv[1], sys.argv[2]
old = json.load(open(old_path, encoding='utf-8'))

new = {}
if new_path.endswith('.json'):
    raw = json.load(open(new_path, encoding='utf-8'))
    for q, r in raw.items():
        new[q] = r
else:
    rx = re.compile(r"^\[(ceb_\w+)\] (warmup\d|rep\d): (\{.*\})\s*$")
    for line in open(new_path, encoding='utf-8', errors='replace'):
        m = rx.match(line.strip())
        if not m:
            continue
        q, what, d = m.group(1), m.group(2), ast.literal_eval(m.group(3))
        new.setdefault(q, {})[what] = d


def best(rec):
    """best ms of the measured reps; None if all timed out"""
    ms = []
    for k, v in rec.items():
        if isinstance(v, dict) and k.startswith('rep') and v.get('ms') is not None:
            ms.append(v['ms'])
    if not ms and isinstance(rec.get('reps'), list):
        ms = [r['ms'] for r in rec['reps'] if r.get('ms') is not None]
    return min(ms) if ms else None


def val(rec):
    for k in ('rep2', 'rep1', 'warmup1'):
        v = rec.get(k)
        if isinstance(v, dict) and v.get('rows') is not None:
            return (v.get('rows'), v.get('val'))
    if isinstance(rec.get('reps'), list):
        for r in rec['reps']:
            if r.get('rows') is not None:
                return (r.get('rows'), r.get('val'))
    return None


if '--keys' in sys.argv:
    k = list(old)[0]
    print({kk: (type(vv).__name__) for kk, vv in old[k].items()})
    sys.exit(0)

print(f"{'query':12} {'08.11':>8} {'15.11':>8} {'ratio':>6}  result")
tot_o = tot_n = 0.0
for q in old:
    if q not in new:
        continue
    bo, bn = best(old[q]), best(new[q])
    vo, vn = val(old[q]), val(new[q])
    same = 'same' if vo == vn else f'DIFF old={vo} new={vn}'
    if vo is None or vn is None:
        same = f'n/a old={vo} new={vn}'
    r = f"{bn / bo:6.2f}" if bo and bn else '   -  '
    so = f"{bo / 1000:8.1f}" if bo else ' timeout'
    sn = f"{bn / 1000:8.1f}" if bn else ' timeout'
    if bo and bn and q.startswith('ceb_7a'):
        tot_o += bo; tot_n += bn
    print(f"{q[4:]:12} {so} {sn} {r}  {same[:110]}")
print(f"7a sum (both measured): 08.11 {tot_o / 1000:.0f} s, 15.11 {tot_n / 1000:.0f} s")
