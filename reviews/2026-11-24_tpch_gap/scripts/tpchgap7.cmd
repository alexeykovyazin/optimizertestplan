@echo off
rem tpchgap7.cmd - partial record unpack: engine pb (base a0960b59ad) against engine pu (the same commit with the
rem patch), original config. Scan micro-queries in isql and the 19 TPC-H queries through the harness.
rem Results: E:\results\tpchgap_scan7_pb.txt, tpchgap_scan7_pu.txt, tpchgap_pb_tpch.csv, tpchgap_pu_tpch.csv.
rem Then f2 and the original config are put back.
set FB_CLIENT_DIR=C:\HQbird\Firebird50
set CONF=E:\fb50-impropt\firebird.conf
set PY=python.exe
for /f "delims=" %%l in ('findstr /b /c:"set ISQL=" E:\fbdata\s036.cmd') do %%l
set ISQL_TPCH=%ISQL:imdb_fb5.fdb=TPCH_SF1_FB5.FDB%
call :round pb
call :round pu
call :round2 pb
call :round2 pu
call E:\fbdata\wc_restore.cmd
echo TPCHGAP7DONE
goto :eof

:swap
sc stop FB_impropt >nul
ping -n 15 127.0.0.1 >nul
copy /y E:\fbdata\engine13_%1.dll E:\fb50-impropt\plugins\engine13.dll >nul
copy /y E:\fbdata\firebird_orig.conf %CONF% >nul
sc start FB_impropt >nul
ping -n 8 127.0.0.1 >nul
goto :eof

:round
call :swap %1
%ISQL_TPCH% -i E:\fbdata\tg_scan7_fb.sql > E:\results\tpchgap_scan7_%1.txt 2>&1
echo scan %1 done %time%
goto :eof

:round2
call :swap %1
del /q E:\results\tpchgap_%1_tpch.csv E:\results\tpchgap_%1_tpch.log 2>nul
%PY% -u E:\fbdata\tg_ab2.py --out E:\results\tpchgap_%1_tpch.csv --expected E:\fbdata\exp_tg_fast.json --db E:/fbdata/impropt_work/TPCH_SF1_FB5.FDB --queries E:\bench\queries_hu --watchdog 600 --reps 3 >> E:\results\tpchgap_%1_tpch.log 2>&1
sc query FB_impropt | findstr RUNNING >nul || (echo SERVER DOWN in %1 & sc start FB_impropt >nul & ping -n 12 127.0.0.1 >nul)
echo tpch %1 done %time%
goto :eof
