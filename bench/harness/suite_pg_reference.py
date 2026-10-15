"""PG-эталон (S6) для сюит после JOB: job-light / scale / synthetic /
job-complex — обобщение job_pg_reference.py.

Отличия от job_pg_reference.py:
  - источник SQL: портированные файлы bench/queries/<suite>/<qid>.sql
    (job-light/scale/synthetic — порт тождественный исходному workload'у
    за исключением снятого ';'), а для job-complex — исходник из
    third_party/JOB-Complex/JOB-Complex.sql (PG-эталон обязан считать
    ПОЛНЫЕ MIN, до усечения);
  - каталоги и bat-файл на dellg15 — с суффиксом сюиты, чтобы окна S6
    разных сюит не затирали друг друга.

Формат результатов тот же: results/<suite>_pg_reference/<qid>.json
  {rows, seconds, checksum, plan, error}

Запуск: python bench/harness/suite_pg_reference.py <gen|run|parse> <suite> [<suite>...]
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GEN = os.path.join(ROOT, "third_party", "imdb-port")
REMOTE_BASE = "E:/pgdumps"
TIMEOUT_S = int(float(os.environ.get("BENCH_PG_TIMEOUT", "300")))
PG_DB = os.environ.get("BENCH_PG_DB", "imdb")
# пароль эталонного PG — только через окружение, в репозитории не хранится
PG_PWD = os.environ.get("BENCH_PG_PWD", "")


def source_sql(suite: str, qid: str) -> str:
    """Исходный PG-диалект запроса qid (БЕЗ портирования)."""
    if suite == "job-complex":
        # исходник: третий файл по порядку 01..30
        if not hasattr(source_sql, "_jc_cache"):
            txt = open(os.path.join(ROOT, "third_party", "JOB-Complex",
                                    "JOB-Complex.sql"), encoding="utf-8").read()
            source_sql._jc_cache = [q.strip() for q in txt.split(";")
                                    if q.strip()]
        idx = int(qid.rsplit("_", 1)[1])
        return source_sql._jc_cache[idx - 1]
    if suite == "tpch":
        # исходник: qgen -s 1 -r 42 -> third_party/tpch-dbgen/queries_out/N.sql
        # (тот же источник, что port_tpch.py; усечение до первого ';' —
        # хвост qgen "where rownum <= n;" снимается). Точность поля интервала
        # "day (3)" PG не принимает (qgen-диалект) — снимаем.
        qnum = int(qid.rsplit("_", 1)[1])
        raw = open(os.path.join(ROOT, "third_party", "tpch-dbgen",
                                "queries_out", f"{qnum}.sql"),
                   encoding="utf-8").read()
        raw = re.sub(r"\b(day|year|month)\s*\(\d+\)", r"\1", raw)
        return raw.split(";", 1)[0]
    if suite in ("jcch-norm", "jcch-skew"):
        # исходник: JCC-H qgen (normal / -k skewed), seed 42 — тот же
        # источник, что port_jcch.py; правила усечения как у tpch.
        qnum = int(qid.rsplit("_", 1)[1])
        sub = "norm" if suite == "jcch-norm" else "skew"
        raw = open(os.path.join(ROOT, "third_party", "dbgen.JCC-H",
                                f"queries_out_{sub}", f"{sub}_{qnum}.sql"),
                   encoding="utf-8").read()
        # seed-комментарий qgen внутрь \copy попасть не может
        # (p-- съедает хвост строки); срезаем строки-комментарии
        raw = re.sub(r"^--.*$", "", raw, flags=re.M)
        raw = re.sub(r"\b(day|year|month)\s*\(\d+\)", r"\1", raw)
        return raw.split(";", 1)[0]
    if suite.startswith("dsb-"):
        # исходник: dsqgen PG-диалект (port_dsb.py перезаписывает рабочие
        # файлы, PG-оригиналы сохранены в orig/ до порта). 039 двухблочный:
        # файлы dsb_039_01_1/_2 — N-й statement оригинала dsb_039_01
        # (тот же сплит, что port_dsb.dsb_statements).
        odir = os.path.join(ROOT, "bench", "queries", suite, "orig")
        base = f"{qid}.sql"
        m = None
        if not os.path.exists(os.path.join(odir, base)):
            m = re.search(r"_(\d+)$", qid)
            if not m:
                raise FileNotFoundError(base)
            base = f"{qid[:m.start()]}.sql"
        raw = open(os.path.join(odir, base), encoding="utf-8").read()
        if m:
            parts = [p.strip().rstrip(";").strip()
                     for p in raw.split(";")]
            parts = [p for p in parts if p]
            return parts[int(m.group(1)) - 1]
        return raw.strip().rstrip(";").strip()
    return open(os.path.join(ROOT, "bench", "queries", suite,
                             f"{qid}.sql"), encoding="utf-8").read()


def qids(suite: str) -> list[str]:
    if suite == "job-complex":
        return [f"job_complex_{i:02d}" for i in range(1, 31)]
    qdir = os.path.join(ROOT, "bench", "queries", suite)
    return sorted(f[:-4] for f in os.listdir(qdir) if f.endswith(".sql"))


def outdir(suite: str) -> str:
    return os.path.join(ROOT, "results", f"{suite}_pg_reference")


def rows_checksum(rows: list[list]) -> str:
    canon = "\x1e".join(repr(tuple(r)) for r in sorted(rows, key=repr))
    return "sha1:" + hashlib.sha1(canon.encode("utf-8")).hexdigest()


def gen(suites: list[str]):
    for suite in suites:
        gdir = os.path.join(GEN, f"{suite}ref")
        os.makedirs(gdir, exist_ok=True)
        for qid in qids(suite):
            sql = source_sql(suite, qid).strip().rstrip(";").strip()
            one_line = " ".join(sql.split())
            pre = post = ""
            if suite in ("tpch", "jcch-norm", "jcch-skew") \
                    and qid.endswith("_15"):
                # qgen Q15: create view + select + drop view — эталон и план
                # полным циклом; \copy оборачивает только итоговый select
                if suite == "tpch":
                    raw = open(os.path.join(ROOT, "third_party",
                                            "tpch-dbgen", "queries_out",
                                            "15.sql"),
                               encoding="utf-8").read()
                else:
                    sub = "norm" if suite == "jcch-norm" else "skew"
                    raw = open(os.path.join(ROOT, "third_party",
                                            "dbgen.JCC-H",
                                            f"queries_out_{sub}",
                                            f"{sub}_15.sql"),
                               encoding="utf-8").read()
                raw = re.sub(r"^--.*$", "", raw, flags=re.M)
                raw = raw.split("where rownum", 1)[0]
                parts = [p.strip() for p in raw.split(";") if p.strip()]
                pre = parts[0] + ";\n"
                post = (parts[2] if len(parts) > 2
                        else "drop view revenue0") + ";\n"
                one_line = " ".join(parts[1].split())
            with open(os.path.join(gdir, f"q_{qid}.sql"), "w",
                      encoding="utf-8", newline="\n") as f:
                f.write(f"SET statement_timeout = '{TIMEOUT_S}s';\n"
                        f"\\timing on\n{pre}"
                        f"\\copy ({one_line}) TO STDOUT WITH (FORMAT csv)\n"
                        f"{post}")
            with open(os.path.join(gdir, f"pe_{qid}.sql"), "w",
                      encoding="utf-8", newline="\n") as f:
                f.write(f"SET statement_timeout = '{TIMEOUT_S}s';\n"
                        f"\\timing on\n{pre}"
                        f"EXPLAIN (ANALYZE, FORMAT JSON, TIMING OFF) "
                        f"{one_line};\n{post}")
        rdir = (REMOTE_BASE + "/" + f"{suite}ref").replace("/", "\\")
        with open(os.path.join(GEN, f"{suite}ref_run.cmd"), "w",
                  encoding="utf-8", newline="\r\n") as f:
            f.write(f"""@echo off
