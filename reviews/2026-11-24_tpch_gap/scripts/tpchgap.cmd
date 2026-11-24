@echo off
rem tpchgap.cmd - TPC-H SF1 on this stand: Firebird engine nv (v5.0-impr-opt ddd4169f9a) against PostgreSQL 17.
rem Phases: Firebird 19 queries (config orig, then JoinOrderDP on), PostgreSQL (parallel, then serial, then
rem plans), Firebird queries 17, 20, 22 (one run, watchdog 600 s). Results: E:\results\tpchgap_*.
rem Then f2 and the original config are put back.
set FB_CLIENT_DIR=C:\HQbird\Firebird50
set PY=python.exe
set CONF=E:\fb50-impropt\firebird.conf
set DB=E:/fbdata/impropt_work/TPCH_SF1_FB5.FDB
set PGDIR=E:\results\tpchgap_pg
for /f "delims=" %%l in ('findstr /b /c:"set ISQL=" E:\fbdata\s036.cmd') do %%l
set ISQL_TPCH=%ISQL:imdb_fb5.fdb=TPCH_SF1_FB5.FDB%

call :swap engine13_nv.dll firebird_orig.conf
%ISQL_TPCH% -i E:\fbdata\tg_fbinfo.sql > E:\results\tpchgap_fbinfo.txt 2>&1
call :fb nv_orig fast 3
echo fb orig done %time%
call :swap engine13_nv.dll firebird_dpdef.conf
call :fb nv_dp fast 2
echo fb dp done %time%

if exist %PGDIR% rd /s /q %PGDIR%
md %PGDIR%
md %PGDIR%\sql
for /f "delims=" %%l in ('findstr PGPASSWORD E:\pgdumps\tpchref_run.cmd') do %%l
set "LC_MESSAGES=C"
C:\pgsql\bin\psql.exe -U postgres -d tpch -A -q -f E:\fbdata\tg_pginfo.sql > E:\results\tpchgap_pginfo.txt 2>&1
%PY% E:\fbdata\tg_pg.py prep
set PGOPTIONS=
call :pg par
set PGOPTIONS=-c max_parallel_workers_per_gather=0
call :pg ser
set PGOPTIONS=
call :pgplans par
set PGOPTIONS=-c max_parallel_workers_per_gather=0
call :pgplans ser
set PGOPTIONS=
set PGPASSWORD=
%PY% E:\fbdata\tg_pg.py sum
echo pg done %time%

call :swap engine13_nv.dll firebird_orig.conf
call :fb nv_slow slow 1
echo fb slow done %time%
call E:\fbdata\wc_restore.cmd
echo TPCHGAPDONE
goto :eof

:fb
rem %1 = round name, %2 = query list (fast, slow), %3 = measured runs
del /q E:\results\tpchgap_%1_tpch.csv E:\results\tpchgap_%1_tpch.log 2>nul
for %%i in (1 2) do call :fbone %1 %2 %3
goto :eof

:fbone
%PY% -u E:\fbdata\tg_ab.py --out E:\results\tpchgap_%1_tpch.csv --expected E:\fbdata\exp_tg_%2.json --db %DB% --queries E:\bench\queries_hu --watchdog 600 --reps %3 >> E:\results\tpchgap_%1_tpch.log 2>&1
sc query FB_impropt | findstr RUNNING >nul || (echo SERVER DOWN in %1 & sc start FB_impropt >nul & ping -n 12 127.0.0.1 >nul)
goto :eof

:pg
rem %1 = mode name; PGOPTIONS is set by the caller
for %%r in (1 2 3) do call :pground %1 %%r
goto :eof

:pground
md %PGDIR%\%1_r%2
for %%f in (E:\pgdumps\tpchref\q_tpch_*.sql) do call :pgone %%f %%~nf %1_r%2
goto :eof

:pgone
if "%2"=="q_tpch_17" goto :eof
if "%2"=="q_tpch_20" goto :eof
C:\pgsql\bin\psql.exe -U postgres -d tpch -A -t -q -f %1 > %PGDIR%\%3\%2.csv 2> %PGDIR%\%3\%2.err
goto :eof

:pgplans
md %PGDIR%\plan_%1
for %%f in (%PGDIR%\sql\pe_tpch_*.sql) do C:\pgsql\bin\psql.exe -U postgres -d tpch -A -t -q -f %%f > %PGDIR%\plan_%1\%%~nf.json 2> %PGDIR%\plan_%1\%%~nf.err
goto :eof

:swap
sc stop FB_impropt >nul
ping -n 15 127.0.0.1 >nul
copy /y E:\fbdata\%1 E:\fb50-impropt\plugins\engine13.dll >nul
copy /y E:\fbdata\%2 %CONF% >nul
sc start FB_impropt >nul
ping -n 8 127.0.0.1 >nul
goto :eof
