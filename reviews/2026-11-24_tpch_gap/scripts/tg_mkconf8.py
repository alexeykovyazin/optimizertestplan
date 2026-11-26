"""tg_mkconf8.py - makes the configs of the settings parity with PostgreSQL: DefaultDbCachePages = 128K and
UseFileSystemCache = true. firebird_tg_par.conf comes from firebird_orig.conf, firebird_tg_par_dp.conf from
firebird_dpdef.conf (JoinOrderDP = true). Firebird takes the first occurrence of a key, so the line is replaced."""
import re

for src_name, dst_name in (("firebird_orig.conf", "firebird_tg_par.conf"),
                           ("firebird_dpdef.conf", "firebird_tg_par_dp.conf")):
    src = open("E:/fbdata/" + src_name, encoding="utf-8", errors="replace").read()
    assert not re.search(r"(?m)^UseFileSystemCache\s*=", src), src_name
    new, n = re.subn(r"(?m)^DefaultDbCachePages\s*=.*$", "DefaultDbCachePages = 128K\nUseFileSystemCache = true", src)
    assert n == 1, (src_name, n)
    open("E:/fbdata/" + dst_name, "w", encoding="utf-8", newline="").write(new)
print("conf8 made")
