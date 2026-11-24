select
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
