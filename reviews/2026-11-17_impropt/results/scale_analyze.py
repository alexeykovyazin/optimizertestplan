"""analyze.py <scale csv> <manifest yaml> <out summary csv>: interim analysis of a partial scale run."""
import csv, re, statistics, sys

csv.field_size_limit(10 ** 9)
src, manifest, out = sys.argv[1:4]

# manifest: id, tables, true_cardinality (a flat YAML list, parsed by lines)
man = {}
cur = None
for line in open(manifest, encoding='utf-8'):
    m = re.match(r'- id: (\S+)', line)
    if m:
        cur = man.setdefault(m.group(1), {})
        continue
    m = re.match(r'  (tables|true_cardinality): (\S+)', line)
    if m and cur is not None:
        cur[m.group(1)] = int(m.group(2))

rows = list(csv.DictReader(open(src, encoding='utf-8', errors='replace', newline='')))
q = {}
for r in rows:
    d = q.setdefault(r['qid'], {})
    if r['kind'] == 'prepare':
        d['dplan'] = r['dplan'] or ''
        d['prepare_ms'] = float(r['prepare_ms'] or 0)
    elif r['kind'] == 'measured':
        d['status'] = r['status']
        d['sec'] = float(r['exec_ms']) / 1000 if r['exec_ms'] else None
        d['check'] = r['check']

res = []
for qid in sorted(q):
    d = q[qid]
    if 'status' not in d:
        continue
    plan = d.get('dplan', '')
    est = None
    m = re.search(r'Aggregate[^\n]*\n\s*-> [^\n]*\(rows=([0-9.]+)\)', plan)
    if m:
        est = float(m.group(1))
    true = man[qid]['true_cardinality']
    qerr = None
    if est is not None:
        qerr = max(est, 1.0) / max(true, 1.0)
    res.append(dict(qid=qid, tables=man[qid]['tables'], true=true, status=d['status'], sec=d['sec'],
                    check=d['check'], est=est, ratio=qerr,
                    bhj=plan.count('Batch Hash Join'), hj=len(re.findall(r'-> Hash Join', plan)),
                    nl=plan.count('Nested Loop Join')))


def pct(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(round(p * (len(v) - 1))))] if v else float('nan')


ok = [r for r in res if r['status'] == 'ok']
to = [r for r in res if r['status'] != 'ok']
print('measured %d, ok %d, timeout %d, match %d, mismatch %d' % (
    len(res), len(ok), len(to), sum(r['check'] == 'match' for r in res), sum(r['check'] == 'MISMATCH' for r in res)))
secs = [r['sec'] for r in ok]
print('ok: sum %.0f s, median %.2f s, p90 %.1f s, max %.1f s' % (sum(secs), statistics.median(secs), pct(secs, .9), max(secs)))

print('\n== time buckets ==')
for lo, hi, name in ((0, 1, '< 1 s'), (1, 10, '1-10 s'), (10, 60, '10-60 s'), (60, 300, '60-300 s')):
    n = [r for r in ok if lo <= r['sec'] < hi]
    print('%-9s %3d  sum %.0f s' % (name, len(n), sum(r['sec'] for r in n)))
print('%-9s %3d' % ('timeout', len(to)))

print('\n== by tables ==')
for t in sorted(set(r['tables'] for r in res)):
    a = [r for r in res if r['tables'] == t]
    o = [r['sec'] for r in a if r['status'] == 'ok']
    print('tables %d: n %3d, timeout %2d, median %.2f s, p90 %.1f s, max %.1f s, sum %.0f s' % (
        t, len(a), len(a) - len(o), statistics.median(o) if o else 0, pct(o, .9) if o else 0, max(o) if o else 0, sum(o)))

print('\n== by true cardinality ==')
edges = [(0, 1e6, '< 1M'), (1e6, 1e7, '1M-10M'), (1e7, 1e8, '10M-100M'), (1e8, 1e9, '100M-1B'), (1e9, 1e10, '1B-10B'), (1e10, 1e15, '>= 10B')]
for lo, hi, name in edges:
    a = [r for r in res if lo <= r['true'] < hi]
    o = [r for r in a if r['status'] == 'ok']
    s = [r['sec'] for r in o]
    thr = [r['true'] / r['sec'] / 1e6 for r in o if r['sec'] > 0.5]
    print('%-9s n %3d, timeout %2d, median %.2f s, max %.1f s, Mrows/s median %.2f' % (
        name, len(a), len(a) - len(o), statistics.median(s) if s else 0, max(s) if s else 0,
        statistics.median(thr) if thr else 0))

