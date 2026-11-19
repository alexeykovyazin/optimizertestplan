"""parse.py: read isql LIST-mode outputs of the E-steps and print the result tables."""
import json, re, sys, statistics


def blocks(path):
    """Yield one dict per result row (LIST mode: 'NAME   value' lines, blank line between rows)."""
    cur = {}
    for line in open(path, encoding='utf-8', errors='replace'):
        line = line.rstrip('\r\n')
        m = re.match(r'^([A-Z_0-9$]+)\s+(\S.*)$', line)
        if m and not line.startswith(('Current memory', 'Delta memory', 'Max memory', 'Elapsed time',
                                      'Buffers', 'Reads', 'Writes', 'Fetches', 'Cpu', 'PLAN')):
            cur[m.group(1)] = m.group(2).strip()
        elif not line.strip():
            if cur:
                yield cur
                cur = {}
    if cur:
        yield cur


def elapsed(path):
    return [float(x) for x in re.findall(r'Elapsed time\s*=\s*([0-9.]+)', open(path, encoding='utf-8', errors='replace').read())]


def num(s):
    return float(s)


what = sys.argv[1]
if what == 'e6':
    meta = json.load(open('e6_meta.json'))
    N = {}
    F = {}
    J = {}
    for f in ('out/p3_e6a.txt', 'out/p3_e6b.txt'):
        for b in blocks(f):
            if b.get('TBL') == 'X3':
                J = {k: num(v) for k, v in b.items() if k.startswith('J')}
            elif 'TBL' in b:
                N[b['TBL']] = num(b['N'])
                F[b['TBL']] = {k: num(v) for k, v in b.items() if re.match(r'F\d+$', k)}
    nt = N['title']
    rows = []
    for q, d in meta['Q'].items():
        facts = d['facts']
        s = 1.0
        for t, k in d['filters']:
            s *= F[t][k] / N[t]
        junf = J[d['j']] if facts else nt
        if not facts:
            ideal = nt * s
        else:
            ideal = junf * s
        inv = {'C_CI': 'cast_info', 'C_MK': 'movie_keyword', 'C_MI': 'movie_info', 'C_MC': 'movie_companies', 'C_MII': 'movie_info_idx'}
        avg = nt * s
        for c in facts:
            avg *= N[inv[c]] / nt
        rows.append(dict(q=q, nt=len(d['tables']), nf=len(facts), true=d['true'], est=d['est'],
                         e_eng=d['true'] / d['est'], e_avg=d['true'] / avg, resid=d['true'] / ideal,
                         junf=junf, s=s))
    json.dump(rows, open('e6_rows.json', 'w'), indent=1)

    def q_err(x):
        return max(x, 1 / x)
    print('query            tbl true        engine_err avg_err  residual')
    for r in sorted(rows, key=lambda r: (r['nf'], r['q'])):
        print('%-16s %d   %-11.4g %-10.1f %-8.2f %-8.2f' % (r['q'], r['nt'], r['true'], r['e_eng'], r['e_avg'], r['resid']))
    for nf in sorted(set(r['nf'] for r in rows)):
        g = [r for r in rows if r['nf'] == nf]
        print('facts=%d n=%2d  median engine %.1f  avg-model %.2f  residual %.2f | resid q-err<=3: %d, >10: %d | over-estimates (resid<1/3): %d' % (
            nf, len(g), statistics.median(r['e_eng'] for r in g), statistics.median(r['e_avg'] for r in g),
            statistics.median(r['resid'] for r in g), sum(q_err(r['resid']) <= 3 for r in g),
            sum(q_err(r['resid']) > 10 for r in g), sum(r['resid'] < 1 / 3 for r in g)))
    g = [r for r in rows if r['nf'] >= 2]
    print('facts>=2 n=%d: resid q-err<=2: %d, <=3: %d, >10: %d; median q-err residual %.2f, avg-model %.2f, engine %.1f' % (
        len(g), sum(q_err(r['resid']) <= 2 for r in g), sum(q_err(r['resid']) <= 3 for r in g),
        sum(q_err(r['resid']) > 10 for r in g), statistics.median(q_err(r['resid']) for r in g),
        statistics.median(q_err(r['e_avg']) for r in g), statistics.median(r['e_eng'] for r in g)))
else:
    f = 'out/p3_%s.txt' % what
    for b in blocks(f):
        print('  '.join('%s=%s' % kv for kv in b.items()))
    print('elapsed:', elapsed(f))
