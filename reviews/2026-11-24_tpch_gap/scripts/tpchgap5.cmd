@echo off
rem tpchgap5.cmd - scan micro-queries on LINEITEM: Firebird engine nv (v5.0-impr-opt ddd4169f9a, original config) and
rem PostgreSQL 17 in one process. Results: E:\results\tpchgap_scan_fb.txt, tpchgap_scan_pg.txt. Then f2 is put back.
set CONF=E:\fb50-impropt\firebird.conf
for /f "delims=" %%l in ('findstr /b /c:"set ISQL=" E:\fbdata\s036.cmd') do %%l
set ISQL_TPCH=%ISQL:imdb_fb5.fdb=TPCH_SF1_FB5.FDB%
set GSTAT_TPCH=%ISQL_TPCH:isql.exe=gstat.exe%
set GSTAT_TPCH=%GSTAT_TPCH:-ch utf8 =%
sc stop FB_impropt >nul
ping -n 15 127.0.0.1 >nul
copy /y E:\fbdata\engine13_nv.dll E:\fb50-impropt\plugins\engine13.dll >nul
copy /y E:\fbdata\firebird_orig.conf %CONF% >nul
sc start FB_impropt >nul
ping -n 8 127.0.0.1 >nul
%ISQL_TPCH% -i E:\fbdata\tg_scan_fb.sql > E:\results\tpchgap_scan_fb.txt 2>&1
echo fb scan done %time%
%GSTAT_TPCH% -r -t LINEITEM > E:\results\tpchgap_scan_gstat.txt 2>&1
echo gstat done %time%
for /f "delims=" %%l in ('findstr PGPASSWORD E:\pgdumps\tpchref_run.cmd') do %%l
set "LC_MESSAGES=C"
set PGOPTIONS=-c max_parallel_workers_per_gather=0
C:\pgsql\bin\psql.exe -U postgres -d tpch -f E:\fbdata\tg_scan_pg.sql > E:\results\tpchgap_scan_pg.txt 2>&1
set PGOPTIONS=
set PGPASSWORD=
echo pg scan done %time%
call E:\fbdata\wc_restore.cmd
echo TPCHGAP5DONE
