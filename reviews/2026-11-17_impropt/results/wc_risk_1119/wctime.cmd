@echo off
rem wctime.cmd - the timing of the queries whose plan the worst case rule changes
set FB_CLIENT_DIR=C:\HQbird\Firebird50
set PY=C:\Users\ak\AppData\Local\Programs\Python\Python313\python.exe
call :swap engine13_wb.dll wc_v0.txt
%PY% -u E:\fbdata\hash_supervisor.py --out E:\results\wct_wb_v0.csv --expected E:\fbdata\expected_wc_wb_v0.json >> E:\results\wct_wb_v0.log 2>&1
echo wb v0 done %TIME%
call :swap engine13_wb.dll wc_v1.txt
%PY% -u E:\fbdata\hash_supervisor.py --out E:\results\wct_wb_v1.csv --expected E:\fbdata\expected_wc_wb_v1.json >> E:\results\wct_wb_v1.log 2>&1
echo wb v1 done %TIME%
call :swap engine13_wb.dll wc_v2.txt
%PY% -u E:\fbdata\hash_supervisor.py --out E:\results\wct_wb_v2.csv --expected E:\fbdata\expected_wc_wb_v2.json >> E:\results\wct_wb_v2.log 2>&1
echo wb v2 done %TIME%
call :swap engine13_wb.dll wc_v3.txt
%PY% -u E:\fbdata\hash_supervisor.py --out E:\results\wct_wb_v3.csv --expected E:\fbdata\expected_wc_wb_v3.json >> E:\results\wct_wb_v3.log 2>&1
echo wb v3 done %TIME%
call :swap engine13_w42.dll wc_v0.txt
%PY% -u E:\fbdata\hash_supervisor.py --out E:\results\wct_w42_v0.csv --expected E:\fbdata\expected_wc_w42_v0.json >> E:\results\wct_w42_v0.log 2>&1
echo w42 v0 done %TIME%
call :swap engine13_w42.dll wc_v1.txt
%PY% -u E:\fbdata\hash_supervisor.py --out E:\results\wct_w42_v1.csv --expected E:\fbdata\expected_wc_w42_v1.json >> E:\results\wct_w42_v1.log 2>&1
echo w42 v1 done %TIME%
call :swap engine13_w42.dll wc_v2.txt
%PY% -u E:\fbdata\hash_supervisor.py --out E:\results\wct_w42_v2.csv --expected E:\fbdata\expected_wc_w42_v2.json >> E:\results\wct_w42_v2.log 2>&1
echo w42 v2 done %TIME%
call :swap engine13_w42.dll wc_v3.txt
%PY% -u E:\fbdata\hash_supervisor.py --out E:\results\wct_w42_v3.csv --expected E:\fbdata\expected_wc_w42_v3.json >> E:\results\wct_w42_v3.log 2>&1
echo w42 v3 done %TIME%
call :swap engine13_f2.dll
if exist E:\fbdata\wc_risk.txt del E:\fbdata\wc_risk.txt
fc /b E:\fb50-impropt\plugins\engine13.dll E:\fbdata\engine13_f2.dll >nul && echo RESTORED f2
echo DONE
goto :eof
:swap
sc stop FB_impropt >nul
ping -n 12 127.0.0.1 >nul
copy /y E:\fbdata\%1 E:\fb50-impropt\plugins\engine13.dll >nul
if not "%2"=="" copy /y E:\fbdata\%2 E:\fbdata\wc_risk.txt >nul
sc start FB_impropt >nul
ping -n 8 127.0.0.1 >nul
goto :eof
