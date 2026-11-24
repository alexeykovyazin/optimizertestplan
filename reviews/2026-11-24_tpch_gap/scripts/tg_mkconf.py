r"""tg_mkconf.py - makes E:\fbdata\firebird_tg_cache.conf: the original config with DefaultDbCachePages = 130000
(the whole TPC-H database, 99214 pages of 16K, fits into the page cache). Firebird takes the first occurrence of
a key, so the line is replaced, not appended."""
import re

src = open(r"E:\fbdata\firebird_orig.conf", encoding="utf-8", errors="replace").read()
new, n = re.subn(r"(?m)^DefaultDbCachePages\s*=.*$", "DefaultDbCachePages = 130000", src)
assert n == 1, n
open(r"E:\fbdata\firebird_tg_cache.conf", "w", encoding="utf-8", newline="").write(new)
print("conf made")
