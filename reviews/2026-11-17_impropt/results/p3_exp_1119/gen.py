import csv, re, json, collections
R = 'E:/Projects_Big/optimizertestplan'
COL = {'cast_info': 'C_CI', 'movie_keyword': 'C_MK', 'movie_info': 'C_MI', 'movie_companies': 'C_MC', 'movie_info_idx': 'C_MII'}
HDR = "SET LIST ON;\nSET STATS ON;\n"

# ---------- E1
open('p3_e1.sql', 'w', newline='\n').write(HDR + """
SELECT
  COUNT(*) AS KEYS_ANY,
  SUM(IIF(C_CI > 0 AND C_MK > 0 AND C_MI > 0 AND C_MC > 0, 1, 0)) AS KEYS_ALL4,
  SUM(C_CI * C_MK) AS J2,
  SUM(C_CI * C_MK * C_MI) AS J3,
  SUM(C_CI * C_MK * C_MI * C_MC) AS J4,
  SUM(CAST(C_CI AS DOUBLE PRECISION) * C_MK * C_MI * C_MC * C_MII) AS J5,
  SUM(IIF(C_MI > 0 AND C_MC > 0, C_CI * C_MK, 0)) AS J2_ALL4,
  SUM(IIF(C_MC > 0, C_CI * C_MK * C_MI, 0)) AS J3_ALL4
FROM X3_KEY;
""")

# ---------- E2 for 2..5 tables
SETS = [['CI', 'MK'], ['CI', 'MK', 'MI'], ['CI', 'MK', 'MI', 'MC'], ['CI', 'MK', 'MI', 'MC', 'MII']]


def e2(cols):
    tot = ",\n".join("    SUM(IIF(x.C_%s > 0, POWER(x.C_%s, p.A), 0e0)) / p.M AS T_%s" % (c, c, c) for c in cols)
    prod = " * ".join((["CAST(x.C_%s AS DOUBLE PRECISION)" % cols[0]] + ["x.C_%s" % c for c in cols[1:]]))
    mins = ", ".join("POWER(x.C_%s, t.A) / t.T_%s" % (c, c) for c in cols)
    where = " AND ".join("x.C_%s > 0" % c for c in cols)
    return """
WITH par AS (
  SELECT a.A, m.M
  FROM (SELECT 0e0 AS A FROM RDB$DATABASE UNION ALL
        SELECT 1e0 FROM RDB$DATABASE UNION ALL
        SELECT 1.5e0 FROM RDB$DATABASE) a
  CROSS JOIN
       (SELECT 256e0 AS M FROM RDB$DATABASE UNION ALL
        SELECT 1024e0 FROM RDB$DATABASE UNION ALL
        SELECT 4096e0 FROM RDB$DATABASE) m
),
tot AS (
  SELECT p.A, p.M,
%s
  FROM X3_KEY x CROSS JOIN par p
  GROUP BY p.A, p.M
),
k AS (
  SELECT t.A, t.M,
    %s AS X,
    MINVALUE(1e0, %s) AS PI
  FROM X3_KEY x CROSS JOIN tot t
  WHERE %s
)
SELECT '%s' AS E2_SET, A, M,
  COUNT(*) AS KEYS,
  SUM(X) AS J,
  SUM(PI) AS MATCHED_EXPECTED,
  SQRT(SUM(X * X * (1e0 / PI - 1e0))) / SUM(X) AS CV
FROM k
GROUP BY A, M
ORDER BY A, M;
""" % (tot, prod, mins, where, "+".join(cols))


open('p3_e2.sql', 'w', newline='\n').write(HDR + "".join(e2(s) for s in SETS))


