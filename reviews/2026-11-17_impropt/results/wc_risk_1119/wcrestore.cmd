@echo off
rem wcrestore.cmd - waits for the end of the timing runs, then makes sure the engine f2 is back
:wait
tasklist /fi "imagename eq python.exe" /nh | find /i "python.exe" >nul
if not errorlevel 1 (ping -n 16 127.0.0.1 >nul & goto wait)
ping -n 61 127.0.0.1 >nul
tasklist /fi "imagename eq python.exe" /nh | find /i "python.exe" >nul
if not errorlevel 1 goto wait
fc /b E:\fb50-impropt\plugins\engine13.dll E:\fbdata\engine13_f2.dll >nul && goto ok
echo RESTORING
sc stop FB_impropt >nul
ping -n 12 127.0.0.1 >nul
copy /y E:\fbdata\engine13_f2.dll E:\fb50-impropt\plugins\engine13.dll >nul
sc start FB_impropt >nul
ping -n 8 127.0.0.1 >nul
:ok
if exist E:\fbdata\wc_risk.txt del E:\fbdata\wc_risk.txt
fc /b E:\fb50-impropt\plugins\engine13.dll E:\fbdata\engine13_f2.dll >nul && echo ENGINE=f2
fc /b E:\fb50-impropt\firebird.conf E:\fbdata\firebird_orig.conf >nul && echo CONF=orig
sc query FB_impropt | find "4 "
for /f %%c in ('find /c "measured" ^< E:\results\wct_w42_v3.csv') do echo w42_v3 measured=%%c
echo DONE
