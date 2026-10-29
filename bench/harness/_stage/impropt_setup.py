
import os, re, subprocess, time, zipfile, socket

ROOT = r"E:\fb50-impropt"
SVC = "FB_impropt"
ZIP = r"E:\fbdata\fb50-impropt.zip"
os.environ["FB_CLIENT_DIR"] = r"C:\HQbird\Firebird50"

def run(cmd, timeout=600):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    return ((r.stdout or "") + (r.stderr or "")).strip()

print("== extract ==")
run(f"sc stop {SVC} >nul 2>&1")
run(f"sc delete {SVC} >nul 2>&1")
if os.path.exists(ROOT):
    run(f"rmdir /s /q {ROOT}")
    time.sleep(2)
os.makedirs(ROOT, exist_ok=True)
with zipfile.ZipFile(ZIP) as z:
    z.extractall(ROOT)
print("extracted:", len(os.listdir(ROOT)), "entries")

print("== init security db ==")
init = os.path.join(ROOT, "_init_sec.sql")
open(init, "w", newline="\r\n").write(
    "create user SYSDBA password 'masterkey';\nexit;\n")
r = run(f'"{ROOT}\\isql.exe" -user sysdba -i "{init}" '
        f'"{ROOT}\\SECURITY5.FDB"', 120)
print("isql:", r or "(no output)")
os.remove(init)
assert "Statement failed" not in r or     "UNIQUE KEY" in r or "PRIMARY" in r,     "security init failed: " + r[:200]  # SYSDBA уже создан — допустимо

print("== firebird.conf ==")
conf = os.path.join(ROOT, "firebird.conf")
lines = open(conf, encoding="utf-8", errors="replace").read().splitlines()
for want in ("RemoteServicePort = 3056", "ServerMode = Super",
             "DefaultDbCachePages = 50000", "LockMemSize = 20M",
             "LockHashSlots = 40099", "TempCacheLimit = 2000M",
             "InlineSortThreshold = 16384",
             "ShowExplainCardinality = true", "PredicateCorrelation = true",
             "ExtendedStatistics = true", "SubQueryConversion = true"):
    key = want.split(" = ")[0]
    if not any(re.match(rf"^\s*{key}\s*=", ln, re.I) for ln in lines):
        lines.append(want)
open(conf, "w", newline="\r\n", encoding="utf-8").write("\n".join(lines) + "\n")
print("conf ok, lines:", len(lines))
print("SETUP DONE")
