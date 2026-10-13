import sys
sys.path.insert(0, 'bench/harness')
import fbenv

fbenv.ensure_client()
db = fbenv.connect_fb('E:/Projects_Big/optimizertestplan/db/golden/imdb_fb5.fdb')
cur = db.cursor()
tests = [
    ("blob_in", "SELECT COUNT(*) FROM movie_info mi WHERE mi.info IN ('Sweden', 'Norway')"),
    ("blob_eq", "SELECT COUNT(*) FROM movie_info mi WHERE mi.info = 'Sweden'"),
    ("blob_min", "SELECT MIN(mi.info) FROM movie_info mi"),
    ("blob_min_sub", "SELECT MIN(SUBSTRING(mi.info FROM 1 FOR 8000)) FROM movie_info mi"),
    ("blob_like", "SELECT COUNT(*) FROM movie_info mi WHERE mi.info LIKE '%Sweden%'"),
    ("blob_neq", "SELECT COUNT(*) FROM movie_info mi WHERE mi.info != 'Sweden'"),
    ("clob_between", "SELECT COUNT(*) FROM title t WHERE t.production_year BETWEEN 1950 AND 2000"),
    ("is_null_note", "SELECT COUNT(*) FROM movie_companies mc WHERE mc.note IS NULL"),
]
for name, sql in tests:
    try:
        cur.prepare(sql)
        print(name, "OK")
    except Exception as e:
        print(name, "FAIL:", str(e)[:140])
cur.close()
db.close()
