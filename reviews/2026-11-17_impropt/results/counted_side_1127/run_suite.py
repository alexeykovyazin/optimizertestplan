"""Run the optimizer regression tests with one engine folder.

usage: run_suite.py <engine_dir> <work_dir> <out_dir> [first_number [last_number]]
"""
import glob
import os
import re
import subprocess
import sys
import time

REVIEWS = r'E:\Projects_Big\optimizertestplan\reviews'

ES = ['ExtendedStatistics = true', 'ShowExplainCardinality = true']
SEC = ['ShowExplainCardinality = true']
T8 = SEC + ['TempCacheLimit = 8M']

ALIASES = {
    'tst2': ES, 'tstnone': ['ExtendedStatistics = true'], 'tst2def': [],
    'tstbhj': ['ExtendedStatistics = true'],
    'tst8oj': ES, 'tst8like': ES, 'tst8sort': ES, 'tst8eq': ES,
    'tst9oj': ES, 'tst9bhj': ES, 'tst9esc': ES, 'tst9mig': ES, 'tst9w1251': ES, 'tst9pf': ES,
    'tst9rg': ES, 'tst9ojm': ES,
    'tst10bhj': ES, 'tst10bhj_def': [], 'tst10ci': ES, 'tst10tr': ES, 'tst10w1251': ES,
    'tst10oj': ES, 'tst10like': ES, 'tst10desc': ES, 'tst10rev': ES, 'tst10blob': ES,
    'tst11blb': ES, 'tst11or': ES + ['PredicateCorrelation = true'], 'tst11ordef': [],
    'tst12bhjlow': SEC + ['TempCacheLimit = 64M'], 'tst12hj': SEC, 'tst13star': SEC,
    'tst16hjtemp': T8 + ['SubQueryConversion = true'],
    'tst16hjtemp64k': T8 + ['HashJoinBatchMemory = 65536'],
    'tst16hjtemp0': T8 + ['HashJoinBatchMemory = 0'],
    'tst17hjprice': SEC, 'tst18fused': SEC,
    'tst19miss': ['DefaultDbCachePages = 1024'],
    'tst19missbig': ['DefaultDbCachePages = 20000'],
    'tst19missoff': ['DefaultDbCachePages = 1024', 'OptimizerPageMissCost = 0'],
    'tst20dpoff': [],
    'tst20dp12': ['JoinOrderDP = true', 'JoinOrderDPBudget = 12'],
    'tst20dp100': ['JoinOrderDP = true', 'JoinOrderDPBudget = 100'],
    'tsthagg512': ['AggregateHashMemory = 512K'],
    'tstsqc': ['SubQueryConversion = true'],
}


def main():
    engine, work, out = sys.argv[1:4]
    first = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    last = int(sys.argv[5]) if len(sys.argv) > 5 else 999

    os.makedirs(work, exist_ok=True)
    os.makedirs(out, exist_ok=True)

    conf = os.path.join(engine, 'databases.conf')
    text = open(conf, encoding='ascii', errors='replace').read()
    marker = '# --- test aliases ---'

    if marker in text:
        text = text[:text.index(marker)]

    lines = [marker]

    for alias, params in ALIASES.items():
        lines.append('%s = %s' % (alias, os.path.join(work, alias + '.fdb').replace('\\', '/')))

        if params:
            lines.append('{')
            lines.extend('\t' + p for p in params)
            lines.append('}')

    open(conf, 'w', encoding='ascii', newline='\r\n').write(text.rstrip() + '\n\n' + '\n'.join(lines) + '\n')

    tests = sorted(glob.glob(os.path.join(REVIEWS, '*_impropt', 'tests', '[0-9][0-9]*.sql')),
                   key=lambda p: os.path.basename(p))
    isql = os.path.join(engine, 'isql.exe')

    for path in tests:
        name = os.path.basename(path)
        number = int(name[:2])

        if number < first or number > last:
            continue

        raw = open(path, 'rb').read().decode('latin-1')

        for alias in re.findall(r"(?im)^\s*create database '([^']+)'", raw):
            f = os.path.join(work, alias + '.fdb')

            if os.path.exists(f):
                try:
                    os.remove(f)
                except OSError as e:
                    print('cannot remove', f, e, flush=True)

        start = time.time()

        try:
            p = subprocess.run([isql, '-q', '-i', path], cwd=work, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=2400)
            rc, data = p.returncode, p.stdout
        except subprocess.TimeoutExpired as e:
            rc, data = 'TIMEOUT', e.stdout or b''

        open(os.path.join(out, name[:-4] + '.txt'), 'wb').write(data + ('\n##### rc=%s\n' % rc).encode())
        print('%-45s rc=%s %.0fs' % (name, rc, time.time() - start), flush=True)


main()
