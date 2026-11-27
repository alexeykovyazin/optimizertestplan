"""Time the counted join queries with one engine folder.

usage: timing.py <engine_dir> <db_file> <out_prefix> [FB_COUNTED_SIDE value] [query labels...]
Prints: label, best elapsed of three runs, result row, the plan lines with the join and count nodes.
"""
import os
import re
import subprocess
import sys

Q = [
    ('Q1 self join, 20 rows per key',
     "select b.k, count(*) n, sum(b.v) w from t a join t b on b.m = a.m group by b.k"),
    ('Q2 self join, 4 aggregates',
     "select b.k, count(*) n, sum(b.v) w, min(b.s) y, avg(b.v) z from t a join t b on b.m = a.m group by b.k"),
    ('Q3 unique key, fact to dim',
     "select f.dim_id, count(*) n, sum(f.v) w from fact f join dim d on d.id = f.dim_id group by f.dim_id"),
    ('Q4 unique key, t to dim',
     "select a.k, count(*) n, sum(a.v) w from t a join dim d on d.id = a.k group by a.k"),
    ('Q5 chain with a unique key',
     "select b.k, count(*) n, sum(b.v) w from t a join t b on b.m = a.m join t c on c.id = a.k group by b.k"),
    ('Q6 free 2M, other 2000, 1000 rows per key',
     "select d.g, count(*) n, sum(d.id) w from fact f join dim d on d.m = f.dim_id group by d.g"),
    ('Q7 as Q6, other side filtered to 20 rows',
     "select d.g, count(*) n, sum(d.id) w from fact f join dim d on d.m = f.dim_id where d.id < 20 group by d.g"),
    ('Q8 free 2M with 1M key values, other 2000',
     "select d.g, count(*) n, sum(d.id) w from fact f join dim d on d.m = f.u group by d.g"),
    ('Q9 free 2M with 500K key values, other 2000',
     "select d.g, count(*) n, sum(d.id) w from fact f join dim d on d.m = f.s group by d.g"),
    ('Q10 free 60000 with 3000 key values, other 2000',
     "select d.g, count(*) n, sum(d.id) w from t a join dim d on d.m = a.m group by d.g"),
    ('Q11 free 2M with 500K key values, other 60000',
     "select b.k, count(*) n, sum(b.v) w from fact f join t b on b.id = f.s group by b.k"),
    ('Q12 free 2M, other 2000 with 10 rows per key',
     "select d.g, count(*) n, sum(d.id) w from fact f join dim d on d.h = f.dim_id group by d.g"),
    ('Q13 free 2M with 1M key values, other 60000',
     "select b.k, count(*) n, sum(b.v) w from fact f join t b on b.id = f.u group by b.k"),
    ('Q14 free 2M with 2000 key values, other 60000',
     "select b.k, count(*) n, sum(b.v) w from fact f join t b on b.id = f.dim_id group by b.k"),
]


def main():
    engine, db, prefix = sys.argv[1:4]
    mode = sys.argv[4] if len(sys.argv) > 4 else ''
    only = sys.argv[5:]

    env = dict(os.environ)
    env.pop('FB_COUNTED_SIDE', None)

    if mode not in ('', '-'):
        env['FB_COUNTED_SIDE'] = mode

    isql = os.path.join(engine, 'isql.exe')

    for label, sql in Q:
        if only and label.split()[0] not in only:
            continue

        wrapped = "select count(*) c, sum(n) n, cast(sum(w) as double precision) w from (%s)" % sql
        script = ("connect '%s' user SYSDBA;\nset explain on;\n%s;\nset explain off;\nset stats on;\n%s;\n%s;\n%s;\n"
                  % (db.replace('\\', '/'), wrapped, wrapped, wrapped, wrapped))
        name = prefix + '_' + label.split()[0] + '.sql'
        open(name, 'w').write(script)

        p = subprocess.run([isql, '-q', '-i', name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           env=env, timeout=3600)
        text = p.stdout.decode('latin-1')
        open(prefix + '_' + label.split()[0] + '.txt', 'w').write(text)

        times = [float(x) for x in re.findall(r'Elapsed time\s*=\s*([0-9.]+)', text)]
        plan = [l.strip() for l in text.splitlines()
                if re.search(r'Join|Count|Aggregate|Unique Scan|Full Scan|Range Scan', l)]
        rows = [l.strip() for l in text.splitlines() if re.match(r'^\s*\d+\s+\d+\s+[0-9.e+]+\s*$', l)]

        print('%s | best %.3f s of %s | rows %s' % (label, min(times) if times else -1, times,
                                                     rows[0] if rows else '?'))
        print('    ' + ' / '.join(plan))
        sys.stdout.flush()


main()
