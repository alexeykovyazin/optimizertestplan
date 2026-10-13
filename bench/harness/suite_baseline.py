"""S8-бейслайн новых сюит (job-light/scale/synthetic/job-complex) на dellg15:3055.

Полный прогон счётчиков+времени по портфелю porting-plan-remaining-suites.md,
протокол как у базовой матрицы, но repeats=2 (прогрев + 1 замер; тяжёлые
>15 c — единственный замер) — сокращение протокола по решению пользователя
2026-10-10 (было repeats=4).

Ключ эталона: (сборка FB, sha golden-БД, порт, OptimizeForFirstRows,
index_config) — самодостаточный хеш, каталог results/baselines/<key_id>/ с
<suite>.collected.parquet, <suite>.executed.parquet и REPORT.md.

Запуск (клиент — LAN-машина):
  python bench/harness/suite_baseline.py --suites job-light scale \
      --golden E:/fbdata/golden/imdb_fb5.fdb --work-dir E:/fbdata/work
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
import pipeline  # noqa: E402

REMOTE_HOST = os.environ.get("DELLG15_SSH", "dellg15")


def remote_sha(path: str) -> str:
    r = subprocess.run(
        ["ssh", REMOTE_HOST,
         f"certutil -hashfile {path.replace('/', chr(92))} SHA256"],
        capture_output=True, text=True)
    for ln in r.stdout.splitlines():
        ln = ln.strip()
        if len(ln) == 64 and all(c in "0123456789abcdef" for c in ln.lower()):
            return ln.lower()
    raise RuntimeError(f"нет sha256 для {path}: {r.stdout[:200]}")


def make_work_copy_remote(golden: str, work: str) -> str:
    """Копия золотого файла НА dellg15 (shutil, не copy /y — ловушка §5)."""
    script = (f"import hashlib,shutil,sys;"
              f"shutil.copyfile(r'{golden}', r'{work}');"
              f"h=hashlib.sha256(open(r'{work}','rb').read()).hexdigest();"
              f"print(h)")
    r = subprocess.run(["ssh", REMOTE_HOST,
                        f"python -c \"{script}\""],
                       capture_output=True, text=True)
    sha = r.stdout.strip()
    if len(sha) != 64:
        raise RuntimeError(f"копия/хеш не удалась: {r.stdout[:200]} "
                           f"{r.stderr[:200]}")
    return sha


def fb_version(host_port: str, db_path: str) -> str:
    import fbenv
    fbenv.HOST_PORT = host_port
    conn = fbenv.connect_fb(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT RDB$GET_CONTEXT('SYSTEM','ENGINE_VERSION')")
        v = cur.fetchone()[0].strip()
        cur.close()
        return v
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suites", nargs="+", required=True)
    ap.add_argument("--host", default="dellg15.local:3055")
    ap.add_argument("--golden", default="E:/fbdata/golden/imdb_fb5.fdb")
    ap.add_argument("--work-dir", default="E:/fbdata/work")
    ap.add_argument("--work-name", default="imdb_work_suite.fdb")
    ap.add_argument("--timeout-s", type=float, default=300.0)
    ap.add_argument("--skip-copy", action="store_true",
                    help="рабочая копия уже создана прошлым запуском")
    ap.add_argument("--only-collect", action="store_true",
                    help="только компиляция (планы) — для synthetic, S6-компиляция")
    a = ap.parse_args()

    os.environ.setdefault("FB_HOSTPORT", a.host)
    import fbenv
    fbenv.HOST_PORT = a.host
    from collector import collect_suite
    from runner import run_suite
    from phase0_make_baseline import flatten_exec

    work = a.work_dir.rstrip("/") + "/" + a.work_name
    if not a.skip_copy:
        sha = make_work_copy_remote(a.golden, work)
        print(f"work copy: sha256={sha[:16]}...", flush=True)
    else:
        sha = remote_sha(work)
        print(f"work copy exists: sha256={sha[:16]}...", flush=True)

    ver = fb_version(a.host, work)
    key = {"build": ver, "db_sha256": sha, "host_port": a.host,
           "index_config": "pk",
           "repeats_protocol": "warmup+1 (repeats=2, adaptive >15c)"}
    import hashlib as _h
    key_id = _h.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:12]
    bdir = os.path.join(pipeline.RESULTS_DIR, "baselines", key_id)
    os.makedirs(bdir, exist_ok=True)

    for suite in a.suites:
        t0 = time.perf_counter()
        collected = collect_suite(work, suite)
        pipeline.save_parquet(collected,
                              os.path.join(bdir, f"{suite}.collected.parquet"))
        print(f"[{suite}] collect: {len(collected)} queries "
              f"({time.perf_counter() - t0:.0f}s)", flush=True)
        if a.only_collect:
            continue
        t0 = time.perf_counter()
        rows = run_suite(work, suite, warmup=True, repeats=2,
                         per_query_timeout_s=a.timeout_s, progress=True)
        flat = flatten_exec(rows, {r["query_id"]: r for r in collected})
        pipeline.save_parquet(flat,
                              os.path.join(bdir, f"{suite}.executed.parquet"))
        ok = sum(1 for r in flat if r.get("median_ms"))
        to = sum(1 for r in flat if r.get("timed_out"))
        err = sum(1 for r in flat if r.get("error"))
        heavy = sum(1 for r in flat if r.get("median_ms") and
                    r["median_ms"] > 15000)
        print(f"[{suite}] executed: {len(flat)} (ok={ok} timeout={to} "
              f"error={err} heavy={heavy}) in {time.perf_counter() - t0:.0f}s",
              flush=True)

    if not a.only_collect:
        meta = {"kind": "suite_baseline", "key": key, "key_id": key_id,
                "suites": a.suites, "golden": a.golden,
                "created": time.strftime("%Y-%m-%d %H:%M")}
        with open(os.path.join(bdir, "baseline_meta.json"), "w",
                  encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        print("baseline key_id:", key_id, "->", bdir)


if __name__ == "__main__":
    main()
