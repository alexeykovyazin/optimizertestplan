"""Построение Firebird-копии JCC-H SF1 (skewed) — §3.2.2, поверх build_tpch.

Схема идентична TPC-H (JCC-H — «100% compatible» форк dbgen 2.17.2);
переопределены только пути, счётчики (lineitem = ровно 6 000 000 — JCC-H
выравнивает, у TPC-H SF1 6 001 215) и источник в манифесте.
Скан максимальных длин строк skew-данных (2026-10-15): все <= канонических
DDL-лимитов (c_comment 116<=117, o_comment 78<=79, ps_comment 198<=199,
l_comment 43<=44) — BLOB-дивергенций нет.

Запуск: python bench/datasets/jcch/build_jcch.py --stage create|load|finalize
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "bench", "datasets", "tpch"))
sys.path.insert(0, os.path.join(ROOT, "bench", "harness"))

import build_tpch as base  # noqa: E402

base.TBL_DIR = os.path.join(HERE, "skew_csv")
base.FDB = os.path.join(ROOT, "db", "jcch", "jcch_sf1_fb5.fdb")
base.MANIFEST = os.path.join(ROOT, "db", "jcch", "jcch_build_manifest.json")
base.CANON_COUNTS = dict(base.CANON_COUNTS, lineitem=6_000_000)

# JCC-H skew: s_comment бывает ПУСТЫМ (20 строк) — в PG COPY text грузится
# как '' (без NULL-клаузы), здесь тоже '' (колонка NOT NULL, NULL не пройдёт)
_lit_orig = base._lit


def _lit_jcch(kind: str, v: str) -> str:
    if v == "":
        return "''"
    return _lit_orig(kind, v)


base._lit = _lit_jcch


def _patch_manifest_info():
    orig = base.stage_load

    def stage_load(threads: int = 3, only=None):
        orig(threads, only)
        m = base.json.load(open(base.MANIFEST, encoding="utf-8"))
        m["source"] = {
            "tool": "dbgen 2.17.2 JCC-H (ldbc/dbgen.JCC-H, JCCH_SKEW)",
            "sf": 1, "skew": True,
            "dir": "bench/datasets/jcch/skew_csv",
            "counts_canonical": base.CANON_COUNTS,
        }
        base.json.dump(m, open(base.MANIFEST, "w", encoding="utf-8"),
                       indent=1, ensure_ascii=False)
    return stage_load


base.stage_load = _patch_manifest_info()

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["create", "load", "finalize"])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--threads", type=int, default=3)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    {"create": lambda: base.stage_create(a.force),
     "load": lambda: base.stage_load(a.threads, a.only),
     "finalize": base.stage_finalize}[a.stage]()
