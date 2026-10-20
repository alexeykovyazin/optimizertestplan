r"""Супервизор прогона HASH-корпуса: крутит hash_imdb_ab.py до полного
покрытия корпуса (резюм по CSV), переживая молчаливые AV драйвера.
"""
import csv
import json
import os
import subprocess
import sys
import time

EXPECTED = r"E:\fbdata\expected_imdb.json"
CSVP = r"E:\results\hash_imdb_ab.csv"
MAX_ITERS = 40

n_expected = len(json.load(open(EXPECTED, encoding="utf-8")))


def done_count() -> int:
    if not os.path.isfile(CSVP):
        return 0
    with open(CSVP, encoding="utf-8") as f:
        return len({r["qid"] for r in csv.DictReader(f)
                    if r["kind"] == "measured"})


for i in range(MAX_ITERS):
    done = done_count()
    if done >= n_expected:
        break
    print(f"@@@ supervisor iter {i}: done {done}/{n_expected}, "
          f"{time.strftime('%H:%M:%S')}", flush=True)
    env = dict(os.environ, FB_CLIENT_DIR=r"C:\HQbird\Firebird50")
    subprocess.run([sys.executable, r"E:\fbdata\hash_imdb_ab.py"], env=env)
    time.sleep(10)

print(f"SUPERVISOR DONE: {done_count()}/{n_expected}", flush=True)