set "PGPASSWORD={PG_PWD}"
set "LC_MESSAGES=C"
if not exist {rdir}\\out mkdir {rdir}\\out
del /q {rdir}\\out\\* 2>nul
for %%f in ({rdir}\\q_*.sql) do C:\\pgsql\\bin\\psql.exe -U postgres -d {PG_DB} -A -t -q -f "%%f" > "{rdir}\\out\\%%~nf.csv" 2> "{rdir}\\out\\%%~nf.err"
for %%f in ({rdir}\\pe_*.sql) do C:\\pgsql\\bin\\psql.exe -U postgres -d {PG_DB} -A -t -q -f "%%f" > "{rdir}\\out\\%%~nf.json" 2> "{rdir}\\out\\%%~nf.err"
echo PGREF_DONE_{suite.upper()}
""")
        print(f"generated {len(qids(suite))} x (q_, pe_) -> {gdir}")


def run_remote(suites: list[str]):
    for suite in suites:
        gdir = os.path.join(GEN, f"{suite}ref")
        files = [os.path.join(gdir, f) for f in os.listdir(gdir)]
        subprocess.run(["scp", "-q", *files,
                        f"dellg15:{REMOTE_BASE}/{suite}ref/"], check=True)
        subprocess.run(["scp", "-q",
                        os.path.join(GEN, f"{suite}ref_run.cmd"),
                        "dellg15:E:/pgdumps/"], check=True)
        r = subprocess.run(
            ["ssh", "dellg15", f"E:\\pgdumps\\{suite}ref_run.cmd"],
            capture_output=True, text=True)
        print(suite, r.stdout[-500:], r.stderr[-500:])


def parse(suites: list[str]):
    for suite in suites:
        odir = outdir(suite)
        os.makedirs(odir, exist_ok=True)
        out = os.path.join(GEN, f"{suite}ref", "out")
        if not os.path.isdir(out):
            print(f"{suite}: нет {out} — сначала run")
            continue
        n_ok = n_plan = 0
        for qid in qids(suite):
            entry = {"rows": None, "seconds": None, "checksum": None,
                     "plan": None, "error": None}
            cf = os.path.join(out, f"q_{qid}.csv")
            ef = os.path.join(out, f"q_{qid}.err")
            if os.path.exists(cf):
                raw = open(cf, encoding="utf-8", errors="replace").read()
                time_re = re.compile(r"^Time: ([\d.,]+) ms")
                time_s = None
                keep = []
                for ln in raw.splitlines():
                    m = time_re.match(ln)
                    if m:
                        time_s = float(m.group(1).replace(",", ".")) / 1000.0
                    else:
                        keep.append(ln)
                entry["seconds"] = time_s
                data = "\n".join(keep)
                if keep:
                    rows = list(csv.reader(io.StringIO(data)))
                    if not rows and "".join(keep).strip() == "":
                        rows = [[]]
                    entry["rows"] = rows
                    entry["checksum"] = rows_checksum(rows)
                elif time_s is not None and not entry["error"]:
                    # \copy вывел 0 строк, но Time есть и ошибки нет —
                    # легитимный пустой результат (0 групп GROUP BY)
                    entry["rows"] = []
                    entry["checksum"] = rows_checksum([])
            if os.path.exists(ef):
                for ln in open(ef, encoding="utf-8", errors="replace"):
                    if ln.startswith("Time:"):
                        entry["seconds"] = float(
                            ln.split()[1].replace(",", ".")) / 1000.0
                    if "ERROR" in ln or "canceling statement" in ln:
                        entry["error"] = ln.strip()[:300]
            if entry["error"]:
                # таймаут/ошибка: пустой \copy — НЕ валидный пустой результат
                entry["rows"] = None
                entry["checksum"] = None
            pf = os.path.join(out, f"pe_{qid}.json")
            if os.path.exists(pf):
                txt = open(pf, encoding="utf-8",
                           errors="replace").read()
                # план = первый [...] в выводе psql; перед ним могут быть
                # статусы/тайминги других стэйтментов (tpch_15: view+select)
                li = txt.find("[")
                if li != -1:
                    try:
                        plan, _ = json.JSONDecoder().raw_decode(txt[li:])
                        entry["plan"] = plan
                        try:
                            entry["pg_execution_ms"] = \
                                plan[0]["Execution Time"]
                        except (KeyError, IndexError, TypeError):
                            pass
                    except json.JSONDecodeError as e:
                        entry["error"] = f"plan parse: {e}"
            with open(os.path.join(odir, f"{qid}.json"), "w",
                      encoding="utf-8") as f:
                json.dump(entry, f, ensure_ascii=False, indent=1)
            n_ok += 1 if entry["checksum"] else 0
            n_plan += 1 if entry["plan"] else 0
        print(f"{suite}: parsed {n_ok} results, {n_plan} plans -> {odir}")


if __name__ == "__main__":
    cmd, suites = sys.argv[1], sys.argv[2:]
    {"gen": gen, "run": run_remote, "parse": parse}[cmd](suites)
