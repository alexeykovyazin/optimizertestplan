@echo off
rem tpchgap4.cmd - the TPC-H queries with DATE literals in place of CAST('...' AS DATE) and DATEADD(...), engine nv
rem (v5.0-impr-opt ddd4169f9a). Results: E:\results\tpchgap_rw4_tpch.csv. Then f2 and the original config are put back.
set FB_CLIENT_DIR=C:\HQbird\Firebird50
set PY=python.exe
set CONF=E:\fb50-impropt\firebird.conf
sc stop FB_impropt >nul
ping -n 15 127.0.0.1 >nul
copy /y E:\fbdata\engine13_nv.dll E:\fb50-impropt\plugins\engine13.dll >nul
copy /y E:\fbdata\firebird_orig.conf %CONF% >nul
sc start FB_impropt >nul
ping -n 8 127.0.0.1 >nul
del /q E:\results\tpchgap_rw4_tpch.csv E:\results\tpchgap_rw4_tpch.log 2>nul
%PY% -u E:\fbdata\tg_ab2.py --out E:\results\tpchgap_rw4_tpch.csv --expected E:\fbdata\tg_rw4\exp_tg_rw4.json --db E:/fbdata/impropt_work/TPCH_SF1_FB5.FDB --queries E:\fbdata\tg_rw4 --watchdog 180 --reps 3 >> E:\results\tpchgap_rw4_tpch.log 2>&1
echo fb rw4 done %time%
call E:\fbdata\wc_restore.cmd
echo TPCHGAP4DONE
