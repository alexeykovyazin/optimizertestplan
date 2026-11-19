@echo off
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
:swap
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