# ---------- E3: 64 rotated samples, 4 tables
def e3(a, m):
    return """
WITH RECURSIVE s AS (
  SELECT 0 AS N FROM RDB$DATABASE
  UNION ALL
  SELECT s.N + 1 FROM s WHERE s.N < 63
),
par AS (SELECT %se0 AS A, %se0 AS M FROM RDB$DATABASE),
tot AS (
  SELECT
    SUM(IIF(x.C_CI > 0, POWER(x.C_CI, p.A), 0e0)) / MAX(p.M) AS T_CI,
    SUM(IIF(x.C_MK > 0, POWER(x.C_MK, p.A), 0e0)) / MAX(p.M) AS T_MK,
    SUM(IIF(x.C_MI > 0, POWER(x.C_MI, p.A), 0e0)) / MAX(p.M) AS T_MI,
    SUM(IIF(x.C_MC > 0, POWER(x.C_MC, p.A), 0e0)) / MAX(p.M) AS T_MC
  FROM X3_KEY x CROSS JOIN par p
),
k AS (
  SELECT x.U,
    CAST(x.C_CI AS DOUBLE PRECISION) * x.C_MK * x.C_MI * x.C_MC AS X,
    MINVALUE(1e0,
      POWER(x.C_CI, p.A) / t.T_CI, POWER(x.C_MK, p.A) / t.T_MK,
      POWER(x.C_MI, p.A) / t.T_MI, POWER(x.C_MC, p.A) / t.T_MC) AS PI
  FROM X3_KEY x CROSS JOIN tot t CROSS JOIN par p
  WHERE x.C_CI > 0 AND x.C_MK > 0 AND x.C_MI > 0 AND x.C_MC > 0
),
e AS (
  SELECT s.N, SUM(k.X / k.PI) AS EST, COUNT(*) AS MATCHED
  FROM k CROSS JOIN s
  WHERE (k.U + s.N / 64e0) - FLOOR(k.U + s.N / 64e0) < k.PI
  GROUP BY s.N
),
j AS (SELECT SUM(X) AS J FROM k)
SELECT '%s/%s' AS E3_A_M,
  COUNT(*) AS SAMPLES,
  AVG(e.EST / j.J) AS R_AVG,
  MIN(e.EST / j.J) AS R_MIN,
  MAX(e.EST / j.J) AS R_MAX,
  SUM(IIF(e.EST BETWEEN j.J / 2 AND j.J * 2, 1, 0)) AS IN_X2,
  SUM(IIF(e.EST BETWEEN j.J / 10 AND j.J * 10, 1, 0)) AS IN_X10,
  SUM(IIF(e.EST > j.J * 2, 1, 0)) AS OVER_X2,
  SUM(IIF(e.EST < j.J / 2, 1, 0)) AS UNDER_X2,
  MIN(e.MATCHED) AS MATCHED_MIN,
  MAX(e.MATCHED) AS MATCHED_MAX
FROM e CROSS JOIN j;
""" % (a, m, a, m)


open('p3_e3.sql', 'w', newline='\n').write(
    HDR + "".join(e3(a, m) for a in ('0', '1', '1.5') for m in ('1024', '4096')))

# ---------- E4, E5, degree summary
deg = "\nUNION ALL\n".join(
    ("SELECT '{c}' AS COL, COUNT(*) AS KEYS, SUM(C_{c}) AS ROWS_N, AVG(C_{c} * 1e0) AS C_AVG, "
     "SUM(1e0 * C_{c} * C_{c}) / SUM(C_{c}) AS C_SELF, MAX(C_{c}) AS C_MAX, "
     "SUM(1e0 * C_{c} * C_{c}) AS SUM_C2 FROM X3_KEY WHERE C_{c} > 0").format(c=c)
    for c in ('CI', 'MK', 'MI', 'MC', 'MII'))
open('p3_e45.sql', 'w', newline='\n').write(HDR + """
WITH r AS (
  SELECT
    CAST(C_CI AS DOUBLE PRECISION) * C_MK * C_MI * C_MC AS X,
    ROW_NUMBER() OVER (ORDER BY C_CI DESC) AS R_CI,
    ROW_NUMBER() OVER (ORDER BY C_MK DESC) AS R_MK,
    ROW_NUMBER() OVER (ORDER BY C_MI DESC) AS R_MI,
    ROW_NUMBER() OVER (ORDER BY C_MC DESC) AS R_MC
  FROM X3_KEY
)
SELECT n.TOPN,
  SUM(IIF(r.R_CI <= n.TOPN AND r.R_MK <= n.TOPN AND r.R_MI <= n.TOPN AND r.R_MC <= n.TOPN, r.X, 0e0))
    / SUM(r.X) AS SHARE_IN_ALL,
  SUM(IIF(r.R_CI <= n.TOPN OR r.R_MK <= n.TOPN OR r.R_MI <= n.TOPN OR r.R_MC <= n.TOPN, r.X, 0e0))
    / SUM(r.X) AS SHARE_IN_ANY
FROM r CROSS JOIN
     (SELECT 100 AS TOPN FROM RDB$DATABASE UNION ALL
      SELECT 1000 FROM RDB$DATABASE UNION ALL
      SELECT 10000 FROM RDB$DATABASE) n
GROUP BY n.TOPN
ORDER BY n.TOPN;

WITH a AS (SELECT C_CI AS C, ROW_NUMBER() OVER (ORDER BY C_CI DESC) AS R FROM X3_KEY WHERE C_CI > 0),
     b AS (SELECT C_MK AS C, ROW_NUMBER() OVER (ORDER BY C_MK DESC) AS R FROM X3_KEY WHERE C_MK > 0),
     c AS (SELECT C_MI AS C, ROW_NUMBER() OVER (ORDER BY C_MI DESC) AS R FROM X3_KEY WHERE C_MI > 0),
     d AS (SELECT C_MC AS C, ROW_NUMBER() OVER (ORDER BY C_MC DESC) AS R FROM X3_KEY WHERE C_MC > 0)
SELECT SUM(CAST(a.C AS DOUBLE PRECISION) * b.C * c.C * d.C) AS BOUND_RANK4
FROM a JOIN b ON b.R = a.R JOIN c ON c.R = a.R JOIN d ON d.R = a.R;

WITH a AS (SELECT C_CI AS C, ROW_NUMBER() OVER (ORDER BY C_CI DESC) AS R FROM X3_KEY WHERE C_CI > 0),
     b AS (SELECT C_MK AS C, ROW_NUMBER() OVER (ORDER BY C_MK DESC) AS R FROM X3_KEY WHERE C_MK > 0)
SELECT SUM(CAST(a.C AS DOUBLE PRECISION) * b.C) AS BOUND_RANK2
FROM a JOIN b ON b.R = a.R;

SELECT POWER(SUM(POWER(C_CI, 4e0)), 0.25e0) * POWER(SUM(POWER(C_MK, 4e0)), 0.25e0)
     * POWER(SUM(POWER(C_MI, 4e0)), 0.25e0) * POWER(SUM(POWER(C_MC, 4e0)), 0.25e0) AS BOUND_HOLDER4,
       SQRT(SUM(1e0 * C_CI * C_CI)) * SQRT(SUM(1e0 * C_MK * C_MK)) AS BOUND_CS2
FROM X3_KEY;

""" + deg + ";\n")

