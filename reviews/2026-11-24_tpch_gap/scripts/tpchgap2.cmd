@echo off
rem tpchgap2.cmd - follow-up of tpchgap.cmd on the engine nv (v5.0-impr-opt ddd4169f9a):
rem 1. TPC-H queries rewritten by hand the way the proposed optimizer changes would transform them
rem    (E:\fbdata\tg_rw\tpch\rw_NN.sql): the expected gain of every change;
rem 2. the scan queries 1, 6, 14 with a page cache that holds the whole database (130000 pages of 16K).
rem Results: E:\results\tpchgap_rw_tpch.csv, tpchgap_cache_tpch.csv, tpchgap_rw_out\. Then f2 and the original
rem config are put back.
set FB_CLIENT_DIR=C:\HQbird\Firebird50
set PY=python.exe
set CONF=E:\fb50-impropt\firebird.conf
set DB=E:/fbdata/impropt_work/TPCH_SF1_FB5.FDB
set OUTD=E:\results\tpchgap_rw_out
for /f "delims=" %%l in ('findstr /b /c:"set ISQL=" E:\fbdata\s036.cmd') do %%l
set ISQL_TPCH=%ISQL:imdb_fb5.fdb=TPCH_SF1_FB5.FDB%
if exist %OUTD% rd /s /q %OUTD%
md %OUTD%

call :swap engine13_nv.dll firebird_orig.conf
del /q E:\results\tpchgap_rw_tpch.csv E:\results\tpchgap_rw_tpch.log 2>nul
for %%i in (1 2) do call :fbone rw E:\fbdata\tg_rw\exp_tg_rw.json E:\fbdata\tg_rw 2
echo fb rw done %time%
for %%q in (rw_17 rw_20 rw_22) do %ISQL_TPCH% -i E:\fbdata\tg_rw\show_%%q.sql > %OUTD%\fb_%%q.txt 2>&1

for /f "delims=" %%l in ('findstr PGPASSWORD E:\pgdumps\tpchref_run.cmd') do %%l
set "LC_MESSAGES=C"
for %%q in (pg_rw_17 pg_rw_20 pg_rw_22) do C:\pgsql\bin\psql.exe -U postgres -d tpch -A -t -q -f E:\fbdata\tg_rw\%%q.sql > %OUTD%\%%q.csv 2> %OUTD%\%%q.err
set PGOPTIONS=-c max_parallel_workers_per_gather=0
for %%q in (pg_rw_17 pg_rw_20 pg_rw_22) do C:\pgsql\bin\psql.exe -U postgres -d tpch -A -t -q -f E:\fbdata\tg_rw\%%q.sql > %OUTD%\%%q_ser.csv 2> %OUTD%\%%q_ser.err
set PGOPTIONS=
set PGPASSWORD=
echo pg rw done %time%

call :swap engine13_nv.dll firebird_tg_cache.conf
del /q E:\results\tpchgap_cache_tpch.csv E:\results\tpchgap_cache_tpch.log 2>nul
for %%i in (1 2) do call :fbone cache E:\fbdata\tg_rw\exp_tg_scan.json E:\bench\queries_hu 3
echo fb cache done %time%
call E:\fbdata\wc_restore.cmd
echo TPCHGAP2DONE
goto :eof

:fbone
rem %1 = round name, %2 = query list, %3 = query folder, %4 = measured runs
%PY% -u E:\fbdata\tg_ab2.py --out E:\results\tpchgap_%1_tpch.csv --expected %2 --db %DB% --queries %3 --watchdog 180 --reps %4 >> E:\results\tpchgap_%1_tpch.log 2>&1
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
