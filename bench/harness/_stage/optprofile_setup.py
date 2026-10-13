
import os, re, subprocess, time, zipfile, socket

ROOT = r"E:\fb50-optprofile"
SVC = "FB_optprofile"
ZIP = r"E:\fbdata\fb50-optprofile.zip"
os.environ["FB_CLIENT_DIR"] = r"C:\HQbird\Firebird50"

def run(cmd, timeout=600):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    return ((r.stdout or "") + (r.stderr or "")).strip()

print("== extract ==")
run(f"sc stop {SVC} >nul 2>&1 & sc delete {SVC} >nul 2>&1")
if os.path.exists(ROOT):
    run(f"rmdir /s /q {ROOT}")
    time.sleep(2)
os.makedirs(ROOT, exist_ok=True)
with zipfile.ZipFile(ZIP) as z:
    z.extractall(ROOT)
print("extracted:", len(os.listdir(ROOT)), "entries")

print("== init security ==")
secdb = os.path.join(ROOT, "SECURITY5.FDB")
init = os.path.join(ROOT, "_init_sec.sql")
open(init, "w", newline="\r\n").write(
    "create user SYSDBA password 'masterkey';\nexit;\n")
r = run(f'cd /d "{ROOT}" && isql.exe -user sysdba -i _init_sec.sql '
        f'"{secdb}"', 120)
print("isql:", (r or "(no output)")[:200])
os.remove(init)

print("== firebird.conf ==")
conf = os.path.join(ROOT, "firebird.conf")
lines = open(conf, encoding="utf-8", errors="replace").read().splitlines()
for want in ("RemoteServicePort = 3180", "ServerMode = Super",
             "DefaultDbCachePages = 2048", "LockMemSize = 20M",
             "LockHashSlots = 40099", "TempCacheLimit = 256M",
             "InlineSortThreshold = 16384"):
    key = want.split(" = ")[0]
    lines = [ln for ln in lines
             if not re.match(rf"^\s*{key}\s*=", ln, re.I)]
    lines.append(want)
open(conf, "w", newline="\r\n", encoding="utf-8").write("\n".join(lines)+"\n")
# рабочие каталоги БД
os.makedirs(r"E:\fbdata\optprofile_work", exist_ok=True)
print("conf ok")

print("== service ==")
print(run(f'sc create {SVC} binPath= "{ROOT}\\firebird.exe" '
          f'displayName= "Firebird OptProfile 3180" start= auto')[:200])
print(run("sc start " + SVC)[:200])
for i in range(30):
    time.sleep(1)
    try:
        with socket.create_connection(("127.0.0.1", 3180), 2):
            print("PORT 3180 UP")
            break
    except OSError:
        pass
else:
    raise SystemExit("port 3180 did not open")
print("SETUP DONE")
