"""Генерация ворклоада DSB (52 PG-шаблона x 2 гауссовых дистрибуции) — §3.2.4.

Источник S0: microsoft/dsb (MIT; Ding et al., PVLDB 14(13) 2021) —
модифицированный тулсет TPC-DS v2.11.0rc2. Собран msbuild (dbgen2.sln,
Release|Win32, toolset v142): dsdgen/dsqgen/distcomp в third_party/dsb/
code/tools. Требование DSB: dsqgen запускать из каталога бинарников
(tpcds.idx и *.dst рядом).

Данные: dsdgen /scale 1 (SF1, correlation между таблицами — порядок
генерации фиксирован внутри dsdgen) -> bench/datasets/dsb/sf1_csv
(25 таблиц, счётчики TPC-DS SF1: store_sales 2 880 404, inventory 11 745 000).

Ловушки Windows-сборки:
  - Git Bash превращает /OPTION в путь — запускать через cmd //c c < NUL
    либо MSYS_NO_PATHCONV=1;
  - distcomp ОБЯЗАН отработать до dsqgen: он запекает гауссовы веса в
    tpcds.idx; на недопечённом idx dsqgen+PARAM_DIST normal виснет
    (IntegrateDist крутится по нулевым весам).

Дистрибуции (по образцу scripts/workload_config.json из репо):
  s2: sigma=2, center=0, rngseed=997; s1: sigma=1, center=0, rngseed=997.
Инстансов на шаблон: 5 -> 52 x 5 x 2 = 520 запросов
(52 шаблона = 15 agg + 20 multi_block + 17 spj; query100-102 — новые DSB).

Запуск: python bench/datasets/dsb/gen_workload.py [--instances 5]
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
TOOLS = os.path.join(ROOT, "third_party", "dsb", "code", "tools")
TPL_ROOT = os.path.join(ROOT, "third_party", "dsb", "query_templates_pg")
OUT_ROOT = os.path.join(ROOT, "bench", "queries")
MANIFEST_DIR = os.path.join(ROOT, "bench", "manifest")

DISTS = [
    {"id": "s2", "param_sigma": 2, "param_center": 0, "rngseed": 997},
    {"id": "s1", "param_sigma": 1, "param_center": 0, "rngseed": 997},
]


def run_tool(args: list[str]) -> int:
    cmd = ["cmd", "/c", os.path.basename(args[0]), *args[1:], "<", "NUL"]
    r = subprocess.run(cmd, cwd=TOOLS, capture_output=True, text=True,
                       errors="replace", shell=True,
                       env={**os.environ, "MSYS_NO_PATHCONV": "1"})
    return r.returncode


def templates() -> list[tuple[str, str]]:
    out = []
    for group in ("agg_queries", "multi_block_queries", "spj_queries"):
        d = os.path.join(TPL_ROOT, group)
        for f in sorted(os.listdir(d)):
            if f.startswith("query") and f.endswith(".tpl"):
                out.append((group, f))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instances", type=int, default=5)
    a = ap.parse_args()

    groups = templates()
    print(f"{len(groups)} templates x {len(DISTS)} dists "
          f"x {a.instances} instances")

    tmp_dir = os.path.join(TOOLS, "dsbq_tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    for dist in DISTS:
        sid = f"dsb-{dist['id']}"
        qdir = os.path.join(OUT_ROOT, sid)
        os.makedirs(qdir, exist_ok=True)
        # 1) запечь гауссову дистрибуцию (ОБЯЗАТЕЛЬНО до dsqgen)
        rc = run_tool([os.path.join(TOOLS, "distcomp.exe"),
                       "/i", "tpcds.dst", "/o", "tpcds.idx",
                       "/param_dist", "normal",
                       "/param_sigma", str(dist["param_sigma"]),
                       "/param_center", str(dist["param_center"]),
                       "/rngseed", str(dist["rngseed"])])
        if rc != 0:
            raise SystemExit(f"distcomp rc={rc}")
        # 2) шаблоны; dsqgen (Win32) иногда падает heap corruption
        # (0xC0000374) недетерминированно — ретраи, не преодолимые — в skip
        skipped = []
        for group, tpl in groups:
            gdir = os.path.join(TPL_ROOT, group)
            ok = False
            for attempt in range(4):
                for f in os.listdir(tmp_dir):
                    os.remove(os.path.join(tmp_dir, f))
                rc = run_tool([os.path.join(TOOLS, "dsqgen.exe"),
                               "/TEMPLATE", tpl,
                               "/DIALECT", "postgres",
                               "/DIRECTORY", gdir,
                               "/OUTPUT_DIR", tmp_dir,
                               "/STREAMS", str(a.instances),
                               "/PARAM_DIST", "normal",
                               "/RNGSEED", str(dist["rngseed"])])
                qname = tpl[:-4]
                outs = [os.path.join(tmp_dir, f"query_{i}.sql")
                        for i in range(a.instances)]
                ok = (rc == 0 and all(os.path.isfile(p) and
                                      os.path.getsize(p) > 200 and
                                      "select" in open(p, encoding="utf-8",
                                                       errors="replace")
                                      .read().lower()
                                      for p in outs))
                if ok:
                    for i in range(a.instances):
                        shutil.copyfile(outs[i],
                                        os.path.join(
                                            qdir, f"dsb_{qname[5:]}_{i + 1:02d}.sql"))
                    ok = True
                    break
            if not ok:
                skipped.append(f"{group}/{tpl}")
                print(f"  {sid} {qname}: SKIPPED (rc={rc})", flush=True)
            else:
                print(f"  {sid} {qname}: {a.instances}", flush=True)
        if skipped:
            print(f"{sid}: SKIPPED TEMPLATES: {skipped}", flush=True)
    print("DSB_WORKLOAD_DONE")


if __name__ == "__main__":
    main()
