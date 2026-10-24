r"""Заполнение тестовой БД + расширенная статистика (FULL) на FB_impropt 3056.

Шаги: свежая копия голдена IMDb -> gfix -mode read_write ->
ALTER DATABASE ADD EXTENDED STATISTICS ->
ALTER DATABASE REFRESH STATISTICS FULL -> отключение.
Хранилище STAT$ в свежей копии отсутствует (старое осталось только в
предыдущей рабочей копии, которую перезаписываем).
"""
import hashlib
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, r"E:\bench\harness")
import fbenv

fbenv.HOST_PORT = "localhost:3056"
fbenv.ensure_client()
from firebird.driver import connect

GOLDEN = r"E:\db\imdb\imdb_fb5.fdb"
WORK = r"E:\fbdata\impropt_work\imdb_fb5.fdb"


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb", buffering=4 * 1024 * 1024) as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


t0 = time.time()
if os.path.exists(WORK):
    os.remove(WORK)
shutil.copyfile(GOLDEN, WORK)
gs, ws = os.path.getsize(GOLDEN), os.path.getsize(WORK)
assert gs == ws, f"size mismatch {gs} != {ws}"
gsha, wsha = sha256(GOLDEN), sha256(WORK)
assert gsha == wsha, "sha mismatch"
print(f"copy ok {gs / 2**30:.1f} GiB sha={wsha[:12]} "
      f"({time.time() - t0:.0f}s)", flush=True)

gfix = None
for cand in (r"E:\fb50-impropt\gfix.exe", r"C:\HQbird\Firebird50\gfix.exe"):
    if os.path.exists(cand):
        gfix = cand
        break
r = subprocess.run(f'"{gfix}" -user SYSDBA -password masterkey '
                   f'-mode read_write "{WORK}"', shell=True,
                   capture_output=True, text=True, errors="replace")
print("gfix:", (r.stdout or "") + (r.stderr or ""), "rc=", r.returncode,
      flush=True)
assert r.returncode == 0, "gfix failed"

db = connect(fbenv.dsn(WORK), user="SYSDBA", password="masterkey",
             charset="UTF8")
cur = db.cursor()
cur.execute("select count(*) from RDB$RELATIONS "
            "where RDB$RELATION_NAME = 'STAT$SETTINGS'")
assert cur.fetchone()[0] == 0, "fresh copy already has STAT$ storage?!"
db.begin()
cur.execute("ALTER DATABASE ADD EXTENDED STATISTICS")
db.commit()
print("storage created", flush=True)

t0 = time.perf_counter()
db.begin()
cur.execute("ALTER DATABASE REFRESH STATISTICS FULL")
db.commit()
print(f"REFRESH FULL: {time.perf_counter() - t0:.0f}s", flush=True)
cur.execute("select count(*) from STAT$TABLES")
print("tables:", cur.fetchone()[0], flush=True)
cur.execute("select count(*) from STAT$COLUMNS")
print("columns:", cur.fetchone()[0], flush=True)
cur.close()
db.close()
print("FILL+STATS DONE", flush=True)
sys.stdout.flush()
os._exit(0)
