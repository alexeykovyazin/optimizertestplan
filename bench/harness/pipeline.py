"""Ключ эталона, каталоги прогонов, сохранение результатов (разделы 4.2, 4.3).

Ключ эталона: (сборка, SHA-256 файла БД, ODS, хеш конфигурации, index_config).
Эталон с другим ключом не используется для сравнения счётчиков.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))
import fbenv  # noqa: E402

RESULTS_DIR = os.path.join(ROOT, "results")
CONFIG_DIR = os.path.join(ROOT, "bench", "config")
GOLD_DIR = os.path.join(ROOT, "db", "golden")

BUILD_ID = os.environ.get("BENCH_BUILD_ID", "fb5.0.5-hqbird-base")


def config_hash() -> str:
    h = hashlib.sha256()
    for name in ("firebird.conf.snapshot", "databases.conf.snapshot",
                 "optimizer_matrix.yaml"):
        with open(os.path.join(CONFIG_DIR, name), "rb") as f:
            h.update(f.read())
    return h.hexdigest()


def golden_sha(index_config: str) -> str:
    path = os.path.join(GOLD_DIR, f"stats_{index_config}.fdb")
    return fbenv.sha256_file(path)


def ods_of(db_path: str) -> str:
    conn = fbenv.connect_fb(db_path)
    try:
        info = conn.info
        return f"ODS{info.ods_version}.{info.ods_minor_version}"
    finally:
        conn.close()


def baseline_key(index_config: str, db_sha: str | None = None) -> dict:
    return {
        "build_id": BUILD_ID,
        "db_sha256": db_sha or golden_sha(index_config),
        "ods": ods_of(os.path.join(GOLD_DIR, f"stats_{index_config}.fdb")),
        "config_hash": config_hash(),
        "index_config": index_config,
    }


def key_id(key: dict) -> str:
    return hashlib.sha1(json.dumps(key, sort_keys=True).encode()).hexdigest()[:12]


def new_run_dir(label: str) -> str:
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    d = os.path.join(RESULTS_DIR, "runs", f"{ts}_{label}")
    os.makedirs(d, exist_ok=True)
    return d


def save_parquet(rows: list[dict], path: str):
    import pyarrow as pa
    import pyarrow.parquet as pq
    if not rows:
        raise ValueError("no rows")
    cols = {k: [r.get(k) for r in rows] for k in rows[0].keys()}
    tbl = pa.table({k: pa.array(v) for k, v in cols.items()})
    pq.write_table(tbl, path)


def load_parquet(path: str) -> list[dict]:
    import pyarrow.parquet as pq
    t = pq.read_table(path)
    return t.to_pylist()


def make_work_copy(index_config: str, run_dir: str) -> str:
    """Побайтовая копия золотого файла для прогона (не restore)."""
    src = os.path.join(GOLD_DIR, f"stats_{index_config}.fdb")
    dst = os.path.join(run_dir, f"stats_{index_config}.fdb")
    got = fbenv.byte_copy(src, dst)
    exp = golden_sha(index_config)
    assert got == exp, f"copy hash mismatch: {got} != {exp}"
    return dst
