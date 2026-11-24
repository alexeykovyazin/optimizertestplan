select
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
