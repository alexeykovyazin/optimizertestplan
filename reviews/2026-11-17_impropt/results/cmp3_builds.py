"""cmp3.py <dir> <suite prefix> <tagA> <tagB> <tagC>: compare three bench runs of one suite."""
import csv, statistics, sys

csv.field_size_limit(10 ** 9)
d, suite = sys.argv[1], sys.argv[2]
tags = sys.argv[3:]


def load(tag):
    q = {}
    for r in csv.DictReader(open('%s/%s_%s.csv' % (d, suite, tag), encoding='utf-8', errors='replace', newline='')):
        e = q.setdefault(r['qid'], {})
        if r['kind'] == 'prepare':
            e['hash'] = r['plan_hash']
            e['dplan'] = r['dplan'] or ''
            e['plan'] = r['plan'] or ''
        elif r['kind'] == 'measured':
            e['status'] = r['status']
            e['sec'] = float(r['exec_ms']) / 1000 if r['exec_ms'] else None
            e['check'] = r['check']
            e['checksum'] = r['checksum']
    return q


runs = {t: load(t) for t in tags}
qids = sorted(runs[tags[0]])

print('== totals ==')
for t in tags:
    q = runs[t]
    ok = [q[k] for k in qids if q[k].get('status') == 'ok']
    bad = [k + ':' + str(q[k].get('status')) for k in qids if q[k].get('status') != 'ok']
    s = [e['sec'] for e in ok]
    print('%-8s n %d ok %d match %d mismatch %d sum %.0f s median %.2f max %.1f notok %s' % (
        t, len(qids), len(ok), sum(e['check'] == 'match' for e in ok), sum(e['check'] == 'MISMATCH' for e in ok),
        sum(s), statistics.median(s), max(s), bad))

common = [k for k in qids if all(runs[t][k].get('status') == 'ok' for t in tags)]
print('\n== common ok: %d ==' % len(common))
for t in tags:
    print('%-8s sum %.1f s' % (t, sum(runs[t][k]['sec'] for k in common)))

for a, b in zip(tags, tags[1:]):
    print('\n== %s -> %s ==' % (a, b))
    ch = [k for k in qids if runs[a][k].get('hash') != runs[b][k].get('hash')]
    print('plan changed: %d %s' % (len(ch), ch[:40]))
    cs = [k for k in common if runs[a][k]['checksum'] != runs[b][k]['checksum']]
    print('checksum differs: %d %s' % (len(cs), cs[:10]))
    st = [(k, runs[a][k].get('status'), runs[b][k].get('status')) for k in qids
          if runs[a][k].get('status') != runs[b][k].get('status')]
    print('status changed: %s' % st)
    same = [k for k in common if k not in ch]
    print('same plan: n %d, sum %.1f -> %.1f s' % (len(same), sum(runs[a][k]['sec'] for k in same),
                                                 sum(runs[b][k]['sec'] for k in same)))
    print('changed plan: n %d, sum %.1f -> %.1f s' % (len([k for k in ch if k in common]),
                                                    sum(runs[a][k]['sec'] for k in ch if k in common),
                                                    sum(runs[b][k]['sec'] for k in ch if k in common)))
    rows = [(runs[b][k]['sec'] - runs[a][k]['sec'], k) for k in common]
    rows.sort()
    print('biggest gains:')
    for dlt, k in rows[:10]:
        print('  %s %.2f -> %.2f s (%+.2f) %s' % (k, runs[a][k]['sec'], runs[b][k]['sec'], dlt, 'PLAN' if k in ch else ''))
    print('biggest losses:')
    for dlt, k in rows[::-1][:10]:
        print('  %s %.2f -> %.2f s (%+.2f) %s' % (k, runs[a][k]['sec'], runs[b][k]['sec'], dlt, 'PLAN' if k in ch else ''))
    ratio = [runs[b][k]['sec'] / runs[a][k]['sec'] for k in same if runs[a][k]['sec'] > 1]
    if ratio:
        print('same plan, > 1 s: n %d, ratio median %.3f, min %.2f, max %.2f' % (
            len(ratio), statistics.median(ratio), min(ratio), max(ratio)))