print('\n== timeouts ==')
for r in sorted(to, key=lambda r: r['true']):
    print('%s tables %d true %s est %s bhj %d hj %d nl %d' % (
        r['qid'], r['tables'], format(r['true'], ','), format(int(r['est']), ',') if r['est'] else '-', r['bhj'], r['hj'], r['nl']))

print('\n== slowest ok ==')
for r in sorted(ok, key=lambda r: -r['sec'])[:12]:
    print('%s %.1f s tables %d true %s Mrows/s %.2f bhj %d hj %d nl %d' % (
        r['qid'], r['sec'], r['tables'], format(r['true'], ','), r['true'] / r['sec'] / 1e6, r['bhj'], r['hj'], r['nl']))

print('\n== largest results that finished ==')
for r in sorted(ok, key=lambda r: -r['true'])[:6]:
    print('%s %.1f s true %s Mrows/s %.2f' % (r['qid'], r['sec'], format(r['true'], ','), r['true'] / r['sec'] / 1e6))

print('\n== plan operators ==')
print('queries with BHJ: %d (timeouts %d); with HJ: %d; with NL: %d; no join: %d' % (
    sum(r['bhj'] > 0 for r in res), sum(r['bhj'] > 0 for r in to), sum(r['hj'] > 0 for r in res),
    sum(r['nl'] > 0 for r in res), sum(not (r['bhj'] or r['hj'] or r['nl']) for r in res)))

print('\n== estimate / true (the top node under the aggregate) ==')
e = [r for r in res if r['ratio'] is not None]
qe = [max(r['ratio'], 1 / r['ratio']) for r in e]
print('n %d, q-error median %.2f, p90 %.1f, p99 %.0f, max %.0f' % (len(qe), statistics.median(qe), pct(qe, .9), pct(qe, .99), max(qe)))
print('within x2: %d, within x10: %d, over x10: %d, under /10: %d' % (
    sum(x <= 2 for x in qe), sum(x <= 10 for x in qe), sum(r['ratio'] > 10 for r in e), sum(r['ratio'] < 0.1 for r in e)))
for t in sorted(set(r['tables'] for r in e)):
    a = [max(r['ratio'], 1 / r['ratio']) for r in e if r['tables'] == t]
    print('tables %d: n %3d, q-error median %.2f, p90 %.1f, max %.0f' % (t, len(a), statistics.median(a), pct(a, .9), max(a)))
print('worst estimates:')
for r in sorted(e, key=lambda r: -max(r['ratio'], 1 / r['ratio']))[:6]:
    print('  %s tables %d true %s est %s ratio %.3g %s %s' % (
        r['qid'], r['tables'], format(r['true'], ','), format(int(r['est']), ','), r['ratio'], r['status'],
        ('%.1f s' % r['sec']) if r['sec'] else ''))

print('\n== not run (362-500) ==')
rest = [man[k] for k in sorted(man) if k not in q or 'status' not in q[k]]
print('n %d; by tables: %s' % (len(rest), {t: sum(1 for x in rest if x['tables'] == t) for t in sorted(set(x['tables'] for x in rest))}))
print('true >= 1B: %d, >= 10B: %d, max %s' % (sum(x['true_cardinality'] >= 1e9 for x in rest),
      sum(x['true_cardinality'] >= 1e10 for x in rest), format(max(x['true_cardinality'] for x in rest), ',')))

with open(out, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(['qid', 'tables', 'true_cardinality', 'status', 'exec_s', 'check', 'estimate', 'estimate_to_true',
                'batch_hash_joins', 'hash_joins', 'nested_loops'])
    for r in res:
        w.writerow([r['qid'], r['tables'], r['true'], r['status'], '' if r['sec'] is None else '%.3f' % r['sec'],
                    r['check'], '' if r['est'] is None else '%.0f' % r['est'],
                    '' if r['ratio'] is None else '%.4g' % r['ratio'], r['bhj'], r['hj'], r['nl']])
