"""mktime.py - the timing runs of the worst case rule: the expected files of the changed queries and wctime.cmd."""
import json, sys

sys.argv = sys.argv[:1]
exec(open('cmpplans.py').read().split("print('plans loaded:'")[0])
EXP = {}
for f in ('expected_joblight70.json', 'expected_ceb121.json', 'expected_scale500.json'):
    EXP.update(json.load(open(SP + 'stand/' + f, encoding='utf-8')))
runs = []
for e in ('wb', 'w42'):
    d = {v: diff(e + '_v0', e + '_' + v) for v in ('v1', 'v2', 'v3')}
    union = [q for q in ids if any(q in d[v] for v in d)]
    for v, qs in [('v0', union)] + list(d.items()):
        miss = [q for q in qs if q not in EXP]
        assert not miss, miss
        name = 'expected_wc_%s_%s.json' % (e, v)
        json.dump({q: EXP[q] for q in qs}, open(SP + 'stand/' + name, 'w', encoding='utf-8'), indent=1)
        runs.append((e, v, name, len(qs)))
BS = chr(92)
FBD = 'E:/fbdata/'.replace('/', BS)
RES = 'E:/results/'.replace('/', BS)
lines = ['@echo off', 'rem wctime.cmd - the timing of the queries whose plan the worst case rule changes',
         'set FB_CLIENT_DIR=' + 'C:/HQbird/Firebird50'.replace('/', BS),
         'set PY=' + 'C:/Users/ak/AppData/Local/Programs/Python/Python313/python.exe'.replace('/', BS)]
for e, v, name, n in runs:
    lines += ['call :swap engine13_%s.dll wc_%s.txt' % (e, v),
              '%PY% -u ' + FBD + 'hash_supervisor.py --out ' + RES + 'wct_%s_%s.csv --expected ' % (e, v) + FBD + name +
              ' >> ' + RES + 'wct_%s_%s.log 2>&1' % (e, v),
              'echo %s %s done %%TIME%%' % (e, v)]
ENG = 'E:/fb50-impropt/plugins/engine13.dll'.replace('/', BS)
lines += ['call :swap engine13_f2.dll', 'if exist ' + FBD + 'wc_risk.txt del ' + FBD + 'wc_risk.txt',
          'fc /b ' + ENG + ' ' + FBD + 'engine13_f2.dll >nul && echo RESTORED f2', 'echo DONE', 'goto :eof',
          ':swap', 'sc stop FB_impropt >nul', 'ping -n 12 127.0.0.1 >nul',
          'copy /y ' + FBD + '%1 ' + ENG + ' >nul',
          'if not "%2"=="" copy /y ' + FBD + '%2 ' + FBD + 'wc_risk.txt >nul',
          'sc start FB_impropt >nul', 'ping -n 8 127.0.0.1 >nul', 'goto :eof']
open(SP + 'stand/wctime.cmd', 'w', newline='').write('\r\n'.join(lines) + '\r\n')
print(runs)
