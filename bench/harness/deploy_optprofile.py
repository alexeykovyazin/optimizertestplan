"""Деплой OptProfile-сборки (feature/optimization-profile) на dellg15.

Распаковка в E:\fb50-optprofile, инициализация SECURITY5.FDB (SYSDBA),
конфиг (порт 3180, паритет кэша), служба FB_optprofile, smoke:
attach, create table, PREPARE с планом. Запуск локально:
  python bench/harness/deploy_optprofile.py
"""
import subprocess
import time

STAGE = r"E:\Projects_Big\optimizertestplan\bench\harness\_stage"

REMOTE = r'''
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
'''

SMOKE = r'''
import sys
sys.path.insert(0, r"E:\bench\harness")
import fbenv
fbenv.HOST_PORT = "localhost:3180"
fbenv.ensure_client()
from firebird.driver import connect, create_database
import os
dbp = r"E:\fbdata\optprofile_work\smoke.fdb"
dsn = "inet://localhost:3180/" + dbp.replace(os.sep, "/")
try: os.remove(dbp)
except OSError: pass
db = create_database(dsn, user="SYSDBA", password="masterkey", charset="UTF8")
db.close()
db = connect(dsn, user="SYSDBA", password="masterkey", charset="UTF8")
cur = db.cursor()
db.begin()
cur.execute("create table t (id integer primary key, v varchar(20))")
db.commit()
db.begin()
cur.execute("insert into t values (1,'a')")
db.commit()
ps = cur.prepare("select count(*) from t where v = 'a'")
print("PLAN:", (ps.plan or "").replace(chr(10), " | "))
assert cur.execute("select count(*) from t where v='a'").fetchone()[0] == 1
db.close()
print("SMOKE OK")
'''


def ssh(cmd, timeout=900):
    r = subprocess.run(["ssh", "dellg15", cmd], capture_output=True,
                       text=True, encoding="cp1251", errors="replace",
                       timeout=timeout)
    out = (r.stdout or "") + (r.stderr or "")
    print(out)
    return out


def main():
    import os
    os.makedirs(STAGE, exist_ok=True)
    for name, body in (("optprofile_setup.py", REMOTE),
                       ("optprofile_smoke.py", SMOKE)):
        open(os.path.join(STAGE, name), "w", newline="\n",
             encoding="utf-8").write(body)
        subprocess.run(["scp", "-q", os.path.join(STAGE, name),
                        f"dellg15:E:/fbdata/{name}"], check=True)
    out = ssh("python E:/fbdata/optprofile_setup.py")
    assert "SETUP DONE" in out, "setup failed"
    out = ssh("python E:/fbdata/optprofile_smoke.py")
    assert "SMOKE OK" in out, "smoke failed"
    print("DEPLOY OK: FB_optprofile on 3180")


if __name__ == "__main__":
    main()
