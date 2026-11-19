import json, re, statistics
m = json.load(open('e6_meta.json')); rows = json.load(open('e6_rows.json'))
v = {}
for line in open('out/p3_e6c.txt', encoding='utf-8', errors='replace'):
    g = re.match(r'^([KS]_J\d+\w*)\s+(\d+)', line)
    if g: v[g.group(1)] = float(g.group(2))
qe = lambda x: max(x, 1 / x)
out = []
for r in rows:
    d = m['Q'][r['q']]; facts = d['facts']; j = d['j']
    if len(facts) < 2: continue
    K = v['K_' + j]; prod = 1.0
    for c in facts: prod *= v['S_%s_%s' % (j, c[2:])]
    corr = r['junf'] * K ** (len(facts) - 1) / prod
    r['corr'] = corr; r['other'] = r['e_eng'] / (corr * r['resid']); out.append(r)
json.dump(out, open('e6_decomp.json', 'w'), indent=1)
print('n', len(out))
for nf in (2, 3, 4):
    g = [r for r in out if r['nf'] == nf]
    print('facts=%d n=%2d median: engine %.1f corr %.1f resid(q-err) %.2f other %.2f | resid<=2: %d <=3: %d >3: %d >10: %d | resid<1 (over): %d, <1/3: %d' % (
        nf, len(g), statistics.median(r['e_eng'] for r in g), statistics.median(r['corr'] for r in g),
        statistics.median(qe(r['resid']) for r in g), statistics.median(r['other'] for r in g),
        sum(qe(r['resid']) <= 2 for r in g), sum(qe(r['resid']) <= 3 for r in g), sum(qe(r['resid']) > 3 for r in g), sum(qe(r['resid']) > 10 for r in g),
        sum(r['resid'] < 1 for r in g), sum(r['resid'] < 1/3 for r in g)))
g = out
print('all n=%d median engine %.1f corr %.1f resid q-err %.2f other %.2f; resid<=2: %d, <=3: %d, 3-10: %d, >10: %d; corr > resid q-err: %d' % (len(g), statistics.median(r['e_eng'] for r in g),
    statistics.median(r['corr'] for r in g), statistics.median(qe(r['resid']) for r in g), statistics.median(r['other'] for r in g),
    sum(qe(r['resid']) <= 2 for r in g), sum(qe(r['resid']) <= 3 for r in g), sum(3 < qe(r['resid']) <= 10 for r in g), sum(qe(r['resid']) > 10 for r in g), sum(r['corr'] > qe(r['resid']) for r in g)))
print('distinct corr by set:')
seen = {}
for r in out: seen[tuple(m['Q'][r['q']]['facts'])] = r['corr']
for k, c in sorted(seen.items(), key=lambda x: (len(x[0]), x[0])): print('  ', '+'.join(x[2:] for x in k), '%.1f' % c)
for q in ('scale_014', 'scale_351', 'job_light_051'):
    r = [x for x in out if x['q'] == q][0]; print(q, 'engine %.1f corr %.1f resid %.2f other %.2f' % (r['e_eng'], r['corr'], r['resid'], r['other']))
print('other: min %.2f max %.1f; other>3: %d; other<1/3: %d' % (min(r['other'] for r in out), max(r['other'] for r in out), sum(r['other'] > 3 for r in out), sum(r['other'] < 1/3 for r in out)))
