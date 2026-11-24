"""make_rw3.py - third stand job: queries 4, 10, 12 with both date bounds written as DATE literals (not CAST, not
DATEADD), to check the joint range estimate of Optimizer::computeConjunctSelectivities. Output: rw3/tpch/rw3_NN.sql,
rw3/exp_tg_rw3.json, tpchgap3.cmd, tpchgap3_start.cmd, tpchgap3_launch.ps1."""
import json
import os

here = os.path.dirname(os.path.abspath(__file__))
src = r"E:\Projects_Big\optimizertestplan\bench\queries\tpch"
out = os.path.join(here, "rw3")
os.makedirs(os.path.join(out, "tpch"), exist_ok=True)


def rewrite(n, pairs):
    text = open(os.path.join(src, "tpch_%02d.sql" % n), encoding="utf-8").read().replace("\r\n", "\n")
    for old, new in pairs:
        assert text.count(old) == 1, (n, old, text.count(old))
        text = text.replace(old, new)
    with open(os.path.join(out, "tpch", "rw3_%02d.sql" % n), "w", encoding="utf-8", newline="\n") as f:
        f.write(text.rstrip() + "\n")


rewrite(4, [("o_orderdate < DATEADD(3 MONTH TO CAST('1994-11-01' AS DATE))", "o_orderdate < date '1995-02-01'"),
            ("o_orderdate >= CAST('1994-11-01' AS DATE)", "o_orderdate >= date '1994-11-01'")])
rewrite(10, [("o_orderdate < DATEADD(3 MONTH TO CAST('1993-04-01' AS DATE))", "o_orderdate < date '1993-07-01'"),
             ("o_orderdate >= CAST('1993-04-01' AS DATE)", "o_orderdate >= date '1993-04-01'")])
rewrite(12, [("l_receiptdate < DATEADD(1 YEAR TO CAST('1994-01-01' AS DATE))", "l_receiptdate < date '1995-01-01'"),
             ("l_receiptdate >= CAST('1994-01-01' AS DATE)", "l_receiptdate >= date '1994-01-01'")])

json.dump({"rw3_%02d" % n: {"suite": "tpch", "checksum": None, "rows": None, "median_ms": 0, "timed_out": False}
           for n in (4, 10, 12)}, open(os.path.join(out, "exp_tg_rw3.json"), "w", encoding="utf-8"))

cmd = r"""@echo off
rem tpchgap3.cmd - queries 4, 10, 12 with DATE literals as both range bounds, engine nv (v5.0-impr-opt ddd4169f9a).
rem Results: E:\results\tpchgap_rw3_tpch.csv. Then f2 and the original config are put back.
set FB_CLIENT_DIR=C:\HQbird\Firebird50
set PY=python.exe
set CONF=E:\fb50-impropt\firebird.conf
sc stop FB_impropt >nul
ping -n 15 127.0.0.1 >nul
copy /y E:\fbdata\engine13_nv.dll E:\fb50-impropt\plugins\engine13.dll >nul
copy /y E:\fbdata\firebird_orig.conf %CONF% >nul
sc start FB_impropt >nul
ping -n 8 127.0.0.1 >nul
del /q E:\results\tpchgap_rw3_tpch.csv E:\results\tpchgap_rw3_tpch.log 2>nul
%PY% -u E:\fbdata\tg_ab2.py --out E:\results\tpchgap_rw3_tpch.csv --expected E:\fbdata\tg_rw3\exp_tg_rw3.json --db E:/fbdata/impropt_work/TPCH_SF1_FB5.FDB --queries E:\fbdata\tg_rw3 --watchdog 180 --reps 2 >> E:\results\tpchgap_rw3_tpch.log 2>&1
echo fb rw3 done %time%
call E:\fbdata\wc_restore.cmd
echo TPCHGAP3DONE
"""
open(os.path.join(here, "tpchgap3.cmd"), "wb").write(cmd.replace("\n", "\r\n").encode("ascii"))
open(os.path.join(here, "tpchgap3_start.cmd"), "wb").write(
    b"@echo off\r\ncall E:\\fbdata\\tpchgap3.cmd > E:\\results\\tpchgap3.log 2>&1\r\n")
open(os.path.join(here, "tpchgap3_launch.ps1"), "w", encoding="ascii", newline="\r\n").write(
    "$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments "
    "@{CommandLine = 'cmd /c E:\\fbdata\\tpchgap3_start.cmd'}\n\"rc=$($r.ReturnValue) pid=$($r.ProcessId)\"\n")
print("made3")
