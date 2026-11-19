import csv, re, sys
csv.field_size_limit(10**9)
P, MAN = sys.argv[1], sys.argv[2]
man = {}; cur = None
for line in open(MAN, encoding='utf-8'):
    m = re.match(r'- id: (\S+)', line)
    if m: cur = man.setdefault(m.group(1), {}); continue
    m = re.match(r'  (tables|true_cardinality): (\S+)', line)
    if m and cur is not None: cur[m.group(1)] = int(m.group(2))
def summ(f):
    q = {}
    for r in csv.DictReader(open(P + '/' + f, encoding='utf-8', errors='replace', newline='')):
        d = q.setdefault(r['qid'], {})
        if r['kind'] == 'prepare':
            m = re.search(r'Aggregate[^\n]*\n\s*-> [^\n]*\(rows=([0-9.]+)\)', r['dplan'] or '')
            d['est'] = float(m.group(1)) if m else None
            d['nl'] = len(re.findall(r'Nested Loop Join', r['dplan'] or ''))
            d['plan'] = r['plan']
        elif r['kind'] == 'measured':
            d['t'] = float(r['exec_ms'])/1000 if r['status'] == 'ok' and r['exec_ms'] else 300.0
    return q
b = summ('joblight_fusedcond.csv')
p = {q: dict(d) for q, d in b.items()}
src = {q: 'base' for q in b}
for f, tag in (('pmch_pagemiss.csv', 'g3'), ('g5ch_pagemiss.csv', 'g5')):
    for q, d in summ(f).items():
        if q in p and 't' in d: p[q] = d; src[q] = tag
print('overlay:', {t: sum(1 for q in src if src[q] == t) for t in ('base', 'g3', 'g5')})
print('job-light n', len(b), len(p), 'sum base %.0f pm %.0f' % (sum(x['t'] for x in b.values()), sum(x['t'] for x in p.values())), 'no estimate:', sum(1 for x in b.values() if not x['est']))
for name, lo, hi in (('under >10x', 10, 1e99), ('under 3-10x', 3, 10), ('within 3x', 1/3, 3), ('over >3x', 0, 1/3)):
    g = [q for q in b if b[q]['est'] and lo < man[q]['true_cardinality']/b[q]['est'] <= hi]
    rate = lambda q: man[q]['true_cardinality']/p[q]['t']
    slow = [q for q in g if p[q]['t'] > 10 and rate(q) < 1e6]
    mid = [q for q in g if p[q]['t'] > 10 and 1e6 <= rate(q) < 3e6]
    ch = [q for q in g if b[q]['plan'] != p[q]['plan']]
    print('%-12s n=%2d base=%5.0f pm=%5.0f plan changed=%d slow=%d (%.0f s) mid=%d (%.0f s)' % (name, len(g), sum(b[q]['t'] for q in g), sum(p[q]['t'] for q in g), len(ch), len(slow), sum(p[q]['t'] for q in slow), len(mid), sum(p[q]['t'] for q in mid)))
    for q in slow + mid:
        print('    %s tables %d true %.1fM err %.1f base %.1f pm %.1f rate %.2fM/s nl %d' % (q, man[q]['tables'], man[q]['true_cardinality']/1e6, man[q]['true_cardinality']/b[q]['est'], b[q]['t'], p[q]['t'], rate(q)/1e6, p[q]['nl']))
    if lo == 10:
        gain = lambda r: sum(max(0, p[q]['t'] - man[q]['true_cardinality']/r - 2) for q in g)
        print('    upper bound of gain: %.0f s at 6M/s, %.0f s at 10M/s' % (gain(6e6), gain(10e6)))
