import sys
sys.path.insert(0, 'bench/harness')
import fbenv

fbenv.ensure_client()
db = fbenv.connect_fb('E:/Projects_Big/optimizertestplan/db/golden/imdb_fb5.fdb')
cur = db.cursor()
tests = [
    ("123", "'123' SIMILAR TO '(0|[1-9][0-9]*)([.][0-9]+)?'"),
    ("0", "'0' SIMILAR TO '(0|[1-9][0-9]*)([.][0-9]+)?'"),
    ("123.45", "'123.45' SIMILAR TO '(0|[1-9][0-9]*)([.][0-9]+)?'"),
    ("01", "'01' SIMILAR TO '(0|[1-9][0-9]*)([.][0-9]+)?'"),
    ("abc", "'abc' SIMILAR TO '(0|[1-9][0-9]*)([.][0-9]+)?'"),
    ("1a", "'1a' SIMILAR TO '(0|[1-9][0-9]*)([.][0-9]+)?'"),
    ("12.", "'12.' SIMILAR TO '(0|[1-9][0-9]*)([.][0-9]+)?'"),
    ("empty", "'' SIMILAR TO '(0|[1-9][0-9]*)([.][0-9]+)?'"),
    ("plus", "'+1' SIMILAR TO '(0|[1-9][0-9]*)([.][0-9]+)?'"),
]
for name, cond in tests:
    try:
        cur.execute(f"SELECT {cond} FROM RDB$DATABASE")
        print(name, cur.fetchone()[0])
    except Exception as e:
        print(name, "ERR:", str(e)[:100])
cur.close()
db.close()
