
import os, sys, time, socket, subprocess
sys.path.insert(0, r"E:\bench\harness")
os.environ["FB_CLIENT_DIR"] = r"C:\HQbird\Firebird50"
import fbenv
fbenv.HOST_PORT = "localhost:3180"
fbenv.ensure_client()
from firebird.driver import connect

# убедимся, что профиль подключён
conf = open(r"E:\fb50-optprofile\databases.conf", encoding="utf-8").read()
assert "stats.profile" in conf, "stats.profile NOT attached!"

def up():
    try:
        with socket.create_connection(("127.0.0.1", 3180), 2):
            return True
    except OSError:
        return False

QDIR = r"E:\bench\queries\stats-ceb-single"
ids = sorted(f[:-4] for f in os.listdir(QDIR) if f.endswith(".sql"))[:150]
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
                subprocess.run("net stop FB_optprofile >nul 2>&1", shell=True)
                subprocess.run(
                    "del /q E:\fbdata\optprofile_work\*.lck >nul 2>&1",
                    shell=True)
                subprocess.run("net start FB_optprofile", shell=True)
                for i in range(30):
                    time.sleep(1)
                    if up(): break
            elif attempt == 2:
                crashes += 1
print(f"WITH-NEW-PROFILE PROBE: 150 queries, ok={ok}, crashes={crashes}",
      flush=True)
os._exit(0)
