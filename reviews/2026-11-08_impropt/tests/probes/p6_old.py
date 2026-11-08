import re,json,sys
txt=open('p6_mcv.out').read()
mcv=[(m.group(1),int(m.group(2))) for m in re.finditer(r'"value": "([^"]*)", "frequency": [0-9.e-]+, "count": (\d+)',txt)]
tot=sum(c for _,c in mcv); S=30000; rem=S-tot; N=200000
preds=[l.rstrip('\n') for l in open('p6_preds.txt') if l.strip()]
est=[float(x) for x in re.findall(r'Filter \(rows=([0-9.]+)\)', open('p6_est.out').read())]
real={}
for l in open('p6_real.out'):
    m=re.match(r'\s*(\d+)\s+(\d+)\s*$', l)
    if m: real[int(m.group(1))]=int(m.group(2))
def like2re(p,esc=None):
    out='';i=0
    while i<len(p):
        ch=p[i]
        if esc and ch==esc and i+1<len(p): out+=re.escape(p[i+1]); i+=2; continue
        out+= '.*' if ch=='%' else '.' if ch=='_' else re.escape(ch); i+=1
    return re.compile('^'+out+'$',re.S)
print("mcv total",tot,"rem",rem)
for i,p in enumerate(preds):
    m=re.match(r"nm (containing|like) '(.*)'( escape '(.)')?$",p)
    if not m: continue
    op,pat=m.group(1),m.group(2)
    if op=='containing': f=lambda v:pat.lower() in v.lower()
    else:
        rx=like2re(pat,m.group(4)); f=lambda v:bool(rx.match(v))
    mm=sum(c for v,c in mcv if f(v))
    old=(mm+rem*0.005)/S*N
    newshare=(est[i]*S/N-mm)/rem
    r=real[i]; realrem=(r-mm*N/S)/(rem*N/S)
    print("%2d %-28s mcvM=%5d old=%9.0f new=%9.0f real=%6d old/r=%.3g new/r=%.3g model=%.5f realRemShare=%.5f"%(i,p[:28],mm,old,est[i],r,old/r if r else 0,est[i]/r if r else 0,newshare,realrem))
