import csv,sys
sys.stdout.reconfigure(encoding='utf-8')
csv.field_size_limit(10**9)
def load(f):
    return {r['qid']:r for r in csv.DictReader(open(f,encoding='utf-8')) if r['kind']=='measured'}
n=load(sys.argv[1]); o=load(sys.argv[2])
ch=[q for q in n if n[q]['plan_hash']!=o[q]['plan_hash']]
print('plan changed:',len(ch),'of',len(n))
for q in sorted(ch):
    print(q[4:], o[q]['status'],o[q]['exec_ms'],'->',n[q]['status'],n[q]['exec_ms'])
same=[q for q in n if q not in ch and n[q]['status']==o[q]['status']=='ok']
import math
print('same-plan geomean', math.exp(sum(math.log(float(n[q]['exec_ms'])/float(o[q]['exec_ms'])) for q in same)/len(same)), len(same))
big=[(float(n[q]['exec_ms'])/float(o[q]['exec_ms']),q) for q in same]
print('same plan, slower x1.5:',[(q[4:],round(r,1)) for r,q in sorted(big,reverse=True) if r>1.5])
for q in ('ceb_11a_009',):
    print('OLD',o[q]['plan'][:1500]); print('NEW',n[q]['plan'][:1500])
