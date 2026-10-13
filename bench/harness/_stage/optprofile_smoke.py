
import sys
sys.path.insert(0, r"E:\bench\harness")
import fbenv
fbenv.HOST_PORT = "localhost:3180"
fbenv.ensure_client()
from firebird.driver import connect, create_database
import os
dbp = r"E:\fbdata\optprofile_work\smoke.fdb"
dsn = "inet://localhost:3180/" + dbp.replace(os.sep, "/")
try: os.remove(dbp)
except OSError: pass
db = create_database(dsn, user="SYSDBA", password="masterkey", charset="UTF8")
db.close()
db = connect(dsn, user="SYSDBA", password="masterkey", charset="UTF8")
cur = db.cursor()
db.begin()
cur.execute("create table t (id integer primary key, v varchar(20))")
db.commit()
db.begin()
cur.execute("insert into t values (1,'a')")
db.commit()
ps = cur.prepare("select count(*) from t where v = 'a'")
print("PLAN:", (ps.plan or "").replace(chr(10), " | "))
assert cur.execute("select count(*) from t where v='a'").fetchone()[0] == 1
db.close()
print("SMOKE OK")
