"""theta.py - how well the worst case of a join prefix predicts the real estimation error.
For every finished count(*) query of the scale and job-light sets: the final join estimate E, the true size A,
the worst sizes W = E * product of (worst / average rows per key) over the non-unique joins after the first stream.
Prints the fit of ln(A/E) by k (count of such joins), by ln(Wsb/E) and by ln(Wmax/E)."""
import csv, math, re, statistics, sys

csv.field_size_limit(10 ** 9)
SP = 'C:/Users/aleks/AppData/Local/Temp/claude/c255271938a7846a/58624a2e-45d9-4769-ae51-5e8b14b87350/scratchpad/'
B = 'E:/Projects_Big/optimizertestplan/bench/'

deg = {}
for line in open(SP + 'wc/wc_deg.txt', encoding='utf-8', errors='replace'):
    if line.startswith('DEG|'):
        _, t, ix, iid, n, sc, sc2, mx = line.strip().split('|')
        n, sc, sc2, mx = float(n), float(sc), float(sc2), float(mx)
        deg[ix] = dict(table=t, id=int(iid), avg=sc / n, sb=sc2 / sc, max=mx, keys=n, rows=sc)

MOVIE = {'CAST_INFO': 'MOVIE_ID_CAST_INFO', 'MOVIE_INFO': 'MOVIE_ID_MOVIE_INFO',
         'MOVIE_INFO_IDX': 'MOVIE_ID_MOVIE_INFO_IDX', 'MOVIE_KEYWORD': 'MOVIE_ID_MOVIE_KEYWORD',
         'MOVIE_COMPANIES': 'MOVIE_ID_MOVIE_COMPANIES'}
ALIAS = {'T': 'TITLE', 'CI': 'CAST_INFO', 'MI': 'MOVIE_INFO', 'MI_IDX': 'MOVIE_INFO_IDX', 'MK': 'MOVIE_KEYWORD',
         'MC': 'MOVIE_COMPANIES'}


def manifest(name):
    man, cur = {}, None
    for line in open(B + 'manifest/' + name, encoding='utf-8'):
        m = re.match(r'- id: (\S+)', line)
        if m:
            cur = man.setdefault(m.group(1), {})
            continue
        m = re.match(r'  (tables|true_cardinality): (\S+)', line)
        if m and cur is not None and m.group(2) != 'null':
            cur[m.group(1)] = int(m.group(2))
    return man


def load(path, man):
    q = {}
    for r in csv.DictReader(open(path, encoding='utf-8', errors='replace', newline='')):
        d = q.setdefault(r['qid'], {})
        if r['kind'] == 'prepare':
            d['plan'], d['dplan'] = r['plan'] or '', r['dplan'] or ''
    out = []
    for qid, d in q.items():
        true = man.get(qid, {}).get('true_cardinality')
        if not true or 'plan' not in d:
            continue
        # the estimate of the top join: the first join node of the detailed plan
        m = re.search(r'(?:Nested Loop Join|Hash Join|Batched Hash Join)[^\n]*\(rows=([0-9.eE+]+)\)', d['dplan'])
        if not m:
            continue
        est = float(m.group(1))
        order = [a for a in re.findall(r'[(, ]([A-Z_]+) (?:INDEX|NATURAL|ORDER)', d['plan']) if a in ALIAS]
        tabs = [ALIAS[a] for a in order]
        if len(tabs) < 2 or len(set(tabs)) != len(tabs):
            continue
        fan = [t for t in tabs[1:] if t != 'TITLE']
        out.append(dict(qid=qid, est=est, true=true, tabs=tabs, k=len(fan),
                        lsb=sum(math.log(deg[MOVIE[t]]['sb'] / deg[MOVIE[t]]['avg']) for t in fan),
                        lmx=sum(math.log(deg[MOVIE[t]]['max'] / deg[MOVIE[t]]['avg']) for t in fan),
                        lerr=math.log(true / max(est, 1.0))))
    return out


