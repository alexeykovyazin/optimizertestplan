import sys
sys.path.insert(0, 'bench/harness')
import fbenv

fbenv.ensure_client()
db = fbenv.connect_fb('E:/Projects_Big/optimizertestplan/db/golden/imdb_fb5.fdb')
cur = db.cursor()
tests = [
    ("cast_blob_double", "SELECT COUNT(*) FROM movie_info mi WHERE mi.info_type_id = 101 AND CAST(mi.info AS DOUBLE PRECISION) <= 5.0"),
    ("cast_blob_sub", "SELECT COUNT(*) FROM movie_info mi WHERE CAST(SUBSTRING(mi.info FROM 1 FOR 100) AS DOUBLE PRECISION) <= 5.0"),
]
for name, sql in tests:
    try:
        cur.execute(sql)
        print(name, "OK rows:", cur.fetchone()[0])
    except Exception as e:
        print(name, "ERR:", str(e).replace(chr(10), ' ')[:120])
cur.close()
db.close()
