"""Обвязка доступа к Firebird для тестов оптимизатора (раздел 5 плана).

Возможности базового инстанса (FB 5.0.5, порт 3055):
  - планы: Statement.plan (простой) и Statement.detailed_plan (дерево доступа);
  - счётчики: isc_info_fetches (page fetches) и постатоличные
    record reads (seq/idx) через isc_database_info (get_table_access_stats);
  - таймаут исполнения: statement timeout на соединении (FB 4+);
  - таймаут prepare: клиентский сторож (отдельный поток + abandon соединения).
RDB$SQL.EXPLAIN с CARDINALITY недоступен (это FB 6) — оценки по узлам,
q-error и CERT на этом инстансе не снимаются (см. отчёт фазы 0).
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

FB_CLIENT_DIR = os.environ.get("FB_CLIENT_DIR", r"C:\Firebird5")
FB_BIN = os.environ.get("FB_BIN", FB_CLIENT_DIR)
HOST_PORT = os.environ.get("FB_HOSTPORT", "localhost:3055")
FB_USER = os.environ.get("FB_USER", "SYSDBA")
FB_PASSWORD = os.environ.get("FB_PASSWORD", "masterkey")

_conn = None  # lazy import target


def ensure_client():
    p = FB_CLIENT_DIR
    if os.path.isdir(p):
        # add_dll_directory и PATH — строго ОДИН РАЗ за процесс: каждое
        # добавление выделяет DLL-каталог, который не освобождается; после
        # ~2500 накопленных вызовов AddDllDirectory начинает спорадически
        # падать с WinError 206 (ERROR_FILENAME_EXCED_RANGE)
        global _client_ready
        if not _client_ready:
            os.add_dll_directory(p)
            if p not in os.environ.get("PATH", "").split(os.pathsep):
                os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")
            _client_ready = True


def dsn(db_path: str) -> str:
    return f"inet://{HOST_PORT}/{db_path.replace(os.sep, '/')}"


_client_ready = False

_optimize_session_supported: bool | None = None


def connect_fb(db_path: str, stmt_timeout_s: float | None = None,
               optimize_all_rows: bool = True):
    """Открыть соединение. Пытается пиннить SET OPTIMIZE ALL ROWS (дефолт
    Firebird — ALL ROWS): общий инстанс на 3055 имеет в firebird.conf
    OptimizeForFirstRows=true. Если движок не принимает SET OPTIMIZE через
    DSQL (команда isql), фиксированной конфигурацией измерений остаётся
    конфигурация инстанса; она входит в хеш ключа эталона (4.2)."""
    global _optimize_session_supported
    ensure_client()
    from firebird.driver import connect
    # lc_ctype фиксирован: без него драйвер берёт кодировку локали (на
    # ru-Windows это cp1251 — падение на не-ASCII данных IMDb)
    db = connect(dsn(db_path), user=FB_USER, password=FB_PASSWORD,
                 charset="UTF8")
    if optimize_all_rows and _optimize_session_supported is None:
        try:
            cur = db.cursor()
            cur.execute("SET OPTIMIZE ALL ROWS")
            cur.close()
            _optimize_session_supported = True
        except Exception:
            _optimize_session_supported = False
            try:
                db.close()
            except Exception:
                pass
            db = connect(dsn(db_path), user=FB_USER, password=FB_PASSWORD,
                         charset="UTF8")
    if stmt_timeout_s:
        db.info.set_statement_timeout = int(stmt_timeout_s * 1000)
    return db


@dataclass
class Counters:
    """Снимок логических счётчиков одного соединения."""
    fetches: int = 0                      # page fetches
    seq_reads: dict = field(default_factory=dict)   # table -> record reads (natural)
    idx_reads: dict = field(default_factory=dict)   # table -> record reads (index)

    def delta(self, before: "Counters") -> "Counters":
        tables = set(self.seq_reads) | set(before.seq_reads) | \
                 set(self.idx_reads) | set(before.idx_reads)
        d = Counters(fetches=self.fetches - before.fetches)
        for t in tables:
            s = self.seq_reads.get(t, 0) - before.seq_reads.get(t, 0)
            i = self.idx_reads.get(t, 0) - before.idx_reads.get(t, 0)
            if s:
                d.seq_reads[t] = s
            if i:
                d.idx_reads[t] = i
        return d

    def total_record_reads(self) -> int:
        return sum(self.seq_reads.values()) + sum(self.idx_reads.values())

    def as_dict(self) -> dict:
        return {"fetches": self.fetches,
                "seq_reads": dict(sorted(self.seq_reads.items())),
                "idx_reads": dict(sorted(self.idx_reads.items()))}


def read_counters(db, table_map: dict | None = None) -> Counters:
    """Считать накопленные счётчики соединения (isc_database_info)."""
    c = Counters(fetches=db.info.fetches)
    for st in db.info.get_table_access_stats():
        name = table_map[st.table_id] if table_map else str(st.table_id)
        if st.sequential:
            c.seq_reads[name] = c.seq_reads.get(name, 0) + st.sequential
        if st.indexed:
            c.idx_reads[name] = c.idx_reads.get(name, 0) + st.indexed
    return c


def table_id_map(db) -> dict:
    cur = db.cursor()
    cur.execute("SELECT RDB$RELATION_ID, TRIM(RDB$RELATION_NAME) FROM RDB$RELATIONS")
    m = {tid: name.strip() for tid, name in cur.fetchall()}
    cur.close()
    return m


def prepare_with_watchdog(db_path: str, sql: str, timeout_s: float) -> dict:
    """Prepare с клиентским сторожем: statement timeout на prepare не
    действует (раздел 5 плана), поэтому prepare уходит в отдельный поток;
    при зависании соединение бросается и открывается новое."""
    ensure_client()
    result = {"prepare_ms": None, "plan": None, "detailed_plan": None,
              "timed_out": False, "error": None}

    def work():
        t0 = time.perf_counter()
        conn = connect_fb(db_path, optimize_all_rows=True)
        try:
            cur = conn.cursor()
            ps = cur.prepare(sql)
            result["prepare_ms"] = (time.perf_counter() - t0) * 1000.0
            result["plan"] = ps.plan
            result["detailed_plan"] = ps.detailed_plan
            ps.free()
            cur.close()
        finally:
            conn.close()

    with ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(work)
        try:
            fut.result(timeout=timeout_s)
        except TimeoutError:
            result["timed_out"] = True
        except Exception as e:  # noqa: BLE001
            result["error"] = f"{type(e).__name__}: {e}"
    return result


# ---------------------------------------------------------------- инструменты

def _run_tool(tool: str, args: list[str], timeout: int = 1800) -> tuple[int, str]:
    exe = os.path.join(FB_BIN, tool)
    r = subprocess.run([exe, *args], capture_output=True, text=True,
                       timeout=timeout)
    out = (r.stdout or "") + (r.stderr or "")
    return r.returncode, out


def gbak_backup(db_path: str, fbk_path: str, timeout: int = 7200) -> tuple[int, str]:
    if os.path.exists(fbk_path):
        os.remove(fbk_path)
    return _run_tool("gbak.exe", ["-b", dsn(db_path), fbk_path,
                                  "-user", FB_USER, "-password", FB_PASSWORD,
                                  "-v"], timeout=timeout)


def gfix_set_readonly(db_path: str) -> tuple[int, str]:
    return _run_tool("gfix.exe", ["-user", FB_USER, "-password", FB_PASSWORD,
                                  "-mode", "read_only", db_path])


def gfix_set_readwrite(db_path: str) -> tuple[int, str]:
    return _run_tool("gfix.exe", ["-user", FB_USER, "-password", FB_PASSWORD,
                                  "-mode", "read_write", db_path])


def isql_script(db_path: str | None, script_sql: str) -> tuple[int, str]:
    """Выполнить SQL-скрипт через isql (для SET STATISTICS INDEX и DDL).
    db_path=None — без подключения (создание новой БД)."""
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False,
                                     encoding="utf-8") as f:
        f.write(script_sql)
        path = f.name
    try:
        args = [dsn(db_path)] if db_path else []
        return _run_tool("isql.exe", [*args, "-user", FB_USER,
                                      "-password", FB_PASSWORD, "-i", path])
    finally:
        os.unlink(path)


def sha256_file(path: str, bufsize: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(bufsize):
            h.update(chunk)
    return h.hexdigest()


def byte_copy(src: str, dst: str) -> str:
    """Побайтовая копия золотого файла (раздел 4.2). Копия делается при
    отсутствии активных соединений с источником; для гарантий используется
    блокировка nbackup, если файл принадлежит серверу."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(src, "rb") as fi, open(dst, "wb") as fo:
        while chunk := fi.read(1 << 22):
            fo.write(chunk)
    return sha256_file(dst)
