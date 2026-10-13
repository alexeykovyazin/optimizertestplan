"""Деплой собранного impr-opt Firebird на dellg15 (порт 3056, служба FB_impropt).

Локально: python bench/harness/deploy_impropt.py
Шаги: zip output_x64_release (без include/lib/doc) -> scp -> распаковка в
E:\fb50-impropt -> инициализация SECURITY5.FDB (CREATE USER SYSDBA) ->
firebird.conf (порт/режим) -> smoke (rows=, EXTENDED STATISTICS) ->
sc create/start FB_impropt.
"""
import os
import subprocess
import sys
import time
import zipfile

OUT = r"E:\Projects_Big\hqbird-impropt\output_x64_release"
ZIP = r"E:\Projects_Big\hqbird-impropt\fb50-impropt.zip"
LOCAL_STAGE = r"E:\Projects_Big\optimizertestplan\bench\harness\_stage"
SKIP_PREFIX = ("include/", "lib/", "doc/")


def ssh(cmd, timeout=900):
    r = subprocess.run(["ssh", "dellg15", cmd], capture_output=True,
                       text=True, timeout=timeout)
    out = (r.stdout or "") + (r.stderr or "")
    print(out)
    return out


REMOTE_SETUP = r'''
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
             "DefaultDbCachePages = 2048", "LockMemSize = 20M",
             "LockHashSlots = 40099", "TempCacheLimit = 256M",
             "InlineSortThreshold = 16384"):
    key = want.split(" = ")[0]
    if not any(re.match(rf"^\s*{key}\s*=", ln, re.I) for ln in lines):
        lines.append(want)
open(conf, "w", newline="\r\n", encoding="utf-8").write("\n".join(lines) + "\n")
print("conf ok, lines:", len(lines))
print("SETUP DONE")
'''


def main():
    assert os.path.exists(os.path.join(OUT, "firebird.exe")), \
        "no firebird.exe in build output"
    if not os.path.exists(ZIP) or os.path.getmtime(ZIP) < \
            os.path.getmtime(os.path.join(OUT, "firebird.exe")):
        if os.path.exists(ZIP):
            os.remove(ZIP)
        n = 0
        with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED,
                             compresslevel=6) as z:
            for root, _d, files in os.walk(OUT):
                for f in files:
                    if f.endswith(".pdb"):
                        continue
                    full = os.path.join(root, f)
                    rel = os.path.relpath(full, OUT).replace(os.sep, "/")
                    if rel.startswith(SKIP_PREFIX):
                        continue
                    z.write(full, rel)
                    n += 1
        print(f"zip: {n} files, {os.path.getsize(ZIP)/1e6:.0f} MB")
    else:
        print("zip fresh, reusing")

    os.makedirs(LOCAL_STAGE, exist_ok=True)
    setup_py = os.path.join(LOCAL_STAGE, "impropt_setup.py")
    open(setup_py, "w", newline="\n", encoding="utf-8").write(REMOTE_SETUP)
    subprocess.run(["scp", "-q", ZIP, "dellg15:E:/fbdata/"], check=True,
                   timeout=3600)
    print("zip copied")
    subprocess.run(["scp", "-q", setup_py, "dellg15:E:/fbdata/"], check=True)
    subprocess.run(["scp", "-q",
                    r"E:\Projects_Big\optimizertestplan\bench\harness"
                    r"\smoke_impropt.py", "dellg15:E:/fbdata/"], check=True)
    print("scripts staged")

    out = ssh("python E:/fbdata/impropt_setup.py")
    assert "SETUP DONE" in out, "setup failed"

    out = ssh("set FB_CLIENT_DIR=C:\\HQbird\\Firebird50&& "
              "python E:/fbdata/smoke_impropt.py --root E:\\fb50-impropt "
              "--port 3056")
    assert "SMOKE OK" in out, "smoke failed on dellg15"

    out = ssh('sc create FB_impropt binPath= "E:\\fb50-impropt\\firebird.exe" '
              'displayName= "Firebird impr-opt 3056" start= auto')
    out += ssh("sc start FB_impropt")
    time.sleep(5)
    out += ssh("sc query FB_impropt")
    assert "RUNNING" in out, "service not running"
    print("DEPLOY OK: service FB_impropt running on 3056")


if __name__ == "__main__":
    main()
