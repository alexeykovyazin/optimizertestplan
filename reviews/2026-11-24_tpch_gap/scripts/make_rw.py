"""make_rw.py - builds the hand-rewritten TPC-H queries of the job tpchgap2: every query is rewritten the way the
proposed optimizer change would transform it, to measure the expected gain. Output: rw/tpch/rw_NN.sql (Firebird),
rw/pg_rw_NN.sql (PostgreSQL, for a cross-check of the results), rw/exp_tg_rw.json, rw/exp_tg_scan.json."""
import json
import os
import re

here = os.path.dirname(os.path.abspath(__file__))
src = r"E:\Projects_Big\optimizertestplan\bench\queries\tpch"
out = os.path.join(here, "rw")
os.makedirs(os.path.join(out, "tpch"), exist_ok=True)


def orig(n):
    return open(os.path.join(src, "tpch_%02d.sql" % n), encoding="utf-8").read().replace("\r\n", "\n")


def sub1(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)


q = {}

# constant folding: DATEADD of literals written as a literal
q["rw_04"] = sub1(orig(4), "DATEADD(3 MONTH TO CAST('1994-11-01' AS DATE))", "CAST('1995-02-01' AS DATE)")
q["rw_10"] = sub1(orig(10), "DATEADD(3 MONTH TO CAST('1993-04-01' AS DATE))", "CAST('1993-07-01' AS DATE)")
q["rw_12"] = sub1(orig(12), "DATEADD(1 YEAR TO CAST('1994-01-01' AS DATE))", "CAST('1995-01-01' AS DATE)")

# OR: single-table restrictions implied by the OR are added
t7 = orig(7)
m = re.search(r"\n(\s*)and l_shipdate between", t7)
assert m
q["rw_07"] = t7.replace(m.group(0), "\n%sand n1.n_name in ('JAPAN', 'JORDAN')\n%sand n2.n_name in ('JAPAN', 'JORDAN')%s" % (
    m.group(1), m.group(1), m.group(0)), 1)

# OR: the common join equality is factored out, the single-table restrictions implied by the OR are added
q["rw_19"] = """select
	sum(l_extendedprice* (1 - l_discount)) as revenue
from
	lineitem,
	part
where
	p_partkey = l_partkey
	and l_shipmode in ('AIR', 'AIR REG')
	and l_shipinstruct = 'DELIVER IN PERSON'
	and p_size >= 1
	and ((l_quantity >= 2 and l_quantity <= 12)
		or (l_quantity >= 19 and l_quantity <= 29)
		or (l_quantity >= 25 and l_quantity <= 35))
	and ((p_brand = 'Brand#53' and p_container in ('SM CASE', 'SM BOX', 'SM PACK', 'SM PKG') and p_size <= 5)
		or (p_brand = 'Brand#54' and p_container in ('MED BAG', 'MED BOX', 'MED PKG', 'MED PACK') and p_size <= 10)
		or (p_brand = 'Brand#13' and p_container in ('LG CASE', 'LG BOX', 'LG PACK', 'LG PKG') and p_size <= 15))
	and (
		(
			p_brand = 'Brand#53'
			and p_container in ('SM CASE', 'SM BOX', 'SM PACK', 'SM PKG')
			and l_quantity >= 2 and l_quantity <= 2 + 10
			and p_size between 1 and 5
		)
		or
		(
			p_brand = 'Brand#54'
			and p_container in ('MED BAG', 'MED BOX', 'MED PKG', 'MED PACK')
			and l_quantity >= 19 and l_quantity <= 19 + 10
			and p_size between 1 and 10
		)
		or
		(
			p_brand = 'Brand#13'
			and p_container in ('LG CASE', 'LG BOX', 'LG PACK', 'LG PKG')
			and l_quantity >= 25 and l_quantity <= 25 + 10
			and p_size between 1 and 15
		)
	)
"""

# semi-join over a sub-query with a unique key: an inner join with the grouped derived table
q["rw_18"] = """select
	c_name, c_custkey, o_orderkey, o_orderdate, o_totalprice, sum(l_quantity)
from
	customer,
	orders,
	lineitem,
	(select l_orderkey as t_orderkey from lineitem group by l_orderkey having sum(l_quantity) > 312) t
where
	o_orderkey = t.t_orderkey
	and c_custkey = o_custkey
	and o_orderkey = l_orderkey
group by
	c_name, c_custkey, o_orderkey, o_orderdate, o_totalprice
order by
	o_totalprice desc, o_orderdate
"""

