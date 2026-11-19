"""mkstand.py - the stand files of the worst case rule research: the script with all the queries (plans only),
the list of the query ids, the parameter files of the variants and the .cmd scripts (CRLF)."""
import glob, os, re

SP = 'C:/Users/aleks/AppData/Local/Temp/claude/c255271938a7846a/58624a2e-45d9-4769-ae51-5e8b14b87350/scratchpad/wc/'
B = 'E:/Projects_Big/optimizertestplan/bench/queries/'
OUT = SP + 'stand/'

# all the queries, one statement each
ids, sql = [], ['set planonly on;']
for suite in ('job-light', 'ceb-imdb-regen', 'scale'):
    for f in sorted(glob.glob(B + suite + '/*.sql')):
        q = open(f, encoding='utf-8').read().strip().rstrip(';').strip()
        assert ';' not in q, f
        ids.append(os.path.basename(f)[:-4])
        sql.append(q + ';')
open(OUT + 'wc_allplans.sql', 'w', encoding='utf-8', newline='\n').write('\n'.join(sql) + '\n')
open(SP + 'wc_qids.txt', 'w', newline='\n').write('\n'.join(ids) + '\n')

# the key degrees: relation, index id, average, size-biased, max
deg = []
for line in open(SP + 'wc_deg.txt', encoding='utf-8', errors='replace'):
    if line.startswith('DEG|'):
        _, t, ix, iid, n, sc, sc2, mx = line.strip().split('|')
        n, sc, sc2, mx = float(n), float(sc), float(sc2), float(mx)
        deg.append('%s %s %.6f %.6f %.0f' % (t, iid, sc / n, sc2 / sc, mx))
assert len(deg) == 23

# variants: mode weight defRatio cap unique
V = {'v0': '0 0.5 4 0 0', 'v1': '2 0.5 4 0 0', 'v2': '1 0.5 4 0 0', 'v3': '2 0.64 4 0 0', 'v4': '1 0.19 4 0 0',
     'v5': '3 0.5 4 0 0'}
for v, head in V.items():
    open(OUT + 'wc_%s.txt' % v, 'w', newline='\n').write(head + '\n' + '\n'.join(deg) + '\n')


def cmd(name, text):
    open(OUT + name, 'w', newline='').write(text.replace('\n', '\r\n'))


SWAP = r''':swap
:waitidle
tasklist /fi "imagename eq isql.exe" /nh | find /i "isql.exe" >nul
if not errorlevel 1 (ping -n 6 127.0.0.1 >nul & goto waitidle)
sc stop FB_impropt >nul
ping -n 12 127.0.0.1 >nul
copy /y E:\fbdata\%1 E:\fb50-impropt\plugins\engine13.dll >nul
if not "%2"=="" copy /y E:\fbdata\%2 E:\fbdata\wc_risk.txt >nul
sc start FB_impropt >nul
ping -n 8 127.0.0.1 >nul
goto :eof
'''

cmd('wcplans.cmd', r'''@echo off
rem wcplans.cmd - the plans of all the queries for every variant of the worst case rule, on the base and on PR 42
for /f "delims=" %%l in ('findstr /b /c:"set ISQL=" E:\fbdata\s036.cmd') do %%l
for %%e in (wb w42) do for %%v in (v0 v1 v2 v3 v4 v5) do call :one %%e %%v
call :swap engine13_f2.dll
if exist E:\fbdata\wc_risk.txt del E:\fbdata\wc_risk.txt
fc /b E:\fb50-impropt\plugins\engine13.dll E:\fbdata\engine13_f2.dll >nul && echo RESTORED f2
echo DONE
goto :eof
:one
call :swap engine13_%1.dll wc_%2.txt
%ISQL% -i E:\fbdata\wc_allplans.sql > E:\results\wcp_%1_%2.txt 2>&1
for /f %%c in ('find /c "PLAN" ^< E:\results\wcp_%1_%2.txt') do echo %1 %2 plans=%%c
goto :eof
''' + SWAP)
print(len(ids), 'queries;', len(V), 'variants')
