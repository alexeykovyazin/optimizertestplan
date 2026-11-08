import sys
preds=[l.rstrip('\n') for l in open(sys.argv[1]) if l.strip()]
with open(sys.argv[2],'w') as f:
    f.write("connect 'probe6' user SYSDBA;\nset planonly on;\nset explain on;\n")
    for p in preds: f.write("select count(*) from pn where %s;\n"%p)
with open(sys.argv[3],'w') as f:
    f.write("connect 'probe6' user SYSDBA;\nset heading off;\n")
    for i,p in enumerate(preds): f.write("select %d, count(*) from pn where %s;\n"%(i,p))