# ---------- E6
S = list(csv.DictReader(open(R + '/reviews/2026-11-17_impropt/results/scale_c1_partial_summary.csv')))
ids = [x['qid'] for x in S if float(x['estimate_to_true']) < 0.1] + ['scale_351', 'job_light_051']
est = {x['qid']: (float(x['true_cardinality']), float(x['estimate'])) for x in S}
est['job_light_051'] = (151179813.0, 16.4e6)
Q = {}
filt = {}
subsets = {}
JOIN = re.compile(r'^(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)$')
FLT = re.compile(r"^(\w+)\.(\w+)\s*(=|<>|!=|<=|>=|<|>)\s*(-?\d+(\.\d+)?|'[^']*')$")
for q in ids:
    d = 'scale' if q.startswith('scale') else 'job-light'
    sql = open('%s/bench/queries/%s/%s.sql' % (R, d, q), encoding='utf-8').read().strip().rstrip(';')
    m = re.match(r'(?is)^SELECT\s+COUNT\(\*\)\s+FROM\s+(.*?)\s+WHERE\s+(.*)$', sql)
    assert m, q
    al = {}
    for item in m.group(1).split(','):
        t, a = item.split()
        al[a] = t.lower()
    f = {a: [] for a in al}
    for c in re.split(r'(?i)\s+AND\s+', m.group(2)):
        c = c.strip()
        j = JOIN.match(c)
        if j:
            assert j.group(2) in ('id', 'movie_id') and j.group(4) in ('id', 'movie_id'), (q, c)
            continue
        g = FLT.match(c)
        assert g, (q, c)
        f[g.group(1)].append('x.' + c[len(g.group(1)) + 1:])
    facts = tuple(sorted(COL[al[a]] for a in al if al[a] != 'title'))
    subsets.setdefault(facts, 'J%d' % (len(subsets) + 1))
    fl = []
    for a in al:
        cond = ' AND '.join(f[a])
        if cond:
            key = filt.setdefault(al[a], {}).setdefault(cond, 'F%d' % (len(filt[al[a]]) + 1))
            fl.append([al[a], key])
    Q[q] = dict(tables=sorted(al.values()), facts=facts, j=subsets[facts], filters=fl,
                true=est[q][0], est=est[q][1], sql=sql)
out = HDR
for t in ('title', 'cast_info', 'movie_info', 'movie_info_idx', 'movie_keyword', 'movie_companies'):
    cols = ",\n  ".join("SUM(IIF(%s, 1, 0)) AS %s" % (c, k) for c, k in filt.get(t, {}).items())
    out += "\nSELECT '%s' AS TBL, COUNT(*) AS N%s\nFROM %s x;\n" % (t, (",\n  " + cols) if cols else "", t)
js = []
for facts, name in subsets.items():
    if facts:
        js.append("SUM(%s) AS %s" % (" * ".join(["CAST(%s AS DOUBLE PRECISION)" % facts[0]] + list(facts[1:])), name))
    else:
        js.append("CAST(0 AS DOUBLE PRECISION) AS %s" % name)
out += "\nSELECT 'X3' AS TBL,\n  " + ",\n  ".join(js) + "\nFROM X3_KEY;\n"
open('p3_e6.sql', 'w', newline='\n').write(out)
json.dump(dict(Q=Q, filt=filt, subsets={n: list(f) for f, n in subsets.items()}), open('e6_meta.json', 'w'), indent=1)
print('queries', len(Q), 'subsets', len(subsets), {t: len(v) for t, v in filt.items()})
print(collections.Counter(len(v['tables']) for v in Q.values()))
