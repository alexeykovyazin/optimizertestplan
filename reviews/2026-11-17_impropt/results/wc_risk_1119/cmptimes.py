"""cmptimes.py - the timing of the variants of the worst case rule.
The time of a query is looked up by its plan text: the new runs first (times/wct_*.csv), then the earlier stand
runs of the same plan. A timeout counts as 300 s."""
import csv, glob, os, re, sys

args = sys.argv[1:]
sys.argv = sys.argv[:1]
exec(open('cmpplans.py').read().split("print('plans loaded:'")[0])
csv.field_size_limit(10 ** 9)
SPR = SP.replace('wc/', '')
norm = lambda p: re.sub(r'\s+', ' ', p or '').strip()

NEW, OLD = {}, {}


def feed(path, store, tag):
    if not os.path.isfile(path):
        return
    plan = {}
    for r in csv.DictReader(open(path, encoding='utf-8', errors='replace', newline='')):
        if r['kind'] == 'prepare':
            plan[r['qid']] = norm(r['plan'])
        elif r['kind'] == 'measured' and r['qid'] in plan:
            ok = r['status'] == 'ok' and r['exec_ms']
            store.setdefault((r['qid'], plan[r['qid']]), (float(r['exec_ms']) / 1000 if ok else 300.0,
                                                          r['status'], r['check'], tag))


for f in sorted(glob.glob(SP + 'times/wct_*.csv')):
    feed(f, NEW, os.path.basename(f)[4:-4])
for f in ('risk/g5ch_pagemiss.csv', 'risk/g5ch_fusedcond.csv', 'risk/pmch_pagemiss.csv', 'risk/pmch_fusedcond.csv',
          'risk/joblight_pagemiss.csv', 'risk/joblight_fusedcond.csv', 'risk/ceb_full_fusedcond.csv',
          'sc/scale_c1.csv'):
    feed(SPR + f, OLD, f)


def t(tag, q, new_only=False):
    k = (q, P[tag][q])
    return NEW.get(k) or (None if new_only else OLD.get(k))


def suite(q):
    return 'jl' if q.startswith('job_light') else 'ceb' if q.startswith('ceb') else 'scale'


print('new measurements: %d, earlier: %d' % (len(NEW), len(OLD)))
bad = [(k[0], v[1], v[2], v[3]) for k, v in NEW.items() if v[2] not in ('match', 'n/a') and v[1] == 'ok']
print('result mismatches in the new runs:', bad[:10])

for e in ('wb', 'w42'):
    for v in ('v1', 'v2', 'v3'):
        tag, base = '%s_%s' % (e, v), e + '_v0'
        d = [q for q in diff(base, tag)]
        have = [q for q in d if t(base, q, True) and t(tag, q, True)]
        if not have:
            continue
        a = sum(t(base, q)[0] for q in have)
        b = sum(t(tag, q)[0] for q in have)
        fast = [q for q in have if t(tag, q)[0] * 1.5 < t(base, q)[0]]
        slow = [q for q in have if t(tag, q)[0] > t(base, q)[0] * 1.5]
        to_a = sum(1 for q in have if t(base, q)[1] != 'ok')
        to_b = sum(1 for q in have if t(tag, q)[1] != 'ok')
        print('\n%s against %s: %d changed, %d measured: %.0f -> %.0f s; faster x1.5: %d, slower x1.5: %d; '
              'not ok: %d -> %d' % (tag, base, len(d), len(have), a, b, len(fast), len(slow), to_a, to_b))
        for s in ('jl', 'ceb', 'scale'):
            hs = [q for q in have if suite(q) == s]
            if hs:
                print('   %-5s n=%2d  %.0f -> %.0f s' % (s, len(hs), sum(t(base, q)[0] for q in hs),
                                                        sum(t(tag, q)[0] for q in hs)))
        top = sorted(have, key=lambda q: t(tag, q)[0] - t(base, q)[0])
        print('   best: ' + ', '.join('%s %.1f->%.1f' % (q, t(base, q)[0], t(tag, q)[0]) for q in top[:5]))
        print('   worst: ' + ', '.join('%s %.1f->%.1f' % (q, t(base, q)[0], t(tag, q)[0]) for q in top[-5:][::-1]))

# all the 691 queries, every configuration, by the plan lookup
cfg = [c for c in ('wb_v0', 'wb_v1', 'wb_v2', 'wb_v3', 'w42_v0', 'w42_v1', 'w42_v2', 'w42_v3') if c in P]
common = [q for q in ids if all(t(c, q) for c in cfg)]
print('\n== all the queries with a known time in every configuration: %d of %d' % (len(common), len(ids)))
for s in ('jl', 'ceb', 'scale', 'all'):
    qs = [q for q in common if s == 'all' or suite(q) == s]
    print('%-5s n=%3d  ' % (s, len(qs)) + '  '.join('%s %.0f' % (c, sum(t(c, q)[0] for q in qs)) for c in cfg))
miss = {c: sum(1 for q in ids if not t(c, q)) for c in cfg}
print('queries without a time:', miss)
if args:
    for q in args:
        print(q, '  '.join('%s %s' % (c, ('%.1f' % t(c, q)[0]) if t(c, q) else '-') for c in cfg))

# the checksums of a query must be the same in every new run
CS = {}
for f in sorted(glob.glob(SP + 'times/wct_*.csv')):
    for r in csv.DictReader(open(f, encoding='utf-8', errors='replace', newline='')):
        if r['kind'] == 'measured' and r['status'] == 'ok':
            CS.setdefault(r['qid'], set()).add((r['rows'], r['checksum']))
print('queries with different checksums between the new runs:', [q for q, s in CS.items() if len(s) > 1], 'of', len(CS))
print('statuses:', {os.path.basename(f)[4:-4]: sorted(set(r['status'] for r in csv.DictReader(open(f, encoding='utf-8', errors='replace', newline='')) if r['kind'] == 'measured')) for f in sorted(glob.glob(SP + 'times/wct_*.csv'))})
