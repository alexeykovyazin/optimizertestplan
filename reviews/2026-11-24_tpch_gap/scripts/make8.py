"""make8.py - eighth stand job: the whole Firebird part of the TPC-H comparison again with the settings that match
PostgreSQL: DefaultDbCachePages = 128K, UseFileSystemCache = true, and one connection held open for a round (the page
cache lives between runs, like shared_buffers). Output: tg_ab3.py, tg_mkconf8.py, tpchgap8.cmd, tpchgap8_start.cmd,
tpchgap8_launch.ps1."""
import os

here = os.path.dirname(os.path.abspath(__file__))

src = open(os.path.join(here, "tg_ab2.py"), encoding="utf-8").read()
old = "    expected = json.load(open(args.expected, encoding=\"utf-8\"))\n"
assert src.count(old) == 1
new = old + ("    # one connection stays open for the whole round: SuperServer keeps the database open and the page\n"
             "    # cache filled between the runs (PostgreSQL keeps shared_buffers the same way)\n"
             "    keeper = fbenv.connect_fb(args.db)\n"
             "    print(\"keeper connection is open\", flush=True)\n")
open(os.path.join(here, "tg_ab3.py"), "w", encoding="utf-8", newline="\n").write(src.replace(old, new))

mkconf = r'''"""tg_mkconf8.py - makes the configs of the settings parity with PostgreSQL: DefaultDbCachePages = 128K and
UseFileSystemCache = true. firebird_tg_par.conf comes from firebird_orig.conf, firebird_tg_par_dp.conf from
firebird_dpdef.conf (JoinOrderDP = true). Firebird takes the first occurrence of a key, so the line is replaced."""
import re

for src_name, dst_name in (("firebird_orig.conf", "firebird_tg_par.conf"),
                           ("firebird_dpdef.conf", "firebird_tg_par_dp.conf")):
    src = open("E:/fbdata/" + src_name, encoding="utf-8", errors="replace").read()
    assert not re.search(r"(?m)^UseFileSystemCache\s*=", src), src_name
    new, n = re.subn(r"(?m)^DefaultDbCachePages\s*=.*$", "DefaultDbCachePages = 128K\nUseFileSystemCache = true", src)
    assert n == 1, (src_name, n)
    open("E:/fbdata/" + dst_name, "w", encoding="utf-8", newline="").write(new)
print("conf8 made")
'''
open(os.path.join(here, "tg_mkconf8.py"), "w", encoding="utf-8", newline="\n").write(mkconf)

cmd = r"""@echo off
rem tpchgap8.cmd - TPC-H SF1, Firebird with the settings that match PostgreSQL: DefaultDbCachePages = 128K,
rem UseFileSystemCache = true, one connection held open for a round (tg_ab3.py).
rem Rounds: par_nv (v5.0-impr-opt ddd4169f9a, 19 queries), par_rw and par_rw4 (rewritten queries), par_dp (JoinOrderDP),
rem par_rel (v5.0-release), par_new (v5.0-release + PR 71), par_slow (queries 17, 20, 22, watchdog 600 s).
rem Results: E:\results\tpchgap_par_*. Then f2 and the original config are put back.
set FB_CLIENT_DIR=C:\HQbird\Firebird50
set PY=C:\Users\ak\AppData\Local\Programs\Python\Python313\python.exe
set CONF=E:\fb50-impropt\firebird.conf
set DB=E:/fbdata/impropt_work/TPCH_SF1_FB5.FDB
for /f "delims=" %%l in ('findstr /b /c:"set ISQL=" E:\fbdata\s036.cmd') do %%l
set ISQL_TPCH=%ISQL:imdb_fb5.fdb=TPCH_SF1_FB5.FDB%
%PY% E:\fbdata\tg_mkconf8.py
if errorlevel 1 (echo CONF8 FAILED & goto :eof)

call :swap engine13_nv.dll firebird_tg_par.conf
%ISQL_TPCH% -i E:\fbdata\tg_fbinfo.sql > E:\results\tpchgap_par_fbinfo.txt 2>&1
call :fb par_nv E:\fbdata\exp_tg_fast.json E:\bench\queries_hu 3 180
echo fb par_nv done %time%
call :fb par_rw E:\fbdata\tg_rw\exp_tg_rw.json E:\fbdata\tg_rw 3 180
echo fb par_rw done %time%
call :fb par_rw4 E:\fbdata\tg_rw4\exp_tg_rw4.json E:\fbdata\tg_rw4 3 180
echo fb par_rw4 done %time%
call :swap engine13_nv.dll firebird_tg_par_dp.conf
call :fb par_dp E:\fbdata\exp_tg_fast.json E:\bench\queries_hu 3 180
echo fb par_dp done %time%
call :swap engine13_rel.dll firebird_tg_par.conf
call :fb par_rel E:\fbdata\exp_tg_fast.json E:\bench\queries_hu 3 180
echo fb par_rel done %time%
call :swap engine13_ojh.dll firebird_tg_par.conf
call :fb par_new E:\fbdata\exp_tg_fast.json E:\bench\queries_hu 3 180
echo fb par_new done %time%
call :swap engine13_nv.dll firebird_tg_par.conf
call :fb par_slow E:\fbdata\exp_tg_slow.json E:\bench\queries_hu 1 600
echo fb par_slow done %time%
call E:\fbdata\wc_restore.cmd
echo TPCHGAP8DONE
goto :eof

:fb
rem %1 = round name, %2 = query list, %3 = query folder, %4 = measured runs, %5 = watchdog, seconds
del /q E:\results\tpchgap_%1_tpch.csv E:\results\tpchgap_%1_tpch.log 2>nul
for %%i in (1 2) do call :fbone %1 %2 %3 %4 %5
goto :eof

:fbone
%PY% -u E:\fbdata\tg_ab3.py --out E:\results\tpchgap_%1_tpch.csv --expected %2 --db %DB% --queries %3 --watchdog %5 --reps %4 >> E:\results\tpchgap_%1_tpch.log 2>&1
sc query FB_impropt | findstr RUNNING >nul || (echo SERVER DOWN in %1 & sc start FB_impropt >nul & ping -n 12 127.0.0.1 >nul)
goto :eof

:swap
sc stop FB_impropt >nul
ping -n 15 127.0.0.1 >nul
copy /y E:\fbdata\%1 E:\fb50-impropt\plugins\engine13.dll >nul
copy /y E:\fbdata\%2 %CONF% >nul
sc start FB_impropt >nul
ping -n 8 127.0.0.1 >nul
goto :eof
"""
open(os.path.join(here, "tpchgap8.cmd"), "wb").write(cmd.replace("\n", "\r\n").encode("ascii"))
open(os.path.join(here, "tpchgap8_start.cmd"), "wb").write(
    b"@echo off\r\ncall E:\\fbdata\\tpchgap8.cmd > E:\\results\\tpchgap8.log 2>&1\r\n")
open(os.path.join(here, "tpchgap8_launch.ps1"), "w", encoding="ascii", newline="\r\n").write(
    "$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments "
    "@{CommandLine = 'cmd /c E:\\fbdata\\tpchgap8_start.cmd'}\n\"rc=$($r.ReturnValue) pid=$($r.ProcessId)\"\n")
print("made8")
