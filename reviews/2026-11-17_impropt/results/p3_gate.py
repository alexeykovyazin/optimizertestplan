# Proposal 3, gate P0: what is left for the key sample after proposal 1 and the join order DP.
# Usage: python p3_gate.py <results dir>
# Part 1: scale queries underestimated more than 10 times, time before and after the page miss cost.
# Part 2: scale queries whose plan the join order DP changes, grouped by the estimate error.
import csv, sys, os, statistics
csv.field_size_limit(10**9)
R = sys.argv[1]

# ---- part 1
def load(f):
    d = {}
    for x in csv.DictReader(open(os.path.join(R, f), encoding='utf-8')):
        q = d.setdefault(x['qid'], {})
        if x['kind'] == 'prepare': q['plan'] = x['plan']
        else:
            q['status'] = x['status']; q['s'] = float(x['exec_ms'])/1000 if x['exec_ms'] else None
    return d
base3, pm3 = load('pagemiss_1118/pmch_fusedcond.csv'), load('pagemiss_1118/pmch_pagemiss.csv')
base5, pm5 = load('pagemiss_1118/g5ch_fusedcond.csv'), load('pagemiss_1118/g5ch_pagemiss.csv')
S = list(csv.DictReader(open(os.path.join(R, 'scale_c1_partial_summary.csv'), encoding='utf-8')))
U = [x for x in S if float(x['estimate_to_true']) < 0.1]
print('underestimated >10x:', len(U), 'timeouts:', sum(x['status'] != 'ok' for x in U))
rows = []
for x in U:
    q = x['qid']; true = float(x['true_cardinality'])
    b_s = float(x['exec_s']) if x['status'] == 'ok' else None
    changed = q in pm5 or q in pm3
    after = pm5.get(q) or pm3.get(q)
    before = base5.get(q) or base3.get(q)
    if changed:
        b = before['s'] if before['status'] == 'ok' else None
        a = after['s'] if after['status'] == 'ok' else None
        plan = after['plan']
    else:
        b = a = b_s; plan = None
    rows.append(dict(q=q, t=int(x['tables']), true=true, err=1/float(x['estimate_to_true']), changed=changed, b=b, a=a,
                     nl=int(x['nested_loops']), plan=plan))
big = [r for r in rows if r['true'] >= 3e9]
small = [r for r in rows if r['true'] < 3e9]
print('true >= 3e9 (proposal 2 area):', len(big), 'timeouts after:', sum(r['a'] is None for r in big))
print('true < 3e9:', len(small), 'changed by page-miss:', sum(r['changed'] for r in small))
def tot(rs, k): return sum(r[k] or 300 for r in rs)
print('  time before %.0f after %.0f (timeout=300)' % (tot(small, 'b'), tot(small, 'a')))
ch = [r for r in small if r['changed']]
print('  changed: before %.0f after %.0f' % (tot(ch, 'b'), tot(ch, 'a')))
# slow after: rate < 1M rows/s and time > 10 s
slow = [r for r in small if (r['a'] or 300) > 10 and r['true'] / (r['a'] or 300) < 1e6]
print('  still slow (>10 s and <1M rows/s):', len(slow), 'time %.0f' % tot(slow, 'a'))
mid = [r for r in small if (r['a'] or 300) > 10 and 1e6 <= r['true'] / (r['a'] or 300) < 3e6]
print('  medium (>10 s and 1-3M rows/s):', len(mid), 'time %.0f' % tot(mid, 'a'))
for r in sorted(slow + mid, key=lambda r: -(r['a'] or 300)):
    print('   %s t=%d true=%.0fM err=%.0f before=%s after=%s rate=%.2fM/s changed=%s nl_base=%d' % (
        r['q'], r['t'], r['true']/1e6, r['err'], r['b'] and round(r['b'],1), r['a'] and round(r['a'],1),
        r['true']/(r['a'] or 300)/1e6, r['changed'], r['nl']))
allsum = sum(float(x['exec_s']) for x in S if x['status'] == 'ok')
print('suite sum (ok, base c1): %.0f' % allsum)
# all 360: slow after P1 regardless of estimate error
print('--- top by time after, true < 3e9')
for r in sorted(small, key=lambda r: -(r['a'] or 300))[:14]:
    print('   %s t=%d true=%.0fM err=%.0f before=%s after=%s rate=%.1fM/s changed=%s nl_base=%d' % (
        r['q'], r['t'], r['true']/1e6, r['err'], r['b'] and round(r['b'],1), r['a'] and round(r['a'],1),
        r['true']/(r['a'] or 300)/1e6, r['changed'], r['nl']))
for rate in (6e6, 10e6):
    gain = sum(max(0, (r['a'] or 300) - r['true']/rate - 2) for r in small)
    print('upper bound of gain at %.0fM rows/s: %.0f s' % (rate/1e6, gain))
print('median rate after: %.1fM/s' % statistics.median(r['true']/(r['a'] or 300)/1e6 for r in small if (r['a'] or 300) > 5))
print('nl_base>0 and unchanged:', sum(1 for r in small if r['nl'] and not r['changed']), 'time %.0f' % sum(r['a'] or 300 for r in small if r['nl'] and not r['changed']))
r14 = [r for r in rows if r['q'] == 'scale_014'][0]; print('scale_014', r14['b'], r14['a'], r14['plan'])

# ---- part 2
def load2(f):
    d = {}
    for x in csv.DictReader(open(os.path.join(R, f), encoding='utf-8')):
        if x['kind'] == 'prepare': continue
        d[x['qid']] = float(x['exec_ms'])/1000 if x['status'] == 'ok' and x['exec_ms'] else 300.0
    return d
off, dp = load2("dp_1118/h2ch_off.csv"), load2("dp_1118/h2ch_dp1000.csv")
S = {x['qid']: x for x in csv.DictReader(open(os.path.join(R, 'scale_c1_partial_summary.csv'), encoding='utf-8'))}
groups = {}
for q in off:
    if not q.startswith('scale') or q not in dp: continue
    if q not in S: g = 'no estimate (361-500)'
    else:
        e = 1/float(S[q]['estimate_to_true'])
        g = 'under >10x' if e > 10 else ('under 3-10x' if e > 3 else ('within 3x' if e > 1/3 else 'over >3x'))
    a = groups.setdefault(g, dict(n=0, off=0, dp=0, slow=0, fast=0, loss=0, win=0))
    a['n'] += 1; a['off'] += off[q]; a['dp'] += dp[q]
    if dp[q] > 1.5*off[q]: a['slow'] += 1; a['loss'] += dp[q]-off[q]
    if off[q] > 1.5*dp[q]: a['fast'] += 1; a['win'] += off[q]-dp[q]
for g, a in groups.items():
    print('%-24s n=%3d off=%5.0f dp=%5.0f slower1.5x=%2d (+%4.0f s) faster1.5x=%2d (-%4.0f s)' % (g, a['n'], a['off'], a['dp'], a['slow'], a['loss'], a['fast'], a['win']))
for q in ('scale_042','scale_119','scale_253','scale_035','scale_289','scale_339','scale_484'):
    x = S.get(q); print(q, off.get(q), dp.get(q), x and (x['tables'], x['true_cardinality'], round(1/float(x['estimate_to_true']),1)))
