"""make_rw4.py - fourth stand job: every TPC-H query that holds CAST('...' AS DATE) or DATEADD(... TO CAST(...)) is
rewritten with DATE literals (the constant expression is folded by hand). It measures what compile-time folding of
constant expressions gives. Output: rw4/tpch/rw4_NN.sql, rw4/exp_tg_rw4.json, tpchgap4*.{cmd,ps1}."""
import datetime
import json
import os
import re

here = os.path.dirname(os.path.abspath(__file__))
src = r"E:\Projects_Big\optimizertestplan\bench\queries\tpch"
out = os.path.join(here, "rw4")
os.makedirs(os.path.join(out, "tpch"), exist_ok=True)

CAST = r"CAST\('(\d{4})-(\d{2})-(\d{2})' AS DATE\)"
DATEADD = re.compile(r"DATEADD\((-?\d+) (DAY|MONTH|YEAR) TO " + CAST + r"\)")


def add(m):
    n, unit = int(m.group(1)), m.group(2)
    d = datetime.date(int(m.group(3)), int(m.group(4)), int(m.group(5)))
    if unit == "DAY":
        d += datetime.timedelta(days=n)
    else:
        months = d.year * 12 + d.month - 1 + (n if unit == "MONTH" else 12 * n)
        d = d.replace(year=months // 12, month=months % 12 + 1)  # the day is 1 in every TPC-H bound
    return "date '%s'" % d.isoformat()


made = []
for n in range(1, 23):
    if n in (17, 20, 22):
        continue
    text = open(os.path.join(src, "tpch_%02d.sql" % n), encoding="utf-8").read().replace("\r\n", "\n")
    new = DATEADD.sub(add, text)
    new = re.sub(CAST, r"date '\1-\2-\3'", new)
    assert "CAST(" not in new and "DATEADD" not in new, n
    if new != text:
        name = "rw4_%02d" % n
        made.append(name)
        with open(os.path.join(out, "tpch", name + ".sql"), "w", encoding="utf-8", newline="\n") as f:
            f.write(new.rstrip() + "\n")
        for ln in new.splitlines():
            if "date '" in ln:
                print(name, ln.strip())

json.dump({name: {"suite": "tpch", "checksum": None, "rows": None, "median_ms": 0, "timed_out": False}
           for name in made}, open(os.path.join(out, "exp_tg_rw4.json"), "w", encoding="utf-8"))

cmd = r"""@echo off
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
"""
open(os.path.join(here, "tpchgap4.cmd"), "wb").write(cmd.replace("\n", "\r\n").encode("ascii"))
open(os.path.join(here, "tpchgap4_start.cmd"), "wb").write(
    b"@echo off\r\ncall E:\\fbdata\\tpchgap4.cmd > E:\\results\\tpchgap4.log 2>&1\r\n")
open(os.path.join(here, "tpchgap4_launch.ps1"), "w", encoding="ascii", newline="\r\n").write(
    "$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments "
    "@{CommandLine = 'cmd /c E:\\fbdata\\tpchgap4_start.cmd'}\n\"rc=$($r.ReturnValue) pid=$($r.ProcessId)\"\n")
print("made4", made)
