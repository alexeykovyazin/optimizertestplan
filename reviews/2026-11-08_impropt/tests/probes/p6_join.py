import re,sys
preds=[l.rstrip('\n') for l in open(sys.argv[1]) if l.strip()]
est=[float(x) for x in re.findall(r'Filter \(rows=([0-9.]+)\)', open(sys.argv[2]).read())]
real={}
for l in open(sys.argv[3]):
    m=re.match(r'\s*(\d+)\s+(\d+)\s*$', l)
    if m: real[int(m.group(1))]=int(m.group(2))
for i,p in enumerate(preds):
    e=est[i]; r=real.get(i)
    ratio = (e/r) if r else float('nan')
    print("%2d | %-45s | %12.2f | %7s | %s" % (i, p[:45], e, r, ('%.3g'%ratio) if r else 'real=0'))
