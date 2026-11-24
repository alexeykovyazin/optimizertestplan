@echo off
rem tpchgap6.cmd - scan micro-queries on LINEITEM with a page cache of 130000 pages (the whole database), engine nv:
rem round nofs = file system cache off (FileSystemCacheThreshold rule), round fs = UseFileSystemCache = true.
rem Results: E:\results\tpchgap_scan6_nofs.txt, tpchgap_scan6_fs.txt. Then f2 and the original config are put back.
set CONF=E:\fb50-impropt\firebird.conf
set PY=python.exe
for /f "delims=" %%l in ('findstr /b /c:"set ISQL=" E:\fbdata\s036.cmd') do %%l
set ISQL_TPCH=%ISQL:imdb_fb5.fdb=TPCH_SF1_FB5.FDB%
%PY% E:\fbdata\tg_mkconf6.py
call :round firebird_tg_cache.conf nofs
call :round firebird_tg_cache_fs.conf fs
call E:\fbdata\wc_restore.cmd
echo TPCHGAP6DONE
goto :eof

:round
sc stop FB_impropt >nul
ping -n 15 127.0.0.1 >nul
copy /y E:\fbdata\engine13_nv.dll E:\fb50-impropt\plugins\engine13.dll >nul
copy /y E:\fbdata\%1 %CONF% >nul
sc start FB_impropt >nul
ping -n 8 127.0.0.1 >nul
%ISQL_TPCH% -i E:\fbdata\tg_scan6_fb.sql > E:\results\tpchgap_scan6_%2.txt 2>&1
echo round %2 done %time%
goto :eof