# sub-query predicates are checked after the selective joins (FIRST keeps the derived table apart)
q["rw_21"] = """select
	s_name, count(*) as numwait
from
	(select first 2000000000 s_name, l1.l_orderkey as k_orderkey, l1.l_suppkey as k_suppkey
	 from supplier, lineitem l1, orders, nation
	 where s_suppkey = l1.l_suppkey
		and o_orderkey = l1.l_orderkey
		and o_orderstatus = 'F'
		and l1.l_receiptdate > l1.l_commitdate
		and s_nationkey = n_nationkey
		and n_name = 'VIETNAM') j
where
	exists (select * from lineitem l2 where l2.l_orderkey = j.k_orderkey and l2.l_suppkey <> j.k_suppkey)
	and not exists (select * from lineitem l3 where l3.l_orderkey = j.k_orderkey and l3.l_suppkey <> j.k_suppkey
		and l3.l_receiptdate > l3.l_commitdate)
group by
	s_name
order by
	numwait desc, s_name
"""

# NOT EXISTS as an anti-join (written as LEFT JOIN ... IS NULL)
t22 = orig(22)
t22 = sub1(t22, "\t\t\tcustomer\n\t\twhere\n\t\t\tsubstring(c_phone from 1 for 2) in\n\t\t\t\t('38',",
           "\t\t\tcustomer left join orders on o_custkey = c_custkey\n\t\twhere\n\t\t\tsubstring(c_phone from 1 for 2) in\n\t\t\t\t('38',")
m = re.search(r"\n\s*and not exists \(\s*select\s*\*\s*from\s*orders\s*where\s*o_custkey = c_custkey\s*\)", t22)
assert m
q["rw_22"] = t22.replace(m.group(0), "\n\t\t\tand o_orderkey is null", 1)

# correlated scalar aggregate sub-query: a join with the grouped derived table
q["rw_17"] = """select
	sum(l_extendedprice) / 7.0 as avg_yearly
from
	lineitem,
	part,
	(select l_partkey as t_partkey, 0.2 * avg(l_quantity) as t_avg from lineitem group by l_partkey) t
where
	p_partkey = l_partkey
	and p_brand = 'Brand#21'
	and p_container = 'WRAP CASE'
	and t.t_partkey = p_partkey
	and l_quantity < t.t_avg
"""
q["rw_20"] = """select
	s_name, s_address
from
	supplier, nation
where
	s_suppkey in (
		select ps_suppkey
		from partsupp,
			(select l_partkey as t_partkey, l_suppkey as t_suppkey, 0.5 * sum(l_quantity) as t_qty
			 from lineitem
			 where l_shipdate >= CAST('1997-01-01' AS DATE)
				and l_shipdate < CAST('1998-01-01' AS DATE)
			 group by l_partkey, l_suppkey) t
		where ps_partkey in (select p_partkey from part where p_name like 'medium%')
			and t.t_partkey = ps_partkey
			and t.t_suppkey = ps_suppkey
			and ps_availqty > t.t_qty
	)
	and s_nationkey = n_nationkey
	and n_name = 'CHINA'
order by
	s_name
"""

for name, text in q.items():
    with open(os.path.join(out, "tpch", name + ".sql"), "w", encoding="utf-8", newline="\n") as f:
        f.write(text.rstrip() + "\n")


def entry(timed_out=False):
    return {"suite": "tpch", "checksum": None, "rows": None, "median_ms": 0, "timed_out": timed_out}


json.dump({name: entry() for name in q}, open(os.path.join(out, "exp_tg_rw.json"), "w", encoding="utf-8"))
json.dump({name: entry() for name in ("tpch_01", "tpch_06", "tpch_14")},
          open(os.path.join(out, "exp_tg_scan.json"), "w", encoding="utf-8"))

# PostgreSQL versions of the decorrelated queries and of the anti-join: a cross-check of the results
pg = {
    "pg_rw_17": q["rw_17"],
    "pg_rw_20": q["rw_20"].replace("CAST('1997-01-01' AS DATE)", "date '1997-01-01'").replace(
        "CAST('1998-01-01' AS DATE)", "date '1998-01-01'"),
    "pg_rw_22": q["rw_22"],
}
for name, text in pg.items():
    one = " ".join(text.split())
    with open(os.path.join(out, name + ".sql"), "w", encoding="utf-8", newline="\n") as f:
        f.write("SET statement_timeout = '300s';\n\\timing on\n\\copy (%s) TO STDOUT WITH (FORMAT csv)\n" % one)

# isql scripts that print the result rows of the queries without a Firebird reference result
for name in ("rw_17", "rw_20", "rw_22"):
    with open(os.path.join(out, "show_" + name + ".sql"), "w", encoding="utf-8", newline="\n") as f:
        f.write(q[name].rstrip() + ";\n")
print("made", sorted(q))
