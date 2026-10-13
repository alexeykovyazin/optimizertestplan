"""Эталонные результаты и планы JOB на PostgreSQL (dellg15) — раздел 4.5.

Для каждого из 113 запросов (оригиналы в PG-диалекте) генерируются:
  q_<qid>.sql  : SET statement_timeout + \\copy (query) TO STDOUT CSV
                 — точные строки результата (CSV-квотирование, NULL='')
  pe_<qid>.sql : EXPLAIN (ANALYZE, FORMAT JSON, TIMING OFF) — фактические
                 кардинальности каждого узла плана PG (истина для оценки
                 точности оценщика) + суммарное время.

Прогон на dellg15 через ssh (bat-цикл psql -f), результаты забираются scp
и складываются в results/job_pg_reference/<qid>.json:
  {rows: [[...]], seconds, checksum, plan (json|null), error|null}

Коллизация '|' внутри значений не страшна: парсим именно CSV.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "third_party", "JOB-queries")
GEN = os.path.join(ROOT, "third_party", "imdb-port")
OUTDIR = os.path.join(ROOT, "results", "job_pg_reference")
REMOTE = "E:/pgdumps/jobref"
TIMEOUT_S = 300
# пароль эталонного PG — только через окружение, в репозитории не хранится
PG_PWD = os.environ.get("BENCH_PG_PWD", "")


def qids() -> list[str]:
    import re
    return sorted(f[:-4] for f in os.listdir(SRC)
                  if re.fullmatch(r"\d+[a-z]\.sql", f))


def rows_checksum(rows: list[list]) -> str:
    canon = "\x1e".join(repr(tuple(r)) for r in sorted(rows, key=repr))
    return "sha1:" + hashlib.sha1(canon.encode("utf-8")).hexdigest()


def gen():
    os.makedirs(os.path.join(GEN, "jobref"), exist_ok=True)
    for qid in qids():
        sql = open(os.path.join(SRC, f"{qid}.sql"), encoding="utf-8").read()
        sql = sql.strip().rstrip(";").strip()
        one_line = " ".join(sql.split())  # \copy не переносит строки
        with open(os.path.join(GEN, "jobref", f"q_{qid}.sql"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(f"SET statement_timeout = '{TIMEOUT_S}s';\n"
                    f"\\timing on\n"
                    f"\\copy ({one_line}) TO STDOUT WITH (FORMAT csv)\n")
        with open(os.path.join(GEN, "jobref", f"pe_{qid}.sql"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(f"SET statement_timeout = '{TIMEOUT_S}s';\n"
                    f"\\timing on\n"
                    f"EXPLAIN (ANALYZE, FORMAT JSON, TIMING OFF) {sql};\n")
    rcmd = REMOTE.replace("/", "\\")
    with open(os.path.join(GEN, "jobref_run.cmd"), "w", encoding="utf-8",
              newline="\r\n") as f:
        f.write(f"""@echo off
set "PGPASSWORD={PG_PWD}"
set "LC_MESSAGES=C"
if not exist {rcmd}\\out mkdir {rcmd}\\out
del /q {rcmd}\\out\\* 2>nul
for %%f in ({rcmd}\\q_*.sql) do C:\\pgsql\\bin\\psql.exe -U postgres -d imdb -A -t -q -f "%%f" > "{rcmd}\\out\\%%~nf.csv" 2> "{rcmd}\\out\\%%~nf.err"
for %%f in ({rcmd}\\pe_*.sql) do C:\\pgsql\\bin\\psql.exe -U postgres -d imdb -A -t -q -f "%%f" > "{rcmd}\\out\\%%~nf.json" 2> "{rcmd}\\out\\%%~nf.err"
echo PGREF_DONE
""")
    n = len(qids())
    print(f"generated {n} x (q_, pe_) -> {GEN}\\jobref")


def run_remote():
    subprocess.run(["scp", "-q", *[os.path.join(GEN, "jobref", f) for f in
                    os.listdir(os.path.join(GEN, "jobref"))],
                    f"dellg15:{REMOTE}/"], check=True)
    subprocess.run(["scp", "-q", os.path.join(GEN, "jobref_run.cmd"),
                    "dellg15:E:/pgdumps/"], check=True)
    r = subprocess.run(["ssh", "dellg15", "E:\\pgdumps\\jobref_run.cmd"],
                       capture_output=True, text=True)
    print(r.stdout[-2000:], r.stderr[-2000:])


def parse():
    os.makedirs(OUTDIR, exist_ok=True)
    out = os.path.join(GEN, "out")
    parsed = {}
    for qid in qids():
        entry = {"rows": None, "seconds": None, "checksum": None,
                 "plan": None, "error": None}
        cf = os.path.join(out, f"q_{qid}.csv")
        ef = os.path.join(out, f"q_{qid}.err")
        if os.path.exists(cf):
            raw = open(cf, encoding="utf-8", errors="replace").read()
            # \timing пишет "Time: ..." в тот же stdout — отделяем от данных
            import re as _re
            time_re = _re.compile(r"^Time: ([\d.,]+) ms")
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
                    # одиночная пустая строка CSV = строка результата из NULL
                    # (агрегат MIN по 0 строк; FB возвращает (None,...))
                    rows = [[]]
                entry["rows"] = rows
                entry["checksum"] = rows_checksum(rows)
        if os.path.exists(ef):
            for ln in open(ef, encoding="utf-8", errors="replace"):
                if ln.startswith("Time:"):
                    # локаль dellg15 даёт "Time: 107,991 ms" (десятичная запятая)
                    entry["seconds"] = float(ln.split()[1].replace(",", ".")) / 1000.0
                if "ERROR" in ln or "canceling statement" in ln:
                    entry["error"] = ln.strip()[:300]
        pf = os.path.join(out, f"pe_{qid}.json")
        if os.path.exists(pf):
            txt = open(pf, encoding="utf-8", errors="replace").read().strip()
            # psql может дописать "Time: ..." в тот же поток
            if "]" in txt:
                txt = txt[:txt.rfind("]") + 1]
            if txt.startswith("["):
                try:
                    plan = json.loads(txt)
                    entry["plan"] = plan
                    try:
                        entry["pg_execution_ms"] = plan[0]["Execution Time"]
                    except (KeyError, IndexError, TypeError):
                        pass
                except json.JSONDecodeError as e:
                    entry["error"] = f"plan parse: {e}"
        parsed[qid] = entry
        with open(os.path.join(OUTDIR, f"{qid}.json"), "w",
                  encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, indent=1)
    ok = sum(1 for e in parsed.values() if e["checksum"])
    plans = sum(1 for e in parsed.values() if e["plan"])
    print(f"parsed: {ok} results, {plans} plans -> {OUTDIR}")


if __name__ == "__main__":
    {"gen": gen, "run": run_remote, "parse": parse}[sys.argv[1]]()
