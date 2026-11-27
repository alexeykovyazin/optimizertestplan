"""aj_cmp.py <file A> <file B> - compare two outputs of aj_q.sql (set list on) by the label of the query.
Prints the labels with different results, the values of both files, and the labels that failed."""
import re
import sys


def load(path):
    res, cur = {}, None
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip()
        m = re.match(r"^Q\s+(\S+)$", line)
        if m:
            cur = m.group(1)
            res.setdefault(cur, [])
            continue
        if not line or cur is None:
            continue
        if line.startswith("Statement failed"):
            res[cur].append("FAILED-AFTER")
            continue
        res[cur].append(" ".join(line.split()))
    return res


a, b = load(sys.argv[1]), load(sys.argv[2])
diff = 0
for q in sorted(set(a) | set(b)):
    if a.get(q) != b.get(q):
        diff += 1
        print("%s  A: %s" % (q, " | ".join(a.get(q, ["-"]))[:230]))
        print("%s  B: %s" % (" " * len(q), " | ".join(b.get(q, ["-"]))[:230]))
print("labels: %d, different: %d" % (len(set(a) | set(b)), diff))
