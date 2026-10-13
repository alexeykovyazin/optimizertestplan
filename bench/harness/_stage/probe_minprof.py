
import json, os, shutil, subprocess, sys, time, socket
sys.path.insert(0, r"E:\bench\harness")
os.environ["FB_CLIENT_DIR"] = r"C:\HQbird\Firebird50"

P = r"E:\fbdata\optprofile_work\stats.profile"
MINP = r"E:\fbdata\optprofile_work\stats_min.profile"
CONF = r"E:\fb50-optprofile\databases.conf"
BAK = CONF + ".minbak"

p = json.load(open(P, encoding="utf-8"))
for t in p["tables"].values():
    t.pop("columns", None)
    t.pop("indexes", None)
json.dump(p, open(MINP, "w", encoding="utf-8"), indent=1)

def sh(cmd):
    subprocess.run(cmd, shell=True, capture_output=True)

def up():
    try:
        with socket.create_connection(("127.0.0.1", 3180), 2):
            return True
    except OSError:
        return False

sh("net stop FB_optprofile >nul 2>&1")
shutil.copyfile(CONF, BAK)
txt = open(CONF, encoding="utf-8").read().replace("stats.profile", "stats_min.profile")
open(CONF, "w", newline="\r\n", encoding="utf-8").write(txt)
sh("net start FB_optprofile")
for i in range(30):
    time.sleep(1)
    if up(): break

import fbenv
fbenv.HOST_PORT = "localhost:3180"
fbenv.ensure_client()
from firebird.driver import connect
QDIR = r"E:\bench\queries\stats-ceb-single"
ids = sorted(f[:-4] for f in os.listdir(QDIR) if f.endswith(".sql"))[:100]
ok, crashes = 0, 0
for qid in ids:
    sql = open(os.path.join(QDIR, qid + ".sql"), encoding="utf-8").read()
    for attempt in range(3):
        try:
            conn = connect(fbenv.dsn("stats_opt"), user="SYSDBA",
                           password="masterkey", charset="UTF8")
            cur = conn.cursor(); ps = cur.prepare(sql)
            cur.close(); conn.close(); ok += 1; break
        except Exception:
            if not up():
                crashes += 1
                sh("net stop FB_optprofile >nul 2>&1")
                sh("del /q E:\fbdata\optprofile_work\*.lck >nul 2>&1")
                sh("net start FB_optprofile")
                for i in range(30):
                    time.sleep(1)
                    if up(): break
            elif attempt == 2:
                crashes += 1
print(f"MIN-PROFILE PROBE (cardinality only): 100 queries, "
      f"ok={ok}, crashes={crashes}", flush=True)
# вернуть обычный профиль
sh("net stop FB_optprofile >nul 2>&1")
shutil.copyfile(BAK, CONF)
os.remove(BAK)
sh("net start FB_optprofile")
for i in range(30):
    time.sleep(1)
    if up(): break
print("restored:", up(), flush=True)
os._exit(0)