def fit(rows, key):
    """Least squares through the origin: lerr = theta * x. Returns theta, the RMSE of the fit, the RMSE of no fit."""
    xs = [r[key] for r in rows]
    ys = [r['lerr'] for r in rows]
    sxx = sum(x * x for x in xs)
    theta = sum(x * y for x, y in zip(xs, ys)) / sxx if sxx else 0
    rm = math.sqrt(sum((y - theta * x) ** 2 for x, y in zip(xs, ys)) / len(ys))
    r0 = math.sqrt(sum(y * y for y in ys) / len(ys))
    return theta, rm, r0


print('== key degrees (rows per key): index, keys, average, size-biased, max, sb/avg, max/avg')
for ix in sorted(deg, key=lambda i: (deg[i]['table'], i)):
    d = deg[ix]
    print('%-34s %9.0f %10.2f %12.1f %10.0f %8.1f %10.1f' % (ix, d['keys'], d['avg'], d['sb'], d['max'],
                                                             d['sb'] / d['avg'], d['max'] / d['avg']))

sets = [('scale', SP + 'sc/scale_c1.csv', 'scale.yaml'), ('job-light', SP + 'risk/joblight_fusedcond.csv', 'job-light.yaml')]
allrows = []
for name, path, man in sets:
    rows = load(path, manifest(man))
    allrows += rows
    print('\n== %s: %d queries with the true size and a join' % (name, len(rows)))
for name, rows in [('all', allrows)] + [('k=%d' % k, [r for r in allrows if r['k'] == k]) for k in range(0, 6)]:
    if len(rows) < 5:
        continue
    under = sum(1 for r in rows if r['lerr'] > math.log(2))
    over = sum(1 for r in rows if r['lerr'] < -math.log(2))
    med = math.exp(statistics.median(r['lerr'] for r in rows))
    p90 = math.exp(sorted(r['lerr'] for r in rows)[int(len(rows) * 0.9)])
    line = '%-5s n=%3d  A/E median %8.2f p90 %9.1f  under x2: %3d  over x2: %3d' % (name, len(rows), med, p90, under, over)
    if name == 'all' or rows[0]['k'] > 0:
        for key, label in (('k', 'const'), ('lsb', 'sb'), ('lmx', 'max')):
            th, rm, r0 = fit(rows, key)
            line += '  | %s: theta %.3f rmse %.2f' % (label, th, rm)
        line += '  (rmse of no correction %.2f)' % fit(rows, 'k')[2]
        inside_sb = sum(1 for r in rows if r['lerr'] <= r['lsb'])
        inside_mx = sum(1 for r in rows if r['lerr'] <= r['lmx'])
        line += '  A<=Wsb: %d, A<=Wmax: %d' % (inside_sb, inside_mx)
    print(line)

# the per-join constant the "const" fit means: exp(theta) per fan-out join; the current rule uses 2.0 as the
# risk multiplier, which is the square root of the implied worst ratio 4.0
th, rm, r0 = fit(allrows, 'k')
print('\nconst fit: error factor per non-unique join = %.2f' % math.exp(th))
print('worst rows of the 12 largest underestimates:')
for r in sorted(allrows, key=lambda r: -r['lerr'])[:12]:
    print('  %-14s k=%d A/E %10.1f  Wsb/E %12.1f  Wmax/E %14.1f  %s' % (r['qid'], r['k'], math.exp(r['lerr']),
          math.exp(r['lsb']), math.exp(r['lmx']), ','.join(r['tabs'])))

print('\n== quantiles of A/E by k, and the same per non-unique join (the k-th root)')
for k in range(1, 5):
    v = sorted(math.exp(r['lerr']) for r in allrows if r['k'] == k)
    if len(v) < 5:
        continue
    qs = [v[min(len(v) - 1, int(len(v) * p))] for p in (0.5, 0.75, 0.9, 0.95)]
    print('k=%d n=%3d  p50 %7.2f p75 %7.1f p90 %7.1f p95 %8.1f | per join: %5.2f %5.2f %5.2f %5.2f' % (
        (k, len(v)) + tuple(qs) + tuple(q ** (1.0 / k) for q in qs)))
