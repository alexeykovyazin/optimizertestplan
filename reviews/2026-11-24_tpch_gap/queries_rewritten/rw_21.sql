select
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
