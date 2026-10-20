r"""Включение флагов оптимизатора в E:\fb50-impropt\firebird.conf + рестарт.

PredicateCorrelation = true, ExtendedStatistics = true,
SubQueryConversion = true (остальные параметры конфига не трогаем).
Активные (не закомментированные) строки этих ключей удаляются,
в конец дописываются три строки с = true, затем sc stop/start FB_impropt.
"""
import re
import subprocess
import time

CONF = r"E:\fb50-impropt\firebird.conf"
SVC = "FB_impropt"
FLAGS = ["PredicateCorrelation", "ExtendedStatistics", "SubQueryConversion"]


def run(cmd, timeout=120):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       errors="replace", timeout=timeout)
    return ((r.stdout or "") + (r.stderr or "")).strip()


lines = open(CONF, encoding="utf-8", errors="replace").read().splitlines()
kept = [ln for ln in lines
        if not any(re.match(rf"^\s*{k}\s*=", ln) for k in FLAGS)]
kept += [f"{k} = true" for k in FLAGS]
open(CONF, "w", newline="\r\n", encoding="utf-8").write("\n".join(kept) + "\n")
print("conf updated,", len(kept), "lines", flush=True)
for k in FLAGS:
    hit = [ln.strip() for ln in kept if ln.startswith(k)]
    print("  ", hit, flush=True)

print(run(f"sc stop {SVC}"), flush=True)
for _ in range(30):
    time.sleep(2)
    if "STOPPED" in run(f"sc query {SVC}"):
        break
print(run(f"sc start {SVC}"), flush=True)
for _ in range(30):
    time.sleep(2)
    q = run(f"sc query {SVC}")
    if "RUNNING" in q:
        break
print("state:", q.replace("\n", " | "), flush=True)
assert "RUNNING" in q, "service did not reach RUNNING"
time.sleep(3)
print("FLAGS RESTART DONE", flush=True)
