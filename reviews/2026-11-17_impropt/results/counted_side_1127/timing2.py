"""Interleaved timing: every round runs each query with every configuration, the best time of all rounds is taken.

usage: timing2.py <db_file> <rounds> <configs> [query labels...]
configs: comma separated name=engine_dir[:FB_COUNTED_SIDE], for example base=C:/x/fb_base,new=C:/x/fb_new:1
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_queries():
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'timing.py')).read()
    ns = {}
    exec(src[src.index('Q = ['):src.index('def main')], ns)
    return ns['Q']


def main():
    db = sys.argv[1].replace('\\', '/')
    rounds = int(sys.argv[2])
    configs = []

    for item in sys.argv[3].split(','):
        name, rest = item.split('=', 1)
        m = re.match(r'^(.*?)(?::([0-9]))?$', rest)
        configs.append((name, m.group(1), m.group(2)))

    only = sys.argv[4:]
    queries = [q for q in load_queries() if not only or q[0].split()[0] in only]
    best = {}
    plans = {}
    rows = {}

    for r in range(rounds):
        for label, sql in queries:
            key = label.split()[0]
            wrapped = "select count(*) c, sum(n) n, cast(sum(w) as double precision) w from (%s)" % sql

            for name, engine, mode in configs:
                env = dict(os.environ)
                env.pop('FB_COUNTED_SIDE', None)

                if mode is not None:
                    env['FB_COUNTED_SIDE'] = mode

                script = ("connect '%s' user SYSDBA;\nset explain on;\n%s;\nset explain off;\nset stats on;\n"
                          "%s;\n%s;\n%s;\n" % (db, wrapped, wrapped, wrapped, wrapped))
                fname = 'i_%s_%s.sql' % (name, key)
                open(fname, 'w').write(script)
                p = subprocess.run([os.path.join(engine, 'isql.exe'), '-q', '-i', fname],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, timeout=3600,
                                   creationflags=0x80)
                text = p.stdout.decode('latin-1')
                open('i_%s_%s.txt' % (name, key), 'w').write(text)
                times = [float(x) for x in re.findall(r'Elapsed time\s*=\s*([0-9.]+)', text)]

                cpus = [float(x) for x in re.findall(r'Cpu\s*=\s*([0-9.]+)', text)]

                if times:
                    best[(key, name)] = min([best.get((key, name), 1e9)] + times)

                if cpus:
                    best[(key, name, 'cpu')] = min([best.get((key, name, 'cpu'), 1e9)] + cpus)

                counted = 'counted' in text
                count_node = bool(re.search(r'->\s*Count\b', text))
                joins = re.findall(r'(Hash Join|Nested Loop Join|Batch Hash Join)', text)
                scans = re.findall(r'-> (?:Table|Index) "(\w+)"(?: as "(\w+)")?', text)
                plans[(key, name)] = '%s%s%s [%s]' % ('+'.join(joins), ' counted' if counted else '',
                                                      ' Count' if count_node else '',
                                                      ' '.join(a or t for t, a in scans))
                res = [l.strip() for l in text.splitlines() if re.match(r'^\s*\d+\s+\d+\s+[0-9.e+]+\s*$', l)]
                rows[(key, name)] = ' '.join(res[0].split()) if res else '?'

    for label, sql in queries:
        key = label.split()[0]
        print(label)

        for name, engine, mode in configs:
            print('    %-8s elapsed %7.3f  cpu %7.3f  %s  | %s' % (name, best.get((key, name), -1),
                  best.get((key, name, 'cpu'), -1), plans.get((key, name)), rows.get((key, name))))

        sys.stdout.flush()


main()
