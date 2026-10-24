r"""Супервизор прогона HASH-корпуса: крутит hash_imdb_ab.py до полного
покрытия корпуса (резюм по CSV), переживая молчаливые AV драйвера.

Запуск: python hash_supervisor.py [--out CSV] [--expected JSON]
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import time

ap = argparse.ArgumentParser()
ap.add_argument("--out", default=r"E:\results\hash_imdb_ab.csv",
                help="CSV раннера (резюм и подсчёт готовности)")
ap.add_argument("--expected", default=r"E:\fbdata\expected_imdb.json")
ap.add_argument("--max-iters", type=int, default=40)
args = ap.parse_args()

n_expected = len(json.load(open(args.expected, encoding="utf-8")))


def done_count() -> int:
    if not os.path.isfile(args.out):
        return 0
    with open(args.out, encoding="utf-8") as f:
        return len({r["qid"] for r in csv.DictReader(f)
                    if r["kind"] == "measured"})


for i in range(args.max_iters):
    done = done_count()
    if done >= n_expected:
        break
    print(f"@@@ supervisor iter {i}: done {done}/{n_expected}, "
          f"{time.strftime('%H:%M:%S')}", flush=True)
    env = dict(os.environ, FB_CLIENT_DIR=r"C:\HQbird\Firebird50")
    subprocess.run([sys.executable, r"E:\fbdata\hash_imdb_ab.py",
                    "--out", args.out, "--expected", args.expected],
                   env=env)
    time.sleep(10)

print(f"SUPERVISOR DONE: {done_count()}/{n_expected}", flush=True)
