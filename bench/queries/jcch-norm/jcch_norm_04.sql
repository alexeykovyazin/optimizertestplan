-- using 42 as a seed to the RNG


select
	o_orderpriority,
	count(*) as order_count
from
	orders
where
	o_orderdate >= CAST('1995-02-01' AS DATE)
	and o_orderdate < DATEADD(3 MONTH TO CAST('1995-02-01' AS DATE))
	and exists (
		select
			*
		from
			lineitem
		where
			l_orderkey = o_orderkey
			and l_commitdate < l_receiptdate
	)
group by
	o_orderpriority
order by
	o_orderpriority
