-- using 42 as a seed to the RNG


select
	s_name,
	s_address
from
	supplier,
	nation
where
	s_suppkey in (
		select
			ps_suppkey
		from
			partsupp
		where
			ps_partkey in (
				select
					p_partkey
				from
					part
				where
					p_name like 'medium%'
			)
			and ps_availqty > (
				select
					0.5 * sum(l_quantity)
				from
					lineitem
				where
					l_partkey = ps_partkey
					and l_suppkey = ps_suppkey
					and l_shipdate >= CAST('1995-01-01' AS DATE)
					and l_shipdate < DATEADD(1 YEAR TO CAST('1995-01-01' AS DATE))
			)
	)
	and s_nationkey = n_nationkey
	and n_name = 'KENYA'
order by
	s_name
