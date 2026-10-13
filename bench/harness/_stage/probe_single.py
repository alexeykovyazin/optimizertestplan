
import os, subprocess, sys, time, socket
sys.path.insert(0, r"E:\bench\harness")
os.environ["FB_CLIENT_DIR"] = r"C:\HQbird\Firebird50"
import fbenv
fbenv.HOST_PORT = "localhost:3180"
fbenv.ensure_client()
from firebird.driver import connect

QDIR = r"E:\bench\queries\stats-ceb-single"
ids = sorted(f[:-4] for f in os.listdir(QDIR) if f.endswith(".sql"))

def server_up():
    try:
        with socket.create_connection(("127.0.0.1", 3180), 2):
            return True
    except OSError:
        return False

def restart():
    subprocess.run("net stop FB_optprofile >nul 2>&1", shell=True)
    subprocess.run("del /q E:\fbdata\optprofile_work\*.lck >nul 2>&1",
                   shell=True)
    subprocess.run("net start FB_optprofile", shell=True)
    for i in range(45):
        time.sleep(1 + i // 10)
        if server_up():
            return True
    return False

crashers, ok, restarts = [], 0, 0
for i, qid in enumerate(ids, 1):
    sql = open(os.path.join(QDIR, qid + ".sql"), encoding="utf-8").read()
    for attempt in range(3):
        try:
            conn = connect(fbenv.dsn("stats_opt"), user="SYSDBA",
                           password="masterkey", charset="UTF8")
            cur = conn.cursor()
            ps = cur.prepare(sql)
            cur.close(); conn.close()
            ok += 1
            break
        except Exception as e:
            txt = f"{type(e).__name__}: {e}"[:110]
            if not server_up() or attempt == 2:
                crashers.append((qid, txt))
                if not server_up():
                    restarts += 1
                    if not restart():
                        print("SERVER WON'T COME BACK", flush=True)
                        print("CRASHERS:", crashers, flush=True)
                        os._exit(2)
                break
    if i % 50 == 0:
        print(f"{i}/{len(ids)} ok={ok} restarts={restarts}", flush=True)
print(f"PROBE DONE ok={ok} restarts={restarts} suspects={crashers}",
      flush=True)
os._exit(0)
