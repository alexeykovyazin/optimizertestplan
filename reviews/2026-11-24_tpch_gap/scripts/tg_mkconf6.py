"""tg_mkconf6.py - makes firebird_tg_cache_fs.conf: DefaultDbCachePages = 130000 and UseFileSystemCache = true."""
import re
src = open("E:/fbdata/firebird_orig.conf", encoding="utf-8", errors="replace").read()
new, n = re.subn(r"(?m)^DefaultDbCachePages\s*=.*$", "DefaultDbCachePages = 130000\nUseFileSystemCache = true", src)
assert n == 1, n
open("E:/fbdata/firebird_tg_cache_fs.conf", "w", encoding="utf-8", newline="").write(new)
print("conf made")
