"""punpack_test.py <firebird root> <database file> - a local check of the partial record unpack.

It builds a table with three record formats, long fragmented records, back versions and deleted rows, then prints
the results of read queries that reference different sets of fields. Run it with the base engine and with the
patched engine: the two outputs must be equal."""
import hashlib
import os
import subprocess
import sys

root, dbfile = sys.argv[1], sys.argv[2]
os.environ["FIREBIRD"] = root
os.environ["PATH"] = root + os.pathsep + os.environ["PATH"]

from firebird.driver import connect, create_database, driver_config  # noqa: E402

driver_config.fb_client_library.value = os.path.join(root, "fbclient.dll")
if os.path.exists(dbfile):
    os.remove(dbfile)

subprocess.run([os.path.join(root, "isql.exe"), "-q", "-user", "SYSDBA"], text=True, check=True,
               input="create database '%s' page_size 8192 default character set utf8;\n" % dbfile)
con = connect(dbfile, user="SYSDBA", charset="UTF8")
cur = con.cursor()
cur.execute("""create table t (
    id integer not null,
    a smallint, b bigint, c numeric(15,2), d date, e char(10), f varchar(50), g double precision,
    h timestamp, i char(30), j varchar(200), k blob sub_type text, l integer,
    m varchar(12000) character set none, n integer,
    constraint t_pk primary key (id))""")
con.commit()
cur.execute("create index t_c on t (c)")
cur.execute("create index t_f on t (f)")
con.commit()

FILL = """execute block as
declare i integer = %d;
begin
  while (i < %d) do
  begin
    insert into t (id, a, b, c, d, e, f, g, h, i, j, k, %s m, n) values (
      :i, iif(mod(:i, 11) = 0, null, mod(:i, 9)), :i * 100003, :i * 1.37 - 5000,
      dateadd(mod(:i, 2500) day to date '2000-01-01'), iif(mod(:i, 13) = 0, null, 'e' || mod(:i, 97)),
      iif(mod(:i, 17) = 0, null, 'строка ' || :i || ' f'), :i / 7.0,
      dateadd(:i minute to timestamp '2001-02-03 04:05:06'), 'i' || mod(:i, 5),
      iif(mod(:i, 19) = 0, null, rpad('j' || :i, mod(:i, 190) + 3, 'ж')),
      iif(mod(:i, 23) = 0, 'blob ' || :i, null), %s
      iif(mod(:i, 50) = 0, rpad('', 10000, (:i * 7919) || 'qwertyuiopasdfghjklzxcvbnm' || :i),
          iif(mod(:i, 3) = 0, null, 'm' || :i)),
      iif(mod(:i, 29) = 0, null, :i));
    i = i + 1;
  end
end"""

cur.execute(FILL % (1, 20001, "l,", ":i * 2,"))
con.commit()
cur.execute("alter table t add o integer default 5, add p varchar(20) default 'dflt'")
con.commit()
cur.execute(FILL % (20001, 25001, "l,", ":i * 2,"))
con.commit()
cur.execute("alter table t drop l")
con.commit()
cur.execute(FILL % (25001, 27001, "", ""))
con.commit()

QUERIES = [
    "select sum(id) from t",
    "select count(*), count(a), sum(a) from t",
    "select sum(b), min(c), max(c), sum(c) from t",
    "select count(d), min(d), max(d) from t",
    "select sum(char_length(e)), min(e), max(e) from t",
    "select sum(char_length(f)), sum(hash(f)) from t",
    "select sum(g), min(h), max(h) from t",
    "select count(i), sum(char_length(j)), sum(hash(j)) from t",
    "select sum(char_length(k)), count(k) from t",
    "select sum(char_length(m)), sum(hash(m)) from t",
    "select sum(n), count(n) from t",
    "select sum(o), count(o), count(p), min(p), max(p) from t",
    "select sum(a), count(c) from t where id between 100 and 9000",
    "select sum(a), count(e) from t where c > 1000 and c < 9000",
    "select count(*), sum(b) from t where f starting with 'строка 12'",
    "select first 50 id, a, c from t order by c desc, id",
    "select first 20 id, f, j from t order by f nulls last, id",
    "select first 20 id, a, m from t where id >= 19990 order by a, id",
    "select count(*), sum(t1.a + t2.a) from t t1 join t t2 on t2.b = t1.b + 100003 where t1.id < 3000",
    "select count(*), sum(t2.n) from t t1 join t t2 on t2.id = t1.id + 1 where t1.a = 2",
    "select d, count(*), sum(c) from t where id < 6000 group by d order by d",
    "select a, count(*), min(e), max(f) from t group by a order by a",
    "select * from t where id in (1, 50, 100, 7000, 20500, 26000, 21, 14, 31, 62) order by id",
    "select count(*) from t where f like '%7%' and a > 3",
    "select count(*) from t t1 where exists (select 1 from t t2 where t2.id = t1.id + 5 and t2.a = t1.a)",
    "select count(distinct e), count(distinct a) from t",
    "select id, a, rdb$record_version is not null from t where id in (7, 14, 28, 31) order by id",
    "select sum(hash(coalesce(e, '') || coalesce(f, '') || coalesce(j, '') || coalesce(m, ''))), sum(a), sum(b), "
    "sum(c), sum(n), sum(o) from t",
]


def show(tag, c):
    for q in QUERIES:
        c.execute(q)
        rows = c.fetchall()
        text = repr(rows)
        if len(text) > 300:
            text = "%d rows sha1 %s" % (len(rows), hashlib.sha1(text.encode("utf-8")).hexdigest())
        print(tag, "|", q[:70], "|", text)


show("clean", cur)
con.commit()

# an old snapshot stays open while another connection makes back versions and deleted rows
old = connect(dbfile, user="SYSDBA",charset="UTF8")
ocur = old.cursor()
ocur.execute("select count(*) from t")
print("old snapshot rows", ocur.fetchall())

cur.execute("update t set c = c + 1, f = f || 'x' where mod(id, 7) = 0")
con.commit()
cur.execute("update t set a = a + 1, j = 'changed ' || id, n = n + 1 where mod(id, 14) = 0")
con.commit()
cur.execute("update t set m = 'short now' where mod(id, 100) = 0")
con.commit()
cur.execute("delete from t where mod(id, 31) = 0")
con.commit()

show("old", ocur)
show("new", cur)
con.commit()

# a not committed change of this transaction: own versions and undo data
cur.execute("update t set e = 'own' where mod(id, 5) = 0")
cur.execute("update t set e = 'own2', g = g + 1 where mod(id, 10) = 0")
show("own", cur)
show("old2", ocur)
con.rollback()
old.commit()
old.close()

# the old versions are garbage now: the scans below collect them
show("gc1", cur)
con.commit()
show("gc2", cur)
con.commit()

cur.execute("update t set n = n + 1 where a = 3")
cur.execute("delete from t where a = 4")
con.commit()
show("dml", cur)
cur.execute("select count(*) from t where c > -100000")
by_index = cur.fetchall()
cur.execute("select count(*) from t where c + 0 > -100000")
print("index against natural", by_index, cur.fetchall())
cur.execute("select count(*) from t where f > ''")
by_index = cur.fetchall()
cur.execute("select count(*) from t where f || '' > ''")
print("index against natural", by_index, cur.fetchall())
con.commit()
con.close()

r = subprocess.run([os.path.join(root, "gfix.exe"), "-v", "-full", "-user", "SYSDBA", dbfile],
                   capture_output=True, text=True)
print("gfix validate rc", r.returncode, "|", (r.stdout + r.stderr).strip()[:300])
