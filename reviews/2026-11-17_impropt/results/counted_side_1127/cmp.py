import glob, os, re, sys
a, b = sys.argv[1:3]
def norm(p):
    out = []
    for l in open(p, encoding='latin-1'):
        l = l.rstrip()
        if re.search(r'Elapsed time|Current memory|Delta memory|Max memory|^Cpu|Buffers|^Reads|^Writes|^Fetches', l): continue
        l = re.sub(r'[A-Za-z]:[\/][^ ]*work_(base|fin)', 'WORK', l)
        out.append(l)
    return out
diff = []
for p in sorted(glob.glob(os.path.join(a, '*.txt'))):
    n = os.path.basename(p); q = os.path.join(b, n)
    if not os.path.exists(q): print('missing', n); continue
    x, y = norm(p), norm(q)
    if x != y:
        import difflib
        d = [l for l in difflib.unified_diff(x, y, lineterm='', n=0) if not l.startswith(('---', '+++', '@@'))]
        diff.append((n, d))
print('tests with different output:', len(diff))
for n, d in diff:
    print('#####', n, len(d), 'lines')
    for l in d[:int(sys.argv[3]) if len(sys.argv) > 3 else 12]: print('   ', l[:210])
