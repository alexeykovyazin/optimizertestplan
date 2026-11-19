"""cmpplans.py - compares the plans of the variants of the worst case rule.
Reads plans/wcp_<engine>_<variant>.txt (one PLAN per query, in the order of wc_qids.txt)."""
import glob, json, os, re, sys

SP = 'C:/Users/aleks/AppData/Local/Temp/claude/c255271938a7846a/58624a2e-45d9-4769-ae51-5e8b14b87350/scratchpad/wc/'
ids = open(SP + 'wc_qids.txt').read().split()


def suite(q):
    return 'jl' if q.startswith('job_light') else 'ceb' if q.startswith('ceb') else 'scale'


def load(tag):
    txt = open(SP + 'plans/wcp_%s.txt' % tag, encoding='utf-8', errors='replace').read()
    plans = [re.sub(r'\s+', ' ', p).strip() for p in re.findall(r'^PLAN .*?(?=\n\s*\n|\Z)', txt, re.S | re.M)]
    err = len(re.findall(r'Statement failed', txt))
    if len(plans) != len(ids):
        print('!! %s: %d plans for %d queries, errors %d' % (tag, len(plans), len(ids), err))
        return None
    return dict(zip(ids, plans))


P = {}
for f in sorted(glob.glob(SP + 'plans/wcp_*.txt')):
    tag = os.path.basename(f)[4:-4]
    d = load(tag)
    if d:
        P[tag] = d


def methods(plan):
    return plan.count('HASH ('), len(re.findall(r' INDEX \(', plan))


def diff(a, b):
    return [q for q in ids if P[a][q] != P[b][q]]


print('plans loaded:', ' '.join(P))
if 'wb_v0' in P and 'w42_v0' in P:
    d = diff('wb_v0', 'w42_v0')
    print('PR 42 against the base (constant rule): %d changed  %s' % (
        len(d), {s: sum(1 for q in d if suite(q) == s) for s in ('jl', 'ceb', 'scale')}))
for e in ('wb', 'w42'):
    if e + '_v0' not in P:
        continue
    for v in ('v1', 'v2', 'v3', 'v4', 'v5'):
        t = '%s_%s' % (e, v)
        if t not in P:
            continue
        d = diff(e + '_v0', t)
        more = sum(1 for q in d if methods(P[t][q])[0] > methods(P[e + '_v0'][q])[0])
        less = sum(1 for q in d if methods(P[t][q])[0] < methods(P[e + '_v0'][q])[0])
        print('%-7s vs %s_v0: %3d changed %s  more hash joins: %d, fewer: %d, same count: %d' % (
            t, e, len(d), {s: sum(1 for q in d if suite(q) == s) for s in ('jl', 'ceb', 'scale')}, more, less,
            len(d) - more - less))
# does PR 42 change what the rule does: the plans of the same variant on the two engines
for v in ('v0', 'v1', 'v2', 'v3', 'v4', 'v5'):
    if 'wb_' + v in P and 'w42_' + v in P:
        print('%s: base against PR 42: %d plans differ' % (v, len(diff('wb_' + v, 'w42_' + v))))

if len(sys.argv) > 1:
    # cmpplans.py show <tagA> <tagB> [n] - the first n differing plans
    a, b = sys.argv[2], sys.argv[3]
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 5
    for q in diff(a, b)[:n]:
        print(q)
        print('  ', a, P[a][q][:420])
        print('  ', b, P[b][q][:420])
